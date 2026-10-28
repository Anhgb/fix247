"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Navigation,
  CheckCircle2,
  Plus,
  Trash2,
  AlertTriangle,
  Receipt,
  Wrench,
  Clock,
  MapPin,
  Camera,
  Wallet,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toast";
import { StatusTimeline } from "@/components/order/StatusTimeline";
import { ChatPanel, ChatMessageItem } from "@/components/order/ChatPanel";
import { apiRequest, apiUpload, ordersApi, techApi } from "@/lib/api";
import { createOrderStream, WSMessage } from "@/lib/ws";

interface LineItemForm {
  item_type: "labor" | "part";
  name: string;
  qty: number;
  unit_price: number;
  photo_url: string;
}

export default function TechnicianOrderDetailPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params?.id as string;
  const { showToast } = useToast();

  const [order, setOrder] = React.useState<any>(null);
  const [messages, setMessages] = React.useState<ChatMessageItem[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);
  const [actionLoading, setActionLoading] = React.useState(false);

  // Quote form state
  const [quoteItems, setQuoteItems] = React.useState<LineItemForm[]>([
    { item_type: "labor", name: "Công sửa chữa / xử lý sự cố", qty: 1, unit_price: 80000, photo_url: "" },
  ]);
  const [quoteReason, setQuoteReason] = React.useState("");

  // After-repair completion state
  const [photoAfterUrls, setPhotoAfterUrls] = React.useState<string[]>([]);
  const [summaryText, setSummaryText] = React.useState("");
  const [uploadingAfterPhoto, setUploadingAfterPhoto] = React.useState(false);

  // DIAG-9 feedback state
  const [diagLabel, setDiagLabel] = React.useState<"correct" | "partial" | "incorrect">("correct");
  const [diagNotes, setDiagNotes] = React.useState("");
  const [diagSubmitted, setDiagSubmitted] = React.useState(false);
  const [isSubmittingDiag, setIsSubmittingDiag] = React.useState(false);

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

  // Realtime updates
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("fix247_access_token") || "";

    const cleanup = createOrderStream(orderId, token, (msg: WSMessage) => {
      if (msg.type === "status") {
        setOrder((prev: any) => (prev ? { ...prev, status: msg.status } : prev));
        showToast(`Trạng thái đơn cập nhật: ${msg.status}`, "info");
      } else if (msg.type === "chat") {
        setMessages((prev) => {
          if (prev.some((m) => m.id === msg.message.id)) return prev;
          return [...prev, msg.message];
        });
      }
    });

    return () => cleanup();
  }, [orderId, showToast]);

  // Status transitions triggered by tech
  const handleTransitionStatus = async (toStatus: string, note?: string) => {
    setActionLoading(true);
    const { data, error } = await apiRequest<any>(`/orders/${orderId}/status`, {
      method: "POST",
      body: JSON.stringify({ to_status: toStatus, note }),
    });
    setActionLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    showToast(`Đã chuyển trạng thái: ${toStatus}`, "success");
    setOrder(data);
  };

  const handleUploadAfterPhoto = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadingAfterPhoto(true);
    const formData = new FormData();
    formData.append("file", file);

    const { data, error } = await apiUpload<{ url?: string; file_url?: string }>(
      "/media/upload",
      formData
    );
    setUploadingAfterPhoto(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    const uploadedUrl = data?.url || data?.file_url;
    if (uploadedUrl) {
      setPhotoAfterUrls((prev) => [...prev, uploadedUrl]);
      showToast("Đã tải ảnh chụp sau sửa thành công.", "success");
    }
  };

  const handleTechCompleteRepair = async () => {
    setActionLoading(true);
    const { data, error } = await ordersApi.techComplete(orderId, {
      photo_after_urls: photoAfterUrls,
      summary: summaryText.trim() || undefined,
    });
    setActionLoading(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast("Đã hoàn tất sửa chữa và gửi yêu cầu nghiệm thu đến khách hàng!", "success");
    setOrder(data);
  };

  // Add line item to quote
  const addQuoteItem = () => {
    setQuoteItems((prev) => [
      ...prev,
      { item_type: "part", name: "", qty: 1, unit_price: 50000, photo_url: "" },
    ]);
  };

  const removeQuoteItem = (idx: number) => {
    setQuoteItems((prev) => prev.filter((_, i) => i !== idx));
  };

  const updateQuoteItem = (idx: number, field: keyof LineItemForm, val: any) => {
    setQuoteItems((prev) =>
      prev.map((item, i) => (i === idx ? { ...item, [field]: val } : item))
    );
  };

  // Compute total
  const quoteTotal = React.useMemo(() => {
    return quoteItems.reduce((acc, it) => acc + (it.qty || 1) * (it.unit_price || 0), 0);
  }, [quoteItems]);

  const isOverThreshold = order?.est_max && order.est_max > 0 && quoteTotal > order.est_max * 1.2;

  // Submit quote
  const handleSubmitQuote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (quoteItems.length === 0) {
      showToast("Vui lòng thêm ít nhất một hạng mục báo giá.", "error");
      return;
    }

    // BR-10: check part > 100k
    for (const it of quoteItems) {
      if (it.item_type === "part" && it.unit_price > 100000 && !it.photo_url) {
        showToast(
          `Linh kiện '${it.name}' trên 100.000đ yêu cầu phải có ảnh đính kèm (BR-10).`,
          "error"
        );
        return;
      }
    }

    // BR-05: check reason if >20%
    if (isOverThreshold && !quoteReason.trim()) {
      showToast(
        "Báo giá vượt 20% giá tham khảo tối đa. Bắt buộc phải có lý do giải trình (BR-05).",
        "error"
      );
      return;
    }

    setActionLoading(true);
    const { data, error } = await apiRequest<any>(`/orders/${orderId}/quote`, {
      method: "POST",
      body: JSON.stringify({
        items: quoteItems,
        quote_reason: isOverThreshold ? quoteReason : undefined,
      }),
    });
    setActionLoading(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast("Đã gửi báo giá tới khách hàng thành công!", "success");
    setOrder(data);
  };

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
      setMessages((prev) => [...prev, data]);
    }
  };

  const handleSubmitDiagnosisFeedback = async () => {
    setIsSubmittingDiag(true);
    const { data, error } = await techApi.submitDiagnosisFeedback(orderId, {
      verified_label: diagLabel,
      notes: diagNotes.trim() || undefined,
    });
    setIsSubmittingDiag(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast("Đã ghi nhận đánh giá chẩn đoán AI (DIAG-9)!", "success");
    setDiagSubmitted(true);
  };

  if (isLoading || !order) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-sm text-slate-400">
        Đang tải thông tin đơn...
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 max-w-lg mx-auto w-full space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push("/tech/dashboard")}
            className="h-10 w-10 p-0 rounded-full"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-xl font-black text-white">Xử Lý Đơn Hàng</h1>
            <p className="text-xs text-slate-400 font-mono">#{order.id.slice(0, 8)}...</p>
          </div>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => router.push("/tech/wallet")}
          className="flex items-center gap-1.5 text-xs text-emerald-400 border-emerald-500/40"
        >
          <Wallet className="w-4 h-4" />
          <span>Ví Thợ</span>
        </Button>
      </div>

      {/* Status timeline */}
      <div className="p-4 bg-surface-card border border-surface-border rounded-2xl shadow-md">
        <StatusTimeline status={order.status} />
      </div>

      {/* Customer Location Info */}
      <div className="p-4 bg-surface-card border border-surface-border rounded-2xl space-y-2 text-xs">
        <span className="font-bold text-white block text-sm">Thông tin điểm hẹn:</span>
        <p className="text-slate-300 flex items-start gap-1.5 leading-relaxed">
          <MapPin className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
          <span>{order.address}</span>
        </p>
        {order.customer_note && (
          <p className="text-slate-400 italic bg-surface-elevated p-2.5 rounded-xl">
            Ghi chú từ khách: &ldquo;{order.customer_note}&rdquo;
          </p>
        )}
      </div>

      {/* Workflow Action Buttons for Technician */}
      {order.status === "ACCEPTED" && (
        <Button
          variant="primary"
          size="lg"
          className="w-full min-h-[48px] font-bold text-base bg-sky-600 hover:bg-sky-500 shadow-lg"
          onClick={() => handleTransitionStatus("ON_THE_WAY", "Thợ đã xuất phát")}
          isLoading={actionLoading}
        >
          <Navigation className="w-5 h-5 mr-2" />
          <span>XUẤT PHÁT ĐẾN ĐIỂM HẸN</span>
        </Button>
      )}

      {order.status === "ON_THE_WAY" && (
        <Button
          variant="primary"
          size="lg"
          className="w-full min-h-[48px] font-bold text-base bg-indigo-600 hover:bg-indigo-500 shadow-lg"
          onClick={() => handleTransitionStatus("SURVEYING", "Thợ đã đến nơi và bắt đầu khảo sát")}
          isLoading={actionLoading}
        >
          <Wrench className="w-5 h-5 mr-2" />
          <span>ĐÃ ĐẾN NƠI & BẮT ĐẦU KHẢO SÁT</span>
        </Button>
      )}

      {/* Quote Creation Form (When SURVEYING) */}
      {order.status === "SURVEYING" && (
        <form
          onSubmit={handleSubmitQuote}
          className="p-5 bg-surface-card border-2 border-brand-500/50 rounded-3xl space-y-4 shadow-xl"
        >
          <div className="flex items-center justify-between border-b border-surface-border pb-3">
            <div>
              <h3 className="text-base font-bold text-white flex items-center gap-1.5">
                <Receipt className="w-5 h-5 text-brand-400" />
                <span>Lập Báo Giá Khảo Sát</span>
              </h3>
              <p className="text-xs text-slate-400">Nhập các hạng mục công và linh kiện</p>
            </div>
            {order.est_max && (
              <span className="text-[11px] text-amber-400 text-right">
                Giá trần tham khảo: {order.est_max.toLocaleString("vi-VN")}đ
              </span>
            )}
          </div>

          <div className="space-y-3">
            {quoteItems.map((item, idx) => (
              <div
                key={idx}
                className="p-3 bg-surface-elevated border border-surface-border rounded-2xl space-y-2 text-xs"
              >
                <div className="flex items-center justify-between">
                  <select
                    value={item.item_type}
                    onChange={(e) => updateQuoteItem(idx, "item_type", e.target.value)}
                    className="bg-surface-card border border-surface-border rounded-lg px-2 py-1 text-slate-200"
                  >
                    <option value="labor">Tiền công</option>
                    <option value="part">Linh kiện</option>
                  </select>

                  {quoteItems.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeQuoteItem(idx)}
                      className="text-red-400 hover:text-red-300 p-1"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <Input
                  label="Tên hạng mục / linh kiện"
                  value={item.name}
                  onChange={(e) => updateQuoteItem(idx, "name", e.target.value)}
                  placeholder="Ví dụ: Thay bugi NGK, Vá lốp xe..."
                  required
                />

                <div className="grid grid-cols-2 gap-2">
                  <Input
                    label="Số lượng"
                    type="number"
                    min={1}
                    value={item.qty.toString()}
                    onChange={(e) => updateQuoteItem(idx, "qty", parseInt(e.target.value) || 1)}
                    required
                  />
                  <Input
                    label="Đơn giá (VND)"
                    type="number"
                    step={5000}
                    value={item.unit_price.toString()}
                    onChange={(e) =>
                      updateQuoteItem(idx, "unit_price", parseInt(e.target.value) || 0)
                    }
                    required
                  />
                </div>

                {item.item_type === "part" && item.unit_price > 100000 && (
                  <Input
                    label="Ảnh linh kiện (Bắt buộc >100k per BR-10)"
                    value={item.photo_url}
                    onChange={(e) => updateQuoteItem(idx, "photo_url", e.target.value)}
                    placeholder="URL ảnh hoặc link tải lên..."
                    required
                  />
                )}
              </div>
            ))}

            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={addQuoteItem}
              className="w-full text-xs min-h-[40px]"
            >
              <Plus className="w-4 h-4 mr-1" />
              <span>Thêm Hạng Mục</span>
            </Button>
          </div>

          {/* Threshold check warning */}
          {isOverThreshold && (
            <div className="p-3 bg-amber-950/60 border border-amber-500/50 rounded-2xl space-y-2 text-xs text-amber-300">
              <div className="flex items-center gap-1.5 font-bold">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span>Báo giá vượt &gt;20% giá tham khảo tối đa (BR-05)</span>
              </div>
              <textarea
                value={quoteReason}
                onChange={(e) => setQuoteReason(e.target.value)}
                placeholder="Bắt buộc nhập lý do giải trình vì sao chi phí cao hơn tham khảo..."
                rows={2}
                required
                className="w-full bg-surface-card border border-surface-border rounded-xl p-2.5 text-xs text-white focus:outline-none focus:border-amber-400"
              />
            </div>
          )}

          {/* Total & Submit */}
          <div className="pt-2 border-t border-surface-border flex items-center justify-between">
            <span className="text-xs text-slate-300">Tổng báo giá:</span>
            <span className="text-lg font-black text-brand-400">
              {quoteTotal.toLocaleString("vi-VN")} đ
            </span>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full min-h-[48px] font-bold"
            isLoading={actionLoading}
          >
            <span>GỬI BÁO GIÁ CHO KHÁCH</span>
          </Button>
        </form>
      )}

      {order.status === "QUOTE_PENDING" && (
        <div className="p-4 bg-yellow-950/40 border border-yellow-500/40 rounded-2xl text-center text-xs text-yellow-300 space-y-1">
          <p className="font-bold">Đã gửi báo giá thành công!</p>
          <p className="text-slate-300">Đang chờ khách hàng xem xét và chấp nhận báo giá...</p>
        </div>
      )}

      {order.status === "IN_REPAIR" && (
        <div className="p-5 bg-surface-card border border-purple-500/40 rounded-2xl space-y-4">
          <div className="flex items-center gap-2 text-purple-300">
            <Wrench className="w-5 h-5" />
            <h3 className="font-bold text-white text-base">Đang Tiến Hành Sửa Chữa</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Khách hàng đã duyệt báo giá. Hãy tiến hành sửa chữa theo đúng quy chuẩn. Sau khi hoàn thành, chụp ảnh thiết bị sau sửa và gửi nghiệm thu (UC-06).
          </p>

          {/* Photo after upload */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-slate-300">
              Ảnh chụp thiết bị sau khi sửa xong (Tối thiểu 1 ảnh)
            </label>
            <div>
              <label className="inline-flex items-center gap-2 px-3 py-2 bg-surface-elevated border border-surface-border rounded-xl text-xs font-medium text-slate-300 cursor-pointer hover:bg-surface-border/50 transition-colors">
                <Camera className="w-4 h-4 text-sky-400" />
                <span>{uploadingAfterPhoto ? "Đang tải ảnh..." : "Chụp / Tải ảnh sau sửa"}</span>
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  disabled={uploadingAfterPhoto}
                  onChange={handleUploadAfterPhoto}
                />
              </label>
            </div>

            {photoAfterUrls.length > 0 && (
              <div className="flex gap-2 overflow-x-auto pt-1">
                {photoAfterUrls.map((url, idx) => (
                  <div key={idx} className="relative group shrink-0">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={url}
                      alt={`Ảnh sau sửa ${idx + 1}`}
                      className="w-16 h-16 object-cover rounded-lg border border-surface-border"
                    />
                    <button
                      type="button"
                      onClick={() => setPhotoAfterUrls((prev) => prev.filter((_, i) => i !== idx))}
                      className="absolute -top-1.5 -right-1.5 bg-red-600 text-white rounded-full p-0.5 text-xs"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">
              Ghi chú công việc đã thực hiện (tùy chọn)
            </label>
            <Input
              value={summaryText}
              onChange={(e) => setSummaryText(e.target.value)}
              placeholder="Ví dụ: Đã thay bugi mới, căn chỉnh lại garanti và chạy thử êm..."
              className="text-xs"
            />
          </div>

          <Button
            variant="primary"
            size="lg"
            className="w-full min-h-[48px] font-bold text-base bg-emerald-600 hover:bg-emerald-500"
            onClick={handleTechCompleteRepair}
            isLoading={actionLoading}
          >
            <CheckCircle2 className="w-5 h-5 mr-2" />
            <span>ĐÃ SỬA XONG & GỬI NGHIỆM THU</span>
          </Button>
        </div>
      )}

      {order.status === "AWAITING_CONFIRM" && (
        <div className="p-5 bg-surface-card border border-amber-500/40 rounded-2xl space-y-3">
          <div className="flex items-center gap-2 text-amber-400">
            <Clock className="w-5 h-5" />
            <h3 className="font-bold text-white text-base">Đang Chờ Khách Nghiệm Thu & Thanh Toán</h3>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Bạn đã báo hoàn thành đơn hàng. Đơn sẽ tự động xác nhận hoàn tất sau 24h nếu khách không khiếu nại (BR-08).
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="default"
              className="flex-1 min-h-[44px]"
              onClick={() => router.push(`/orders/${orderId}/invoice`)}
            >
              <Receipt className="w-4 h-4 mr-1.5 text-brand-primary" />
              <span>Xem Hóa Đơn</span>
            </Button>
            <Button
              variant="secondary"
              size="default"
              className="flex-1 min-h-[44px] text-emerald-400 border-emerald-500/40"
              onClick={() => router.push("/tech/wallet")}
            >
              <Wallet className="w-4 h-4 mr-1.5" />
              <span>Ví Thợ</span>
            </Button>
          </div>
        </div>
      )}

      {order.status === "COMPLETED" && (
        <div className="p-5 bg-surface-card border border-emerald-500/40 rounded-2xl space-y-3">
          <div className="flex items-center gap-2 text-emerald-400">
            <CheckCircle2 className="w-5 h-5" />
            <h3 className="font-bold text-white text-base">Đơn Hàng Đã Hoàn Tất</h3>
          </div>
          <p className="text-xs text-slate-300">
            Đơn hàng đã được nghiệm thu và ghi nhận hoa hồng nền tảng vào ví thợ.
          </p>
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="default"
              className="flex-1 min-h-[44px]"
              onClick={() => router.push(`/orders/${orderId}/invoice`)}
            >
              <Receipt className="w-4 h-4 mr-1.5 text-brand-primary" />
              <span>Xem Hóa Đơn</span>
            </Button>
            <Button
              variant="secondary"
              size="default"
              className="flex-1 min-h-[44px] text-emerald-400 border-emerald-500/40"
              onClick={() => router.push("/tech/wallet")}
            >
              <Wallet className="w-4 h-4 mr-1.5" />
              <span>Ví & Đối Soát</span>
            </Button>
          </div>
        </div>
      )}

      {/* DIAG-9 Feedback Section (Optional for Technician after job) */}
      {(order.status === "AWAITING_CONFIRM" || order.status === "COMPLETED") && (
        <div className="p-4 bg-surface-card border border-brand-500/30 rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-brand-400 font-bold text-sm">
              <Sparkles className="w-4 h-4" />
              <span>Đánh Giá Độ Chính Xác Chẩn Đoán AI (DIAG-9)</span>
            </div>
            {diagSubmitted && (
              <span className="text-[11px] font-bold text-emerald-400 bg-emerald-950/70 border border-emerald-500/30 px-2 py-0.5 rounded-full flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Đã gửi
              </span>
            )}
          </div>

          <p className="text-xs text-slate-300 leading-relaxed">
            Kết quả thực tế khi kiểm tra tại hiện trường so với phỏng đoán ban đầu của AI:
          </p>

          {!diagSubmitted ? (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-1.5">
                <button
                  type="button"
                  onClick={() => setDiagLabel("correct")}
                  className={`p-2.5 rounded-xl border text-xs font-semibold text-center transition min-h-[44px] ${
                    diagLabel === "correct"
                      ? "bg-emerald-950/80 border-emerald-500 text-emerald-300 ring-2 ring-emerald-500/20"
                      : "bg-surface-elevated border-surface-border text-slate-400"
                  }`}
                >
                  Chính xác 100%
                </button>
                <button
                  type="button"
                  onClick={() => setDiagLabel("partial")}
                  className={`p-2.5 rounded-xl border text-xs font-semibold text-center transition min-h-[44px] ${
                    diagLabel === "partial"
                      ? "bg-amber-950/80 border-amber-500 text-amber-300 ring-2 ring-amber-500/20"
                      : "bg-surface-elevated border-surface-border text-slate-400"
                  }`}
                >
                  Đúng một phần
                </button>
                <button
                  type="button"
                  onClick={() => setDiagLabel("incorrect")}
                  className={`p-2.5 rounded-xl border text-xs font-semibold text-center transition min-h-[44px] ${
                    diagLabel === "incorrect"
                      ? "bg-red-950/80 border-red-500 text-red-300 ring-2 ring-red-500/20"
                      : "bg-surface-elevated border-surface-border text-slate-400"
                  }`}
                >
                  Sai lệch
                </button>
              </div>

              <Input
                value={diagNotes}
                onChange={(e) => setDiagNotes(e.target.value)}
                placeholder="Ghi chú thêm về lỗi thực tế (tùy chọn)..."
                className="text-xs"
              />

              <Button
                type="button"
                variant="secondary"
                size="default"
                className="w-full min-h-[44px] text-xs font-bold"
                onClick={handleSubmitDiagnosisFeedback}
                isLoading={isSubmittingDiag}
              >
                Gửi Phản Hồi Chẩn Đoán AI
              </Button>
            </div>
          ) : (
            <p className="text-xs text-emerald-400 italic">
              Cảm ơn phản hồi của bạn! Dữ liệu này giúp mô hình AI nâng cao độ tin cậy và định giá chính xác hơn.
            </p>
          )}
        </div>
      )}

      {/* Chat panel */}
      <ChatPanel
        orderId={orderId}
        messages={messages}
        currentUserRole="technician"
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}
