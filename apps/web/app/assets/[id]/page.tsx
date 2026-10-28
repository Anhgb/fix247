"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Bike,
  Tv,
  Wrench,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Receipt,
  User,
  Calendar,
  Sparkles,
  ExternalLink,
  Edit2,
  Trash2,
  ShieldCheck,
  Package,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { useToast } from "@/components/ui/Toast";
import { assetsApi, AssetResponse, AssetCreate } from "@/lib/api";

export default function AssetDetailPage() {
  const params = useParams();
  const router = useRouter();
  const assetId = params?.id as string;
  const { showToast } = useToast();

  const [asset, setAsset] = React.useState<AssetResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [showEditModal, setShowEditModal] = React.useState(false);
  const [isUpdating, setIsUpdating] = React.useState(false);

  // Edit fields
  const [brand, setBrand] = React.useState("");
  const [model, setModel] = React.useState("");
  const [year, setYear] = React.useState("");
  const [plateOrSerial, setPlateOrSerial] = React.useState("");
  const [locationLabel, setLocationLabel] = React.useState("");
  const [notes, setNotes] = React.useState("");

  const loadAsset = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await assetsApi.get(assetId);
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setAsset(data);
      setBrand(data.brand || "");
      setModel(data.model || "");
      setYear(data.year ? String(data.year) : "");
      setPlateOrSerial(data.plate_or_serial || "");
      setLocationLabel(data.location_label || "");
      setNotes(data.notes || "");
    }
  }, [assetId, showToast]);

  React.useEffect(() => {
    loadAsset();
  }, [loadAsset]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsUpdating(true);
    const payload: Partial<AssetCreate> = {
      brand: brand.trim(),
      model: model.trim(),
      year: year ? parseInt(year, 10) : undefined,
      plate_or_serial: plateOrSerial.trim() || undefined,
      location_label: locationLabel.trim() || undefined,
      notes: notes.trim() || undefined,
    };

    const { error } = await assetsApi.update(assetId, payload);
    setIsUpdating(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast("Cập nhật thông tin thành công!", "success");
    setShowEditModal(false);
    loadAsset();
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "--";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat("vi-VN").format(amount) + " đ";
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-4">
        <div className="w-10 h-10 border-4 border-brand-primary border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-xs text-slate-400">Đang tải nhật ký sức khỏe...</p>
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center space-y-4">
        <AlertTriangle className="w-12 h-12 text-amber-400" />
        <h2 className="text-lg font-bold text-white">Không Tìm Thấy Thiết Bị</h2>
        <Button variant="secondary" size="default" onClick={() => router.push("/assets")}>
          Quay lại danh bạ
        </Button>
      </div>
    );
  }

  const isVehicle = asset.asset_type === "vehicle";
  const title = `${asset.brand || ""} ${asset.model || ""}`.trim();

  return (
    <div className="flex-1 flex flex-col p-4 pb-16 space-y-5">
      {/* Top Header */}
      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-3">
          <Link
            href="/assets"
            className="p-2 min-h-[44px] min-w-[44px] rounded-xl bg-surface-card border border-surface-border text-slate-300 hover:text-white flex items-center justify-center"
            aria-label="Quay lại danh bạ thiết bị"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              <span>Nhật Ký Sức Khỏe</span>
              <Sparkles className="w-4 h-4 text-brand-400" />
            </h1>
            <p className="text-xs text-slate-400">Lịch sử bảo dưỡng & thay thế linh kiện</p>
          </div>
        </div>

        <Button
          variant="secondary"
          size="default"
          className="min-h-[44px] text-xs font-semibold"
          onClick={() => setShowEditModal(true)}
        >
          <Edit2 className="w-3.5 h-3.5 mr-1" />
          <span>Sửa</span>
        </Button>
      </div>

      {/* Asset Info Card */}
      <Card className="bg-gradient-to-br from-surface-elevated via-surface-card to-surface-card border-surface-border">
        <CardContent className="p-4 space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`w-12 h-12 rounded-2xl flex items-center justify-center shrink-0 ${
                  isVehicle
                    ? "bg-amber-950/70 text-amber-400 border border-amber-500/30"
                    : "bg-sky-950/70 text-sky-400 border border-sky-500/30"
                }`}
              >
                {isVehicle ? <Bike className="w-7 h-7" /> : <Tv className="w-7 h-7" />}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-lg font-bold text-white">{title}</h2>
                  {asset.year && <span className="text-xs text-slate-400">({asset.year})</span>}
                </div>
                <p className="text-xs text-slate-400">
                  {isVehicle ? "🛵 Xe máy" : "🏠 Thiết bị gia đình"}
                  {asset.plate_or_serial && ` • ${asset.plate_or_serial}`}
                </p>
                {asset.location_label && (
                  <p className="text-[11px] text-slate-400 mt-0.5">Vị trí: {asset.location_label}</p>
                )}
              </div>
            </div>

            <div>
              {asset.health_status === "good" ? (
                <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-950/70 border border-emerald-500/30 px-2.5 py-1 rounded-full">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Tốt
                </span>
              ) : asset.health_status === "due_soon" ? (
                <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-400 bg-amber-950/70 border border-amber-500/30 px-2.5 py-1 rounded-full">
                  <Clock className="w-3.5 h-3.5" />
                  Sắp Đến Hạn
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-xs font-bold text-red-400 bg-red-950/70 border border-red-500/30 px-2.5 py-1 rounded-full">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  Cần Bảo Dưỡng
                </span>
              )}
            </div>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-surface-border text-center">
            <div className="p-2.5 bg-surface-card rounded-xl">
              <span className="text-[11px] text-slate-400 block">Số lần sửa chữa/bảo dưỡng</span>
              <strong className="text-sm font-bold text-white">
                {asset.maintenance_count} lần
              </strong>
            </div>
            <div className="p-2.5 bg-surface-card rounded-xl">
              <span className="text-[11px] text-slate-400 block">Lần cuối bảo dưỡng</span>
              <strong className="text-xs font-bold text-slate-200">
                {formatDate(asset.last_maintained_at)}
              </strong>
            </div>
          </div>

          {/* Notes if any */}
          {asset.notes && (
            <p className="text-xs text-slate-400 italic bg-surface-card/60 p-2.5 rounded-xl border border-surface-border/50">
              Ghi chú: {asset.notes}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Reminders section */}
      {asset.reminders && asset.reminders.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
            <Clock className="w-4 h-4 text-amber-400" />
            <span>Nhắc Nhở Bảo Dưỡng Định Kỳ (FR-HEALTH-02)</span>
          </h3>
          <div className="space-y-2">
            {asset.reminders.map((rem, idx) => (
              <div
                key={idx}
                className="p-3.5 bg-amber-950/30 border border-amber-500/40 rounded-2xl flex items-start gap-3"
              >
                <div className="w-8 h-8 rounded-xl bg-amber-500/20 text-amber-400 flex items-center justify-center shrink-0 mt-0.5">
                  <AlertTriangle className="w-4 h-4" />
                </div>
                <div className="flex-1 space-y-1">
                  <h4 className="text-xs font-bold text-amber-300">{rem.title}</h4>
                  <p className="text-xs text-slate-300 leading-relaxed">{rem.message}</p>
                  {rem.due_date && (
                    <span className="text-[11px] text-slate-400 block">
                      Hạn: {formatDate(rem.due_date)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Maintenance Timeline */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
          <Calendar className="w-4 h-4 text-brand-400" />
          <span>Lịch Sử Sửa Chữa & Bảo Dưỡng ({asset.recent_logs?.length || 0})</span>
        </h3>

        {!asset.recent_logs || asset.recent_logs.length === 0 ? (
          <div className="p-8 text-center bg-surface-card border border-surface-border rounded-2xl space-y-2">
            <Wrench className="w-10 h-10 text-slate-500 mx-auto" />
            <p className="text-sm font-bold text-white">Chưa có nhật ký bảo dưỡng nào</p>
            <p className="text-xs text-slate-400 max-w-xs mx-auto">
              Khi bạn đặt lịch sửa chữa qua Fix 24/7 và đơn hoàn thành, thợ sẽ tự động cập nhật
              nhật ký chi tiết vào đây.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {asset.recent_logs.map((log) => (
              <Card key={log.id} className="bg-surface-card border-surface-border overflow-hidden">
                <CardContent className="p-4 space-y-3">
                  {/* Log Header */}
                  <div className="flex items-start justify-between border-b border-surface-border pb-2.5">
                    <div>
                      <span className="text-xs text-slate-400 block">Thời gian thực hiện</span>
                      <strong className="text-sm font-bold text-white">
                        {formatDate(log.performed_at)}
                      </strong>
                    </div>

                    <div className="text-right">
                      <span className="text-xs text-slate-400 block">Tổng thanh toán</span>
                      <strong className="text-sm font-bold text-brand-400">
                        {formatVND(log.total_cost)}
                      </strong>
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="space-y-1">
                    <span className="text-xs font-semibold text-slate-300">Nội dung công việc:</span>
                    <p className="text-xs text-slate-200 bg-surface-elevated/70 p-2.5 rounded-xl leading-relaxed">
                      {log.summary}
                    </p>
                  </div>

                  {/* Parts replaced */}
                  {log.parts_replaced && log.parts_replaced.length > 0 && (
                    <div className="space-y-1.5">
                      <span className="text-xs font-semibold text-slate-300 flex items-center gap-1">
                        <Package className="w-3.5 h-3.5 text-slate-400" />
                        <span>Phụ tùng thay thế:</span>
                      </span>
                      <div className="space-y-1 bg-surface-elevated/40 p-2.5 rounded-xl border border-surface-border/50 text-xs">
                        {log.parts_replaced.map((part, pIdx) => (
                          <div key={pIdx} className="flex justify-between items-center text-slate-300">
                            <span>
                              • {part.name} (x{part.qty})
                            </span>
                            <span className="font-medium text-slate-200">
                              {formatVND(part.qty * part.unit_price)}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Footer details: technician & order link */}
                  <div className="pt-2 border-t border-surface-border/60 flex items-center justify-between text-xs text-slate-400">
                    <div className="flex items-center gap-1.5">
                      <User className="w-3.5 h-3.5 text-slate-500" />
                      <span>Thợ: </span>
                      <strong className="text-slate-300">
                        {log.technician_name || "Thợ Fix 24/7"}
                      </strong>
                    </div>

                    {log.order_id && (
                      <Link
                        href={`/orders/${log.order_id}`}
                        className="inline-flex items-center gap-1 text-brand-primary hover:text-brand-400 font-medium"
                      >
                        <Receipt className="w-3.5 h-3.5" />
                        <span>Xem đơn hàng</span>
                      </Link>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Edit Modal */}
      <BottomSheet
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title="Cập Nhật Thông Tin Thiết Bị"
      >
        <form onSubmit={handleUpdate} className="space-y-4">
          <div className="grid grid-cols-2 gap-2">
            <Input
              label="Hãng sản xuất *"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              required
            />
            <Input
              label="Dòng máy / Model *"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Input
              label="Năm sản xuất / mua"
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              min="1990"
              max="2030"
            />
            <Input
              label={isVehicle ? "Biển số xe" : "Số Serial"}
              value={plateOrSerial}
              onChange={(e) => setPlateOrSerial(e.target.value)}
            />
          </div>

          <Input
            label="Vị trí đặt / sử dụng"
            value={locationLabel}
            onChange={(e) => setLocationLabel(e.target.value)}
          />

          <Input
            label="Ghi chú thêm"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full min-h-[48px] font-bold text-base"
            isLoading={isUpdating}
          >
            Lưu Thay Đổi
          </Button>
        </form>
      </BottomSheet>
    </div>
  );
}

