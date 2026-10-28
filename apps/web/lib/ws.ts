/**
 * WebSocket Realtime Client with Polling Fallback – Fix 24/7
 * FR-TRACK-01: Realtime order status, technician position & chat.
 * Fallback to 5-second polling when WebSocket is disconnected.
 */

export interface WSStatusMessage {
  type: "status";
  status: string;
}

export interface WSLocationMessage {
  type: "location";
  order_id: string;
  lat: number;
  lng: number;
  ts: string;
}

export interface WSChatMessage {
  type: "chat";
  message: {
    id: string;
    order_id: string;
    sender_id: string;
    sender_role: string;
    content: string;
    media_url?: string | null;
    created_at: string;
  };
}

export interface WSJobInviteMessage {
  type: "job_invite";
  order_id: string;
  distance_m: number;
  address: string;
  expires_in: number;
}

export type WSMessage =
  | WSStatusMessage
  | WSLocationMessage
  | WSChatMessage
  | WSJobInviteMessage;

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1";
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function createOrderStream(
  orderId: string,
  token: string,
  onMessage: (msg: WSMessage) => void
): () => void {
  let ws: WebSocket | null = null;
  let pollingInterval: NodeJS.Timeout | null = null;
  let isClosed = false;
  let lastEventTime = new Date().toISOString();

  function startPolling() {
    if (pollingInterval || isClosed) return;

    pollingInterval = setInterval(async () => {
      try {
        const res = await fetch(
          `${API_BASE}/orders/${orderId}/events?since=${encodeURIComponent(
            lastEventTime
          )}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        if (!res.ok) return;

        const data = await res.json();
        if (data.status) {
          onMessage({ type: "status", status: data.status });
        }
        if (data.messages && Array.isArray(data.messages)) {
          data.messages.forEach((m: any) => {
            onMessage({ type: "chat", message: m });
          });
        }
        lastEventTime = new Date().toISOString();
      } catch (err) {
        // Ignore polling error
      }
    }, 5000); // FR-TRACK-01: 5s polling fallback
  }

  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  }

  function connect() {
    if (isClosed) return;

    try {
      const wsUrl = `${WS_BASE}/orders/${orderId}/stream?token=${encodeURIComponent(
        token
      )}`;
      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        stopPolling();
      };

      ws.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          onMessage(parsed);
        } catch (e) {
          // Ignore parse error
        }
      };

      ws.onclose = () => {
        if (!isClosed) {
          startPolling();
          // Attempt reconnect after 3s
          setTimeout(connect, 3000);
        }
      };

      ws.onerror = () => {
        if (ws) ws.close();
      };
    } catch (e) {
      startPolling();
    }
  }

  connect();

  return () => {
    isClosed = true;
    stopPolling();
    if (ws) {
      ws.close();
      ws = null;
    }
  };
}
