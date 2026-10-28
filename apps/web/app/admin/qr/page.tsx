"use client";

import * as React from "react";
import Link from "next/link";
import {
  QrCode,
  Plus,
  Printer,
  MapPin,
  Eye,
  ExternalLink,
  Building,
  TrendingUp,
  Share2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { useToast } from "@/components/ui/Toast";
import { adminApi, QRLocationItem, QRLocationCreate } from "@/lib/api";

export default function AdminQRLocationsPage() {
  const { showToast } = useToast();

  const [locations, setLocations] = React.useState<QRLocationItem[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);

  // Create modal
  const [showCreateModal, setShowCreateModal] = React.useState(false);
  const [name, setName] = React.useState("");
  const [locationType, setLocationType] = React.useState("KTX / Khu trọ sinh viên");
  const [address, setAddress] = React.useState("");
  const [lat, setLat] = React.useState<number | undefined>(16.4637);
  const [lng, setLng] = React.useState<number | undefined>(107.5909);
  const [ownerContact, setOwnerContact] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  // Print Sticker Modal
  const [printLoc, setPrintLoc] = React.useState<QRLocationItem | null>(null);

  const loadLocations = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await adminApi.getQRLocations();
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setLocations(data.items);
    }
  }, [showToast]);

  React.useEffect(() => {
    loadLocations();
  }, [loadLocations]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !address.trim()) return;

    setIsSubmitting(true);
    const payload: QRLocationCreate = {
      name: name.trim(),
      location_type: locationType.trim(),
      address: address.trim(),
      lat,
      lng,
      owner_contact: ownerContact.trim() || undefined,
    };
    const { data, error } = await adminApi.createQRLocation(payload);
    setIsSubmitting(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast("Đã tạo điểm dán mã QR mới thành công (AT-08)!", "success");
    setShowCreateModal(false);
    setName("");
    setAddress("");
    setOwnerContact("");
    loadLocations();
  };

  const handlePrint = () => {
    if (typeof window !== "undefined") {
      window.print();
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-white">Quản Lý Điểm Đặt Mã QR</h2>
          <p className="text-xs text-slate-400">Tạo tem dán KTX, khu trọ & theo dõi lượt quét (UC-12, AT-08)</p>
        </div>

        <Button
          variant="primary"
          size="default"
          className="min-h-[40px] text-xs font-semibold"
          onClick={() => setShowCreateModal(true)}
        >
          <Plus className="w-3.5 h-3.5 mr-1" />
          <span>Tạo Điểm Mới</span>
        </Button>
      </div>

      {/* Locations List */}
      {isLoading ? (
        <div className="py-16 text-center text-xs text-slate-400">Đang tải danh sách điểm QR...</div>
      ) : locations.length === 0 ? (
        <div className="p-8 text-center bg-surface-card border border-surface-border rounded-2xl text-xs text-slate-400 space-y-3">
          <QrCode className="w-12 h-12 text-slate-500 mx-auto" />
          <p>Chưa có điểm đặt mã QR nào.</p>
          <Button variant="primary" size="default" onClick={() => setShowCreateModal(true)}>
            Tạo Điểm QR Đầu Tiên
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {locations.map((loc) => (
            <Card key={loc.id} className="bg-surface-card border-surface-border">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-white text-sm">{loc.name}</h3>
                      <Badge variant="brand" className="text-[10px]">
                        {loc.location_type || "Cố định"}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-300 mt-1 flex items-start gap-1">
                      <MapPin className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                      <span>{loc.address}</span>
                    </p>
                  </div>

                  <Button
                    variant="secondary"
                    size="default"
                    className="min-h-[36px] text-xs px-2.5"
                    onClick={() => setPrintLoc(loc)}
                  >
                    <Printer className="w-3.5 h-3.5 mr-1" />
                    <span>In Tem Dán</span>
                  </Button>
                </div>

                {/* QR Code link & stats */}
                <div className="grid grid-cols-3 gap-2 p-2 bg-surface-elevated rounded-xl text-center text-xs border border-surface-border/50">
                  <div>
                    <span className="text-[10px] text-slate-400 block">Lượt quét QR</span>
                    <strong className="text-white text-sm">{loc.scan_count}</strong>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Đơn phát sinh</span>
                    <strong className="text-emerald-400 text-sm">{loc.order_count}</strong>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Chuyển đổi</span>
                    <strong className="text-brand-300 text-sm">{loc.conversion_rate_pct}%</strong>
                  </div>
                </div>

                <div className="pt-2 border-t border-surface-border flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-mono text-[11px]">Mã: {loc.code}</span>

                  <Link
                    href={`/qr/${loc.code}`}
                    target="_blank"
                    className="text-brand-primary hover:underline flex items-center gap-1 font-medium"
                  >
                    <span>Mở trang quét (/qr/{loc.code})</span>
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create QR Location BottomSheet */}
      <BottomSheet
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Tạo Điểm Đặt Mã QR Mới"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <Input
            label="Tên địa điểm dán tem *"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="VD: KTX Đại học Khoa học Huế"
            required
          />

          <Input
            label="Loại địa điểm *"
            value={locationType}
            onChange={(e) => setLocationType(e.target.value)}
            placeholder="VD: Ký túc xá, Bãi giữ xe, Dãy trọ sinh viên..."
            required
          />

          <Input
            label="Địa chỉ chi tiết (Sẽ tự điền khi khách quét) *"
            value={address}
            onChange={(e) => setAddress(e.target.value)}
            placeholder="Số nhà, tên đường, phường tại TP. Huế..."
            required
          />

          <Input
            label="Người liên hệ quản lý điểm (Tùy chọn)"
            value={ownerContact}
            onChange={(e) => setOwnerContact(e.target.value)}
            placeholder="Tên chủ trọ / SĐT bảo vệ..."
          />

          <Button type="submit" variant="primary" size="lg" className="w-full font-bold" isLoading={isSubmitting}>
            Tạo Mã & Điểm QR
          </Button>
        </form>
      </BottomSheet>

      {/* Printable QR Sticker BottomSheet (Print Preview) */}
      <BottomSheet
        isOpen={printLoc !== null}
        onClose={() => setPrintLoc(null)}
        title="Bản Xem Trước Tem Dán QR (Print Preview)"
      >
        {printLoc && (
          <div className="space-y-4">
            {/* Printable Sticker Box */}
            <div className="p-6 bg-white text-slate-900 rounded-3xl shadow-2xl border-4 border-slate-900 text-center space-y-3 max-w-xs mx-auto print:m-0 print:border-none">
              <div className="space-y-0.5 border-b-2 border-slate-900 pb-2">
                <span className="text-[10px] font-black uppercase tracking-widest text-orange-600 block">
                  CỨU HỘ & SỬA CHỮA KHẨN CẤP
                </span>
                <h3 className="text-2xl font-black tracking-tight text-slate-900">
                  FIX 24/7 HUẾ
                </h3>
              </div>

              {/* Dynamic QR Code Render */}
              <div className="p-3 bg-slate-50 border-2 border-dashed border-slate-400 rounded-2xl inline-block mx-auto">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(
                    typeof window !== "undefined"
                      ? `${window.location.origin}/qr/${printLoc.code}`
                      : `https://fix247.vn/qr/${printLoc.code}`
                  )}`}
                  alt={`QR ${printLoc.code}`}
                  className="w-44 h-44 object-contain mx-auto"
                />
              </div>

              <div className="space-y-1">
                <p className="text-xs font-black uppercase text-slate-900">
                  QUÉT BẰNG CAMERA ĐIỆN THOẠI
                </p>
                <p className="text-[11px] text-slate-600 font-medium leading-tight">
                  Không cần tải ứng dụng • Thợ đến sau 15 phút
                </p>
              </div>

              <div className="pt-2 border-t border-slate-300 text-[10px] text-slate-700">
                <strong>{printLoc.name}</strong>
                <p className="truncate">{printLoc.address}</p>
                <span className="font-mono font-bold text-[9px] text-slate-500 mt-0.5 block">
                  MÃ: {printLoc.code}
                </span>
              </div>
            </div>

            <Button
              variant="primary"
              size="lg"
              className="w-full font-bold bg-slate-900 hover:bg-slate-800 text-white"
              onClick={handlePrint}
            >
              <Printer className="w-4 h-4 mr-2" />
              <span>In Tem Dán Này</span>
            </Button>
          </div>
        )}
      </BottomSheet>
    </div>
  );
}

