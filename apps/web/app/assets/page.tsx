"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Plus,
  Bike,
  Tv,
  Wrench,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Trash2,
  ChevronRight,
  ShieldCheck,
  Calendar,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { useToast } from "@/components/ui/Toast";
import { assetsApi, AssetResponse, AssetCreate } from "@/lib/api";

export default function AssetsPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [assets, setAssets] = React.useState<AssetResponse[]>([]);
  const [totalCount, setTotalCount] = React.useState(0);
  const [isLoading, setIsLoading] = React.useState(true);
  const [showAddModal, setShowAddModal] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // Form state
  const [assetType, setAssetType] = React.useState<"vehicle" | "appliance">("vehicle");
  const [brand, setBrand] = React.useState("");
  const [model, setModel] = React.useState("");
  const [year, setYear] = React.useState("");
  const [plateOrSerial, setPlateOrSerial] = React.useState("");
  const [locationLabel, setLocationLabel] = React.useState("");
  const [notes, setNotes] = React.useState("");

  const loadAssets = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await assetsApi.list();
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setAssets(data.items);
      setTotalCount(data.total);
    }
  }, [showToast]);

  React.useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  const handleCreateAsset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!brand.trim() || !model.trim()) {
      showToast("Vui lòng nhập hãng sản xuất và dòng máy/xe.", "error");
      return;
    }

    setIsSubmitting(true);
    const payload: AssetCreate = {
      asset_type: assetType,
      brand: brand.trim(),
      model: model.trim(),
      year: year ? parseInt(year, 10) : undefined,
      plate_or_serial: plateOrSerial.trim() || undefined,
      location_label: locationLabel.trim() || undefined,
      notes: notes.trim() || undefined,
    };

    const { data, error } = await assetsApi.create(payload);
    setIsSubmitting(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast("Đã lưu thiết bị vào Sổ sức khỏe điện tử!", "success");
    setShowAddModal(false);
    // Reset form
    setBrand("");
    setModel("");
    setYear("");
    setPlateOrSerial("");
    setLocationLabel("");
    setNotes("");
    loadAssets();
  };

  const handleDeleteAsset = async (id: string, name: string) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa tài sản "${name}" khỏi danh bạ?`)) {
      return;
    }
    const { error } = await assetsApi.delete(id);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    showToast("Đã xóa thiết bị.", "info");
    loadAssets();
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "Chưa bảo dưỡng";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  const getHealthBadge = (status: "good" | "needs_maintenance" | "due_soon") => {
    switch (status) {
      case "good":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-950/70 border border-emerald-500/30 px-2.5 py-0.5 rounded-full">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Tốt
          </span>
        );
      case "due_soon":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-400 bg-amber-950/70 border border-amber-500/30 px-2.5 py-0.5 rounded-full">
            <Clock className="w-3.5 h-3.5" />
            Sắp Đến Hạn
          </span>
        );
      case "needs_maintenance":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-red-400 bg-red-950/70 border border-red-500/30 px-2.5 py-0.5 rounded-full">
            <AlertTriangle className="w-3.5 h-3.5" />
            Cần Bảo Dưỡng
          </span>
        );
    }
  };

  return (
    <div className="flex-1 flex flex-col p-4 pb-16 space-y-5">
      {/* Top Header */}
      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="p-2 min-h-[44px] min-w-[44px] rounded-xl bg-surface-card border border-surface-border text-slate-300 hover:text-white flex items-center justify-center"
            aria-label="Quay lại trang chủ"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <span>Sổ Sức Khỏe Thiết Bị</span>
              <Sparkles className="w-4 h-4 text-brand-400" />
            </h1>
            <p className="text-xs text-slate-400">
              Quản lý xe máy & đồ điện gia dụng ({totalCount}/10 tài sản)
            </p>
          </div>
        </div>

        <Button
          variant="primary"
          size="default"
          className="min-h-[44px] text-xs font-semibold"
          onClick={() => setShowAddModal(true)}
          disabled={totalCount >= 10}
        >
          <Plus className="w-4 h-4 mr-1" />
          <span>Thêm Mới</span>
        </Button>
      </div>

      {/* Overview Banner */}
      <div className="p-4 bg-gradient-to-br from-brand-950/50 via-surface-card to-surface-card border border-brand-500/30 rounded-2xl space-y-2">
        <div className="flex items-center gap-2 text-brand-400 font-bold text-sm">
          <ShieldCheck className="w-4 h-4" />
          <span>Theo Dõi & Nhắc Lịch Tự Động (FR-HEALTH-01)</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed">
          Mỗi khi thợ hoàn tất sửa chữa, lịch sử thay phụ tùng và chi phí sẽ tự động được ghi vào
          sổ. Hệ thống tự động nhắc thay dầu (xe máy) hoặc vệ sinh (điện máy) định kỳ.
        </p>
      </div>

      {/* Asset List */}
      {isLoading ? (
        <div className="py-16 text-center space-y-3">
          <div className="w-10 h-10 border-4 border-brand-primary border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Đang tải danh bạ thiết bị...</p>
        </div>
      ) : assets.length === 0 ? (
        <div className="p-8 text-center bg-surface-card border border-surface-border rounded-2xl space-y-4">
          <div className="w-16 h-16 rounded-full bg-surface-elevated mx-auto flex items-center justify-center text-slate-400">
            <Wrench className="w-8 h-8" />
          </div>
          <div className="space-y-1">
            <h3 className="text-base font-bold text-white">Chưa Có Thiết Bị Nào</h3>
            <p className="text-xs text-slate-400 max-w-xs mx-auto">
              Thêm xe máy hoặc thiết bị gia đình để lưu lại nhật ký sửa chữa, chi phí và nhận nhắc
              lịch bảo dưỡng tự động.
            </p>
          </div>
          <Button
            variant="primary"
            size="default"
            className="min-h-[48px]"
            onClick={() => setShowAddModal(true)}
          >
            <Plus className="w-4 h-4 mr-1.5" />
            <span>Thêm Thiết Bị Đầu Tiên</span>
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {assets.map((item) => {
            const isVehicle = item.asset_type === "vehicle";
            const title = `${item.brand || ""} ${item.model || ""}`.trim();

            return (
              <Card
                key={item.id}
                className="bg-surface-card border-surface-border hover:border-slate-600 transition"
              >
                <CardContent className="p-4 space-y-3">
                  {/* Top row */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 ${
                          isVehicle
                            ? "bg-amber-950/60 text-amber-400 border border-amber-500/30"
                            : "bg-sky-950/60 text-sky-400 border border-sky-500/30"
                        }`}
                      >
                        {isVehicle ? <Bike className="w-6 h-6" /> : <Tv className="w-6 h-6" />}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-bold text-white text-base">{title}</h3>
                          {item.year && (
                            <span className="text-[11px] text-slate-400">({item.year})</span>
                          )}
                        </div>
                        <p className="text-xs text-slate-400">
                          {isVehicle ? "🛵 Xe máy" : "🏠 Thiết bị gia đình"}
                          {item.plate_or_serial && ` • ${item.plate_or_serial}`}
                          {item.location_label && ` • ${item.location_label}`}
                        </p>
                      </div>
                    </div>

                    <div>{getHealthBadge(item.health_status)}</div>
                  </div>

                  {/* Reminders / Status message */}
                  {item.reminders && item.reminders.length > 0 && (
                    <div className="p-2.5 bg-surface-elevated/70 border border-surface-border rounded-xl space-y-1">
                      {item.reminders.map((rem, rIdx) => (
                        <div
                          key={rIdx}
                          className="flex items-center gap-2 text-xs text-amber-300 font-medium"
                        >
                          <Clock className="w-3.5 h-3.5 shrink-0" />
                          <span>{rem.title}: {rem.message}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Summary & Actions row */}
                  <div className="pt-2 border-t border-surface-border flex items-center justify-between text-xs text-slate-400">
                    <div>
                      <span>Đã bảo dưỡng: </span>
                      <strong className="text-white">{item.maintenance_count} lần</strong>
                      <span className="mx-1.5">•</span>
                      <span>Gần nhất: </span>
                      <strong className="text-slate-300">{formatDate(item.last_maintained_at)}</strong>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => handleDeleteAsset(item.id, title)}
                        className="p-1.5 text-slate-400 hover:text-red-400 transition"
                        title="Xóa thiết bị"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>

                      <Link
                        href={`/assets/${item.id}`}
                        className="inline-flex items-center gap-1 font-semibold text-brand-primary hover:text-brand-400 p-1.5"
                      >
                        <span>Nhật ký</span>
                        <ChevronRight className="w-4 h-4" />
                      </Link>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Add Asset Modal */}
      <BottomSheet
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        title="Thêm Thiết Bị Vào Sổ Sức Khỏe"
      >
        <form onSubmit={handleCreateAsset} className="space-y-4">
          {/* Asset Type toggle */}
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Loại phương tiện / thiết bị
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setAssetType("vehicle")}
                className={`min-h-[48px] rounded-xl font-semibold text-sm flex items-center justify-center gap-2 border transition ${
                  assetType === "vehicle"
                    ? "bg-amber-950/80 border-amber-500 text-amber-300 ring-2 ring-amber-500/20"
                    : "bg-surface-card border-surface-border text-slate-400"
                }`}
              >
                <Bike className="w-5 h-5" />
                <span>Xe máy</span>
              </button>
              <button
                type="button"
                onClick={() => setAssetType("appliance")}
                className={`min-h-[48px] rounded-xl font-semibold text-sm flex items-center justify-center gap-2 border transition ${
                  assetType === "appliance"
                    ? "bg-sky-950/80 border-sky-500 text-sky-300 ring-2 ring-sky-500/20"
                    : "bg-surface-card border-surface-border text-slate-400"
                }`}
              >
                <Tv className="w-5 h-5" />
                <span>Thiết bị gia đình</span>
              </button>
            </div>
          </div>

          {/* Brand & Model */}
          <div className="grid grid-cols-2 gap-2">
            <Input
              label="Hãng sản xuất *"
              value={brand}
              onChange={(e) => setBrand(e.target.value)}
              placeholder={assetType === "vehicle" ? "Honda, Yamaha..." : "Daikin, Panasonic..."}
              required
            />
            <Input
              label="Dòng máy / Model *"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder={assetType === "vehicle" ? "Wave Alpha, Air Blade..." : "Inverter 1.5HP..."}
              required
            />
          </div>

          {/* Year & Plate/Serial */}
          <div className="grid grid-cols-2 gap-2">
            <Input
              label="Năm sản xuất / mua"
              type="number"
              value={year}
              onChange={(e) => setYear(e.target.value)}
              placeholder="2022"
              min="1990"
              max="2030"
            />
            <Input
              label={assetType === "vehicle" ? "Biển số xe" : "Số Serial"}
              value={plateOrSerial}
              onChange={(e) => setPlateOrSerial(e.target.value)}
              placeholder={assetType === "vehicle" ? "75F1-123.45" : "SN: 88921..."}
              helperText="Mỗi thiết bị cần một mã định danh duy nhất"
            />
          </div>

          {/* Location */}
          <Input
            label="Vị trí đặt / sử dụng (tùy chọn)"
            value={locationLabel}
            onChange={(e) => setLocationLabel(e.target.value)}
            placeholder="Ví dụ: Xe đi làm chính, Điều hòa phòng khách..."
          />

          {/* Notes */}
          <Input
            label="Ghi chú thêm"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Ví dụ: Xe vừa thay lốp trước tháng trước..."
          />

          <Button
            type="submit"
            variant="primary"
            size="lg"
            className="w-full min-h-[48px] font-bold text-base"
            isLoading={isSubmitting}
          >
            Lưu Thiết Bị Vào Sổ Sức Khỏe
          </Button>
        </form>
      </BottomSheet>
    </div>
  );
}

