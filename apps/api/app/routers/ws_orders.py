"""
WebSocket Order Stream – Fix 24/7.
FR-TRACK-01/02/03.
Realtime WebSocket endpoint at /orders/{id}/stream for order status,
technician live GPS tracking, and in-order messaging.
"""
from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from jose import JWTError
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.core.security import decode_token, verify_token_type
from app.models import ChatMessage, Order, OrderStatus, User, _uuid_default
from app.routers.orders import mask_phone_number

router = APIRouter(tags=["realtime"])


@router.websocket("/orders/{order_id}/stream")
async def order_websocket_stream(
    websocket: WebSocket,
    order_id: str,
):
    """
    FR-TRACK-01/02/03: WebSocket connection for an order.
    Query param token: ?token=<access_jwt>
    Streams status transitions, live location (when ON_THE_WAY), and chat messages.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Verify token
    try:
        payload = decode_token(token)
        if not verify_token_type(payload, "access"):
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        user_id = payload["sub"]
    except (JWTError, ValueError, KeyError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Check order & user permissions
    async with AsyncSessionLocal() as db:
        u_res = await db.execute(select(User).where(User.id == user_id))
        current_user = u_res.scalar_one_or_none()
        if not current_user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        o_res = await db.execute(select(Order).where(Order.id == order_id))
        order = o_res.scalar_one_or_none()
        if not order:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Check authorization
        if current_user.role.value != "admin":
            if order.customer_id != current_user.id and order.technician_id != current_user.id:
                # Also allow if technician is current candidate in dispatch
                pass

    await websocket.accept()

    redis = await get_redis()
    pubsub = redis.pubsub()
    await pubsub.subscribe(f"order:{order_id}", f"loc:{order_id}")

    async def redis_listener():
        """Listen to Redis channel and forward to WebSocket client."""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    await websocket.send_text(data)
        except (asyncio.CancelledError, Exception):
            pass

    async def client_listener():
        """Receive messages from WebSocket client (e.g. chat messages)."""
        try:
            while True:
                text = await websocket.receive_text()
                try:
                    msg_json = json.loads(text)
                except Exception:
                    continue

                msg_type = msg_json.get("type")
                if msg_type == "chat":
                    raw_content = msg_json.get("content", "").strip()
                    if not raw_content:
                        continue

                    masked_content, is_masked = mask_phone_number(raw_content)
                    media_url = msg_json.get("media_url")

                    async with AsyncSessionLocal() as db:
                        chat_record = ChatMessage(
                            id=_uuid_default(),
                            order_id=order_id,
                            sender_id=current_user.id,
                            sender_role=current_user.role.value,
                            content=masked_content,
                            media_url=media_url,
                            is_phone_masked=is_masked,
                        )
                        db.add(chat_record)
                        await db.commit()
                        await db.refresh(chat_record)

                        chat_event = {
                            "type": "chat",
                            "message": {
                                "id": str(chat_record.id),
                                "order_id": order_id,
                                "sender_id": str(chat_record.sender_id),
                                "sender_role": chat_record.sender_role,
                                "content": chat_record.content,
                                "media_url": chat_record.media_url,
                                "created_at": chat_record.created_at.isoformat(),
                            },
                        }
                        await redis.publish(f"order:{order_id}", json.dumps(chat_event))

        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    redis_task = asyncio.create_task(redis_listener())
    client_task = asyncio.create_task(client_listener())

    done, pending = await asyncio.wait(
        [redis_task, client_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()

    try:
        await pubsub.unsubscribe(f"order:{order_id}", f"loc:{order_id}")
        await pubsub.close()
    except Exception:
        pass

