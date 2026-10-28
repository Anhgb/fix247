"use client";

/**
 * Warranty Claim Page – FR-PAY-06
 * Allows customer to file warranty claim within 7 days (motorbike) / 30 days (home).
 */

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ShieldAlert,
  ShieldCheck,
  Camera,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toast";
import {
  ordersApi,
  WarrantyClaimCreate,
  WarrantyClaimResponse,
  InvoiceResponse,
  apiUpload,
} from "@/lib/api";

export default function WarrantyClaimPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params?.id as string;
  const { showToast } = useToast();

  const [existingClaims, setExistingClaims] = React.useState<WarrantyClaimResponse[]>([]);
  const [invoice, setInvoice] = React.useState<InvoiceResponse | null>(null);
  const [reason, setReason] = React.useState("");
  const [mediaUrls, setMediaUrls] = React.useState<string[]>([]);
  const [newUrl, setNewUrl] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(true);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [uploading, setUploading] = React.useState(false);

  React.useEffect(() => {
    async function loadData() {
      setIsLoading(true);
      const [claimRes, invRes] = await Promise.all([
        ordersApi.getWarranty(orderId),
        ordersApi.getInvoice(orderId),
      ]);

      if (claimRes.data) {
        if (Array.isArray(claimRes.data)) {
          setExistingClaims(claimRes.data);
        } else {
          setExistingClaims([claimRes.data]);
        }
      }

      if (invRes.data) {
        setInvoice(invRes.data);
      }
      setIsLoading(false);
    }
    loadData();
  }, [orderId]);

  const handleAddMedia = () => {
    if (!newUrl.trim()) return;
    setMediaUrls((prev) => [...prev, newUrl.trim()]);
    setNewUrl("");
  };

  const handleRemoveMedia = (index: number) => {
    setMediaUrls((prev) => prev.filter((_, i) => i !== index));
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    const { data, error } = await apiUpload<{ url?: string; file_url?: string }>(
      "/media/upload",
      formData
    );
    setUploading(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    const uploadedUrl = data?.url || data?.file_url;
    if (uploadedUrl) {
      setMediaUrls((prev) => [...prev, uploadedUrl]);
      showToast("Đã tải ảnh bằng chứng lên thành công.", "success");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (reason.trim().length < 5) {
      showToast("Vui lòng mô tả chi tiết sự cố cần bảo hành (tối thiểu 5 ký tự).", "error");
      return;
    }

    setIsSubmitting(true);
    const payload: WarrantyClaimCreate = {
      reason: reason.trim(),
      media_urls: mediaUrls,
    };

    const { data, error } = await ordersApi.submitWarranty(orderId, payload);
    setIsSubmitting(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast("Yêu cầu bảo hành đã được gửi đến thợ kỹ thuật!", "success");
    if (data) {
      setExistingClaims((prev) => [data, ...prev]);
    }
    setReason("");
    setMediaUrls([]);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <Loader2 className="w-8 h-8 animate-spin text-brand-primary" />
      </div>
    );
  }

  const warrantyDays = invoice?.warranty_days ?? 7;

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 max-w-lg mx-auto w-full space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => router.push(`/orders/${orderId}`)}
          className="h-10 w-10 p-0 rounded-full"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-xl font-black text-white">Yêu Cầu Bảo Hành</h1>
          <p className="text-xs text-slate-400 font-mono">Đơn #{orderId.slice(0, 8)}...</p>
        </div>
      </div>

      {/* Warranty policy reminder */}
      <div className="p-4 bg-emerald-950/40 border border-emerald-500/30 rounded-2xl flex items-start gap-3">
        <ShieldCheck className="w-6 h-6 text-emerald-400 flex-shrink-0 mt-0.5" />
        <div className="space-y-1 text-xs">
          <p className="font-bold text-white text-sm">Chính Sách Bảo Hành Fix 24/7</p>
          <p className="text-slate-300">
            Dịch vụ được bảo hành <strong className="text-emerald-400">{warrantyDays} ngày</strong> kể
            từ khi hoàn tất. Nếu thiết bị tái phát lỗi sau sửa chữa, thợ sẽ đến kiểm tra và khắc phục
            miễn phí.
          </p>
        </div>
      </div>

      {/* Active claims list */}
      {existingClaims.length > 0 && (
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-slate-300 flex items-center gap-2">
            <Clock className="w-4 h-4 text-sky-400" />
            Lịch Sử Khiếu Nại Bảo Hành
          </h2>
          <div className="space-y-2">
            {existingClaims.map((claim) => (
              <div
                key={claim.id}
                className="p-4 bg-surface-card border border-surface-border rounded-xl space-y-2"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-amber-400 uppercase tracking-wider">
                    {claim.status === "open"
                      ? "Đang xử lý"
                      : claim.status === "resolved"
                      ? "Đã xử lý"
                      : claim.status}
                  </span>
                  <span className="text-slate-500">
                    {new Date(claim.created_at).toLocaleDateString("vi-VN")}
                  </span>
                </div>
                <p className="text-sm text-slate-200">{claim.reason}</p>
                {claim.media_urls && claim.media_urls.length > 0 && (
                  <div className="flex gap-2 overflow-x-auto pt-1">
                    {claim.media_urls.map((url, i) => (
                      <a
                        key={i}
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-sky-400 underline truncate max-w-[150px]"
                      >
                        Ảnh #{i + 1}
                      </a>
                    ))}
                  </div>
                )}
                {claim.resolution_note && (
                  <div className="p-2 bg-surface-elevated rounded text-xs text-slate-300">
                    <strong className="text-emerald-400">Kết quả xử lý:</strong>{" "}
                    {claim.resolution_note}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Create claim form */}
      <form
        onSubmit={handleSubmit}
        className="p-5 bg-surface-card border border-surface-border rounded-2xl space-y-4"
      >
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <ShieldAlert className="w-5 h-5 text-amber-400" />
          Gửi Yêu Cầu Bảo Hành Mới
        </h2>

        <div className="space-y-1.5">
          <label className="text-xs font-semibold text-slate-300">
            Mô tả hiện tượng lỗi tái phát <span className="text-red-400">*</span>
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={4}
            className="w-full bg-surface-elevated border border-surface-border rounded-xl p-3 text-white text-sm focus:outline-none focus:border-brand-primary transition-colors placeholder:text-slate-500"
            placeholder="Ví dụ: Xe sau khi sửa chạy được 2 ngày lại bị tắt máy đột ngột khi giảm ga..."
            required
            minLength={5}
            maxLength={1000}
          />
          <div className="text-xs text-slate-500 text-right">{reason.length}/1000 ký tự</div>
        </div>

        {/* Media attachments */}
        <div className="space-y-2">
          <label className="text-xs font-semibold text-slate-300">
            Hình ảnh / Video sự cố (tùy chọn)
          </label>

          <div className="flex gap-2">
            <Input
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              placeholder="Dán link ảnh hoặc tải tệp..."
              className="text-xs h-10"
            />
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={handleAddMedia}
              className="h-10 px-3"
            >
              <Plus className="w-4 h-4" />
            </Button>
          </div>

          <div>
            <label className="inline-flex items-center gap-2 px-3 py-2 bg-surface-elevated border border-surface-border rounded-xl text-xs font-medium text-slate-300 cursor-pointer hover:bg-surface-border/50 transition-colors">
              <Camera className="w-4 h-4 text-sky-400" />
              <span>{uploading ? "Đang tải lên..." : "Chụp ảnh / Chọn tệp ảnh"}</span>
              <input
                type="file"
                accept="image/*"
                className="hidden"
                disabled={uploading}
                onChange={handleFileUpload}
              />
            </label>
          </div>

          {mediaUrls.length > 0 && (
            <div className="space-y-1.5 pt-2">
              {mediaUrls.map((url, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2 bg-surface-elevated rounded-lg text-xs"
                >
                  <span className="truncate max-w-[240px] text-slate-300">{url}</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveMedia(idx)}
                    className="text-red-400 hover:text-red-300 p-1"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="w-full min-h-[48px] font-bold bg-amber-600 hover:bg-amber-500 text-white"
          isLoading={isSubmitting}
        >
          <ShieldAlert className="w-5 h-5 mr-2" />
          Gửi Yêu Cầu Bảo Hành
        </Button>
      </form>
    </div>
  );
}

