"""
Dispatch worker service – Fix 24/7.
FR-BOOK-01/02, BR-03: Dispatch finds and invites the best available technician sequentially.
Sequential 60s expiry via Redis, 90s expansion from 3km to 5km, NO_TECH fallback.
"""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
from app.models import DispatchAttempt, Order, OrderStatus, _uuid_default
from app.services.booking_rules import rank_technicians
from app.services.order_state_machine import transition_order
from app.services.technician_location import find_nearby_technicians

# Configuration
INVITE_TIMEOUT_SECONDS = 60
EXPANSION_SECONDS = 90
INITIAL_RADIUS_M = 3000
EXPANDED_RADIUS_M = 5000


async def start_dispatch(
    db: AsyncSession,
    order: Order,
    find_nearby_fn: Optional[Callable] = None,
    redis_client=None,
    sleep_fn: Optional[Callable] = None,
) -> None:
    """
    FR-BOOK-01/02: Emergency dispatch loop.
    1. Transition to SEARCHING
    2. Search <=3km, rank by BR-03
    3. Invite sequentially (60s expiry per tech)
    4. If 90s elapses without accept, expand search to 5km
    5. If all candidates exhausted, transition to NO_TECH
    """
    if find_nearby_fn is None:
        find_nearby_fn = find_nearby_technicians
    if sleep_fn is None:
        sleep_fn = asyncio.sleep

    redis = redis_client or (await get_redis())

    # 1. Transition to SEARCHING
    if order.status != OrderStatus.SEARCHING:
        await transition_order(db, order, OrderStatus.SEARCHING, note="Bắt đầu tìm thợ")

    order_id = str(order.id)
    dispatch_start = time.time()
    invited_tech_ids: set[str] = set()
    accepted = False
    radius_m = INITIAL_RADIUS_M

    while not accepted:
        # Check if 90s passed since dispatch start to expand radius to 5km
        now = time.time()
        if (now - dispatch_start) >= EXPANSION_SECONDS and radius_m < EXPANDED_RADIUS_M:
            radius_m = EXPANDED_RADIUS_M
            if redis:
                try:
                    await redis.set(f"dispatch:{order_id}:expanded", "1")
                except Exception:
                    pass

        # Query candidates
        lat = float(order.lat) if order.lat is not None else 16.4637
        lng = float(order.lng) if order.lng is not None else 107.5909
        raw_candidates = await find_nearby_fn(db=db, lat=lat, lng=lng, radius_m=radius_m)

        # Filter out already invited technicians in this dispatch cycle
        uninvited = [c for c in raw_candidates if str(c.get("user_id")) not in invited_tech_ids]

        if not uninvited:
            # If not yet expanded to 5km, we might wait until 90s expansion point
            elapsed = time.time() - dispatch_start
            if radius_m < EXPANDED_RADIUS_M and elapsed < EXPANSION_SECONDS:
                wait_time = min(5.0, EXPANSION_SECONDS - elapsed)
                await sleep_fn(wait_time)
                continue
            else:
                # No more candidates even at 5km
                break

        # BR-03: Rank candidates
        ranked = rank_technicians(uninvited, order_lat=lat, order_lng=lng)

        # Sequential invite
        round_found_accept = False
        for candidate in ranked:
            tech_id = str(candidate["user_id"])
            invited_tech_ids.add(tech_id)

            attempt = DispatchAttempt(
                id=_uuid_default(),
                order_id=order.id,
                technician_id=tech_id,
                invited_at=datetime.now(timezone.utc),
                response="expired",
            )
            db.add(attempt)
            await db.flush()

            # Set current tech in Redis with 60s TTL
            if redis:
                try:
                    await redis.setex(f"dispatch:{order_id}:current_tech", INVITE_TIMEOUT_SECONDS, tech_id)
                    # Broadcast job invite to technician
                    invite_payload = json.dumps({
                        "type": "job_invite",
                        "order_id": order_id,
                        "distance_m": candidate.get("distance_m", 0),
                        "address": order.address,
                        "expires_in": INVITE_TIMEOUT_SECONDS,
                    })
                    await redis.publish(f"tech:{tech_id}", invite_payload)
                    await redis.publish(f"order:{order_id}", invite_payload)
                except Exception:
                    pass

            # Wait up to 60 seconds polling for response key in Redis
            wait_step = 1.0
            waited = 0.0
            tech_response = None

            while waited < INVITE_TIMEOUT_SECONDS:
                if redis:
                    try:
                        resp = await redis.get(f"dispatch:{order_id}:response:{tech_id}")
                        if resp:
                            tech_response = resp.decode("utf-8") if isinstance(resp, bytes) else str(resp)
                            break
                    except Exception:
                        pass
                await sleep_fn(wait_step)
                waited += wait_step

            # Record response
            attempt.responded_at = datetime.now(timezone.utc)
            if tech_response == "accepted":
                attempt.response = "accepted"
                order.technician_id = tech_id
                order.accepted_at = datetime.now(timezone.utc)
                await transition_order(db, order, OrderStatus.ACCEPTED, actor_id=tech_id, note="Thợ chấp nhận đơn")
                accepted = True
                round_found_accept = True
                break
            elif tech_response == "declined":
                attempt.response = "rejected"
            else:
                attempt.response = "expired"

            await db.flush()

            # Clean up Redis current_tech
            if redis:
                try:
                    await redis.delete(f"dispatch:{order_id}:current_tech")
                except Exception:
                    pass

            # Check if 90s has elapsed to expand search on next check
            if not round_found_accept and (time.time() - dispatch_start) >= EXPANSION_SECONDS and radius_m < EXPANDED_RADIUS_M:
                break  # break inner loop to re-query with 5km

        if round_found_accept:
            break

    # If loop finished without acceptance, end in NO_TECH
    if not accepted:
        await transition_order(db, order, OrderStatus.NO_TECH, note="Không tìm thấy thợ phù hợp")
