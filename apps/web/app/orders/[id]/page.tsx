"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Navigation,
  CheckCircle2,
  AlertTriangle,
  PhoneCall,
  Clock,
  ShieldCheck,
  XCircle,
  Receipt,
  CreditCard,
  Star,
  ShieldAlert,
  AlertOctagon,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { StatusTimeline } from "@/components/order/StatusTimeline";
import { ChatPanel, ChatMessageItem } from "@/components/order/ChatPanel";
import { QuoteSheet } from "@/components/order/QuoteSheet";
import { LeafletMap } from "@/components/map/LeafletMap";
import { apiRequest, ordersApi } from "@/lib/api";
import { createOrderStream, WSMessage } from "@/lib/ws";

export default function OrderTrackingPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params?.id as string;
  const { showToast } = useToast();

  const [order, setOrder] = React.useState<any>(null);
  const [messages, setMessages] = React.useState<ChatMessageItem[]>([]);
  const [techPos, setTechPos] = React.useState<[number, number] | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [actionLoading, setActionLoading] = React.useState(false);

  // Fetch initial order and chat history
  const fetchOrder = React.useCallback(async () => {
    const { data, error } = await apiRequest<any>(`/orders/${orderId}`);
    if (error) {
      showToast(error.message, "error");
      setIsLoading(false);
      return;
    }
    setOrder(data);
    setIsLoading(false);
  }, [orderId, showToast]);

  const fetchMessages = React.useCallback(async () => {
    const { data } = await apiRequest<ChatMessageItem[]>(`/orders/${orderId}/messages`);
    if (data) {
      setMessages(data);
    }
  }, [orderId]);

  React.useEffect(() => {
    fetchOrder();
    fetchMessages();
  }, [fetchOrder, fetchMessages]);

  // Realtime WebSocket stream with fallback
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("fix247_access_token") || "";

    const cleanup = createOrderStream(orderId, token, (msg: WSMessage) => {
      if (msg.type === "status") {
        setOrder((prev: any) => (prev ? { ...prev, status: msg.status } : prev));
        showToast(`Trạng thái đơn hàng cập nhật: ${msg.status}`, "info");
      } else if (msg.type === "location") {
        setTechPos([msg.lat, msg.lng]);
      } else if (msg.type === "chat") {
        setMessages((prev) => {
          if (prev.some((m) => m.id === msg.message.id)) return prev;
          return [...prev, msg.message];
        });
      }
    });

    return () => cleanup();
  }, [orderId, showToast]);

  // Chat message send handler
  const handleSendMessage = async (content: string, mediaUrl?: string) => {
    const { data, error } = await apiRequest<ChatMessageItem>(`/orders/${orderId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content, media_url: mediaUrl }),
    });
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setMessages((prev) => {
        if (prev.some((m) => m.id === data.id)) return prev;
        return [...prev, data];
      });
    }
  };

  // Quote handlers
  const handleAcceptQuote = async () => {
    setActionLoading(true);
    const { data, error } = await apiRequest<any>(`/orders/${orderId}/quote/respond`, {
      method: "POST",
      body: JSON.stringify({ action: "accept" }),
    });
    setActionLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    showToast("Bạn đã chấp thuận báo giá! Thợ đang tiến hành sửa chữa.", "success");
    setOrder(data);
  };

  const handleRejectQuote = async () => {
    if (!confirm("Bạn có chắc chắn muốn từ chối báo giá? Phí khảo sát 30.000đ sẽ được tính.")) {
      return;
    }
    setActionLoading(true);
    const { data, error } = await apiRequest<any>(`/orders/${orderId}/quote/respond`, {
      method: "POST",
      body: JSON.stringify({ action: "reject" }),
    });
    setActionLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    showToast("Đã từ chối báo giá. Đơn hàng đã đóng.", "info");
    setOrder(data);
  };

  // Completion confirmation
  const handleConfirmComplete = async () => {
    setActionLoading(true);
    const { data, error } = await apiRequest<any>(`/orders/${orderId}/confirm-complete`, {
      method: "POST",
    });
    setActionLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    showToast("Xác nhận hoàn thành sửa chữa thành công!", "success");
    setOrder(data);
  };

  // Cancellation handler
  const handleCancelOrder = async () => {
    const reason = prompt("Vui lòng nhập lý do hủy đơn:");
    if (!reason) return;

    setActionLoading(true);
    const { data, error } = await apiRequest<any>(`/orders/${orderId}/cancel`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    });
    setActionLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    showToast("Đã hủy đơn hàng thành công.", "info");
    setOrder(data);
  };

  // Dispute handler
  const handleDispute = async () => {
    const reason = prompt("Vui lòng nêu rõ lý do bạn khiếu nại (chưa hài lòng, lỗi linh kiện, sai giá,...):");
    if (!reason || reason.trim().length < 5) {
      if (reason) showToast("Lý do khiếu nại tối thiểu 5 ký tự.", "error");
      return;
    }
    setActionLoading(true);
    const { error } = await ordersApi.submitDispute(orderId, reason.trim());
    setActionLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    showToast("Đã gửi khiếu nại thành công. Đơn hàng chuyển sang trạng thái tranh chấp để CSKH hỗ trợ.", "info");
    fetchOrder();
  };

  if (isLoading || !order) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-sm text-slate-400">
        Đang tải thông tin đơn hàng...
      </div>
    );
  }

  const custLat = order.lat ? Number(order.lat) : 16.4637;
  const custLng = order.lng ? Number(order.lng) : 107.5909;

  // Build map markers
  const markers: any[] = [
    {
      id: "customer",
      position: [custLat, custLng],
      icon: "customer",
      popup: "Điểm hẹn của bạn",
    },
  ];

  if (techPos) {
    markers.push({
      id: "technician",
      position: techPos,
      icon: "technician",
      popup: "Vị trí thợ hiện tại",
    });
  }

  const canCancel = [
    "CREATED",
    "SEARCHING",
    "SCHEDULED",
    "ACCEPTED",
    "ON_THE_WAY",
  ].includes(order.status);

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 max-w-lg mx-auto w-full space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push("/orders")}
            className="h-10 w-10 p-0 rounded-full"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-xl font-black text-white">Theo Dõi Đơn Hàng</h1>
            <p className="text-xs text-slate-400 font-mono truncate max-w-[180px]">
              #{order.id.slice(0, 8)}...
            </p>
          </div>
        </div>

        {canCancel && (
          <Button
            variant="secondary"
            size="sm"
            onClick={handleCancelOrder}
            disabled={actionLoading}
            className="text-xs text-red-400 border-red-500/30"
          >
            Hủy đơn
          </Button>
        )}
      </div>

      {/* Status Timeline */}
      <div className="p-4 bg-surface-card border border-surface-border rounded-2xl shadow-md">
        <StatusTimeline status={order.status} />
      </div>

      {/* Map (shown especially when ON_THE_WAY or tracking) */}
      {(order.status === "ON_THE_WAY" || order.status === "ACCEPTED" || techPos) && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-slate-300">
            <span className="font-bold flex items-center gap-1.5">
              <Navigation className="w-4 h-4 text-sky-400" />
              <span>Vị trí thợ đang di chuyển (FR-TRACK-02)</span>
            </span>
            <span className="text-emerald-400 font-medium">GPS trực tiếp</span>
          </div>

          <LeafletMap
            center={techPos || [custLat, custLng]}
            zoom={15}
            markers={markers}
          />
        </div>
      )}

      {/* Quote Approval Sheet */}
      {order.status === "QUOTE_PENDING" && (
        <QuoteSheet
          items={order.items || []}
          finalQuote={order.final_quote || 0}
          estMax={order.est_max}
          surcharge={order.night_surcharge}
          quoteReason={order.events?.[order.events.length - 1]?.note}
          isLoading={actionLoading}
          onAccept={handleAcceptQuote}
          onReject={handleRejectQuote}
        />
      )}

      {/* Awaiting Completion Confirmation */}
      {order.status === "AWAITING_CONFIRM" && (
        <div className="p-5 bg-gradient-to-br from-emerald-950/70 via-surface-card to-surface-card border-2 border-emerald-500/60 rounded-3xl shadow-xl space-y-3">
          <div className="flex items-center gap-2 text-emerald-400">
            <ShieldCheck className="w-6 h-6" />
            <h3 className="font-bold text-white text-base">Thợ Đã Sửa Xong – Chờ Nghiệm Thu</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Vui lòng kiểm tra kỹ thiết bị. Sau khi nghiệm thu đạt, hãy thanh toán và bấm xác nhận hoàn tất. Đơn sẽ tự động xác nhận sau 24h nếu không có khiếu nại (BR-08).
          </p>
          {order.total && (
            <div className="p-3 bg-surface-elevated rounded-xl flex items-center justify-between text-sm">
              <span className="text-slate-300">Tổng tiền cần thanh toán:</span>
              <span className="font-black text-emerald-400 text-lg">
                {order.total.toLocaleString("vi-VN")} đ
              </span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2 pt-1">
            <Button
              variant="secondary"
              size="default"
              className="min-h-[44px] flex items-center justify-center gap-1.5"
              onClick={() => router.push(`/orders/${orderId}/invoice`)}
            >
              <Receipt className="w-4 h-4 text-brand-primary" />
              <span>Xem Hóa Đơn</span>
            </Button>
            <Button
              variant="primary"
              size="default"
              className="min-h-[44px] flex items-center justify-center gap-1.5 bg-brand-primary"
              onClick={() => router.push(`/orders/${orderId}/pay`)}
            >
              <CreditCard className="w-4 h-4" />
              <span>Thanh Toán</span>
            </Button>
          </div>

          <Button
            variant="primary"
            size="lg"
            className="w-full min-h-[48px] bg-emerald-600 hover:bg-emerald-500 font-bold"
            onClick={handleConfirmComplete}
            isLoading={actionLoading}
          >
            <CheckCircle2 className="w-5 h-5 mr-2" />
            <span>Xác Nhận Đã Hoàn Thành</span>
          </Button>

          <Button
            variant="secondary"
            size="sm"
            className="w-full text-xs text-red-400 border-red-500/30 hover:bg-red-950/30"
            onClick={handleDispute}
            disabled={actionLoading}
          >
            <AlertOctagon className="w-4 h-4 mr-1.5" />
            <span>Báo cáo sự cố / Khiếu nại</span>
          </Button>
        </div>
      )}

      {/* Completed Order Actions */}
      {order.status === "COMPLETED" && (
        <div className="p-5 bg-surface-card border border-emerald-500/40 rounded-3xl space-y-3 shadow-lg">
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="w-6 h-6" />
            <h3 className="font-bold text-white text-base">Đơn Hàng Đã Hoàn Tất</h3>
          </div>
          <p className="text-xs text-slate-300">
            Cảm ơn bạn đã tin dùng Fix 24/7. Bạn có thể xem lại hóa đơn, đánh giá chất lượng thợ hoặc gửi yêu cầu bảo hành nếu cần.
          </p>

          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="secondary"
              size="default"
              className="min-h-[44px] flex items-center justify-center gap-1.5"
              onClick={() => router.push(`/orders/${orderId}/invoice`)}
            >
              <Receipt className="w-4 h-4 text-brand-primary" />
              <span>Hóa Đơn</span>
            </Button>

            <Button
              variant="secondary"
              size="default"
              className="min-h-[44px] flex items-center justify-center gap-1.5 text-amber-300 border-amber-500/40 hover:bg-amber-950/20"
              onClick={() => router.push(`/orders/${orderId}/review`)}
            >
              <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
              <span>Đánh Giá Thợ</span>
            </Button>
          </div>

          <Button
            variant="secondary"
            size="default"
            className="w-full min-h-[44px] flex items-center justify-center gap-1.5 text-emerald-300 border-emerald-500/40 hover:bg-emerald-950/20"
            onClick={() => router.push(`/orders/${orderId}/warranty`)}
          >
            <ShieldAlert className="w-4 h-4" />
            <span>Yêu Cầu Bảo Hành</span>
          </Button>
        </div>
      )}

      {/* Warranty Mode Status */}
      {order.status === "WARRANTY" && (
        <div className="p-5 bg-amber-950/50 border border-amber-500/50 rounded-3xl space-y-3">
          <div className="flex items-center gap-2 text-amber-400">
            <ShieldAlert className="w-6 h-6" />
            <h3 className="font-bold text-white text-base">Đang Trong Chế Độ Bảo Hành</h3>
          </div>
          <p className="text-xs text-slate-300">
            Yêu cầu bảo hành của bạn đã được tiếp nhận và thông báo tới thợ kỹ thuật.
          </p>
          <div className="flex gap-2">
            <Button
              variant="primary"
              size="default"
              className="flex-1 min-h-[44px] bg-amber-600 hover:bg-amber-500"
              onClick={() => router.push(`/orders/${orderId}/warranty`)}
            >
              Xem Chi Tiết Bảo Hành
            </Button>
            <Button
              variant="secondary"
              size="default"
              className="min-h-[44px]"
              onClick={() => router.push(`/orders/${orderId}/invoice`)}
            >
              <Receipt className="w-4 h-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Disputed Status */}
      {order.status === "DISPUTED" && (
        <div className="p-5 bg-red-950/60 border-2 border-red-500 rounded-3xl space-y-2">
          <div className="flex items-center gap-2 text-red-400">
            <AlertOctagon className="w-6 h-6" />
            <h3 className="font-bold text-white text-base">Đơn Hàng Đang Tranh Chấp</h3>
          </div>
          <p className="text-xs text-red-200/90 leading-relaxed">
            Đơn hàng đã được chuyển tới ban quản trị Fix 24/7. Chúng tôi sẽ liên hệ cả khách hàng và thợ kỹ thuật trong vòng 2 giờ làm việc để giải quyết thỏa đáng.
          </p>
        </div>
      )}

      {/* Chat Panel */}
      <ChatPanel
        orderId={orderId}
        messages={messages}
        currentUserRole="customer"
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}

