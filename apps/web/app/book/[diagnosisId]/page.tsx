"use client";

import * as React from "react";
import { useRouter, useParams } from "next/navigation";
import {
  AlertOctagon,
  Calendar,
  MapPin,
  Clock,
  ArrowLeft,
  ShieldCheck,
  Moon,
  Info,
  Bike,
  Tv,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { LeafletMap } from "@/components/map/LeafletMap";
import { apiRequest, assetsApi, AssetResponse } from "@/lib/api";

export default function BookOrderPage() {
  const router = useRouter();
  const params = useParams();
  const diagnosisId = params?.diagnosisId as string;
  const { showToast } = useToast();

  const [mode, setMode] = React.useState<"emergency" | "scheduled">("emergency");
  const [address, setAddress] = React.useState("Số 123 Đường Hùng Vương, P. Phú Nhuận, TP. Huế");
  const [lat, setLat] = React.useState(16.4637);
  const [lng, setLng] = React.useState(107.5909);
  const [note, setNote] = React.useState("");
  const [scheduledAt, setScheduledAt] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);
  const [diagnosisData, setDiagnosisData] = React.useState<any>(null);
  const [userAssets, setUserAssets] = React.useState<AssetResponse[]>([]);
  const [selectedAssetId, setSelectedAssetId] = React.useState<string>("");

  // Load user assets
  React.useEffect(() => {
    assetsApi.list().then(({ data }) => {
      if (data) setUserAssets(data.items);
    });
  }, []);

  // Night surcharge detection (BR-04: 22:00 - 05:00)
  const isNight = React.useMemo(() => {
    const hour = new Date().getHours();
    return hour >= 22 || hour < 5;
  }, []);

  // Fetch diagnosis if available
  React.useEffect(() => {
    if (diagnosisId && diagnosisId !== "direct") {
      apiRequest(`/diagnoses/${diagnosisId}`).then(({ data }: any) => {
        if (data) {
          setDiagnosisData(data);
          if (data.asset_id) {
            setSelectedAssetId(data.asset_id);
          }
        }
      });
    }

    // Attempt GPS
    if (typeof window !== "undefined" && "geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLat(pos.coords.latitude);
          setLng(pos.coords.longitude);
        },
        () => {},
        { timeout: 5000 }
      );
    }
  }, [diagnosisId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      const payload: any = {
        mode,
        diagnosis_id: diagnosisId !== "direct" ? diagnosisId : null,
        asset_id: selectedAssetId || undefined,
        location: {
          lat,
          lng,
          address,
        },
        note: note || undefined,
      };

      if (mode === "scheduled") {
        if (!scheduledAt) {
          showToast("Vui lòng chọn thời gian hẹn.", "error");
          setIsLoading(false);
          return;
        }
        payload.scheduled_at = new Date(scheduledAt).toISOString();
      }

      const { data, error } = await apiRequest<any>("/orders", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (error) {
        showToast(error.message, "error");
        setIsLoading(false);
        return;
      }

      showToast("Tạo đơn thành công! Đang chuyển hướng...", "success");
      router.push(`/orders/${data.id}`);
    } catch (err) {
      showToast("Có lỗi xảy ra khi tạo đơn.", "error");
      setIsLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 max-w-lg mx-auto w-full space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => router.back()}
          className="h-10 w-10 p-0 rounded-full"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-xl font-black text-white">Xác Nhận Đặt Thợ</h1>
          <p className="text-xs text-slate-400">TP. Huế – Định vị GPS & điều phối nhanh</p>
        </div>
      </div>

      {/* Diagnosis recap if available */}
      {diagnosisData && (
        <div className="p-3.5 bg-surface-card border border-brand-500/40 rounded-2xl flex items-center justify-between">
          <div>
            <span className="text-[10px] font-bold text-brand-400 uppercase tracking-wider block">
              Kết quả chẩn đoán AI
            </span>
            <p className="text-sm font-bold text-white">
              {diagnosisData.candidates?.[0]?.name || "Sự cố thiết bị"}
            </p>
          </div>
          {diagnosisData.candidates?.[0]?.price_range && (
            <div className="text-right">
              <span className="text-xs font-bold text-emerald-400 block">
                {diagnosisData.candidates[0].price_range.min?.toLocaleString("vi-VN")} -{" "}
                {diagnosisData.candidates[0].price_range.max?.toLocaleString("vi-VN")} đ
              </span>
              <span className="text-[10px] text-slate-400">Giá niêm yết</span>
            </div>
          )}
        </div>
      )}

      {/* Mode Selector */}
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          onClick={() => setMode("emergency")}
          className={`p-3.5 rounded-2xl border-2 flex flex-col items-center text-center transition ${
            mode === "emergency"
              ? "bg-emergency-950/70 border-emergency-500 text-white shadow-lg shadow-emergency-950/40"
              : "bg-surface-card border-surface-border text-slate-400 hover:text-white"
          }`}
        >
          <AlertOctagon className={`w-6 h-6 mb-1 ${mode === "emergency" ? "text-emergency-400" : ""}`} />
          <span className="text-sm font-black">Cứu Hộ Khẩn Cấp</span>
          <span className="text-[11px] mt-0.5 opacity-80">Thợ đến 10 - 20 phút</span>
        </button>

        <button
          type="button"
          onClick={() => setMode("scheduled")}
          className={`p-3.5 rounded-2xl border-2 flex flex-col items-center text-center transition ${
            mode === "scheduled"
              ? "bg-brand-950/70 border-brand-500 text-white shadow-lg shadow-brand-950/40"
              : "bg-surface-card border-surface-border text-slate-400 hover:text-white"
          }`}
        >
          <Calendar className={`w-6 h-6 mb-1 ${mode === "scheduled" ? "text-brand-400" : ""}`} />
          <span className="text-sm font-black">Đặt Lịch Hẹn</span>
          <span className="text-[11px] mt-0.5 opacity-80">07:00 - 21:00 hàng ngày</span>
        </button>
      </div>

      {/* Night surcharge alert (BR-04) */}
      {mode === "emergency" && isNight && (
        <div className="p-3 bg-amber-950/50 border border-amber-500/40 rounded-2xl flex items-center gap-2.5 text-xs text-amber-300">
          <Moon className="w-5 h-5 text-amber-400 shrink-0" />
          <div>
            <span className="font-bold block">Phụ thu khẩn cấp ban đêm: +15.000đ</span>
            <span className="text-[11px] text-slate-300">Áp dụng khung giờ 22:00 - 05:00 (100% trả cho thợ).</span>
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Map preview */}
        <div className="space-y-1.5">
          <label className="text-xs font-bold text-slate-300 flex items-center gap-1.5">
            <MapPin className="w-4 h-4 text-brand-400" />
            <span>Vị trí trên bản đồ (OpenStreetMap / Leaflet)</span>
          </label>
          <LeafletMap
            center={[lat, lng]}
            zoom={15}
            markers={[
              {
                id: "customer",
                position: [lat, lng],
                icon: "customer",
                popup: "Vị trí của bạn",
              },
            ]}
          />
        </div>

        <Input
          label="Địa chỉ chi tiết"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          placeholder="Số nhà, tên đường, phường..."
          required
        />

        {mode === "scheduled" && (
          <div className="space-y-1">
            <label className="text-xs font-bold text-slate-300">
              Thời gian hẹn (07:00 - 21:00, sau ít nhất 2h)
            </label>
            <input
              type="datetime-local"
              value={scheduledAt}
              onChange={(e) => setScheduledAt(e.target.value)}
              required
              className="w-full bg-surface-card border border-surface-border rounded-xl px-3.5 py-3 text-sm text-white focus:outline-none focus:border-brand-500"
            />
          </div>
        )}

        {/* Digital Health Log Asset Selector (FR-HEALTH-01) */}
        {userAssets.length > 0 && (
          <div className="p-3 bg-surface-card border border-surface-border rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-brand-400" />
                <span>Ghi nhật ký vào Sổ Sức Khỏe thiết bị:</span>
              </label>
              <Link
                href="/assets"
                className="text-[11px] text-brand-primary hover:text-brand-400 font-medium"
              >
                Quản lý thiết bị
              </Link>
            </div>
            <select
              value={selectedAssetId}
              onChange={(e) => setSelectedAssetId(e.target.value)}
              className="w-full p-2.5 bg-surface-elevated border border-surface-border rounded-xl text-xs text-white focus:outline-none focus:border-brand-500"
            >
              <option value="">-- Không liên kết với thiết bị nào --</option>
              {userAssets.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  {asset.asset_type === "vehicle" ? "🛵" : "🏠"} {asset.brand} {asset.model}{" "}
                  {asset.plate_or_serial ? `[${asset.plate_or_serial}]` : ""}
                </option>
              ))}
            </select>
            <p className="text-[11px] text-slate-400">
              Sau khi sửa chữa hoàn tất, chi phí và phụ tùng sẽ tự động lưu vào Sổ sức khỏe của thiết bị này.
            </p>
          </div>
        )}

        <div className="space-y-1">
          <label className="text-xs font-bold text-slate-300">
            Ghi chú thêm cho thợ (Không bắt buộc)
          </label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Mô tả cụ thể vị trí hoặc tình trạng xe/thiết bị..."
            rows={3}
            className="w-full bg-surface-card border border-surface-border rounded-xl p-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        <Button
          type="submit"
          variant={mode === "emergency" ? "emergency" : "primary"}
          size="lg"
          className="w-full min-h-[48px] font-bold text-base shadow-xl"
          isLoading={isLoading}
        >
          {mode === "emergency" ? "XÁC NHẬN GỌI THỢ NGAY" : "XÁC NHẬN ĐẶT LỊCH HẸN"}
        </Button>
      </form>
    </div>
  );
}

