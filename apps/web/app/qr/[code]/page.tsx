"use client";

import * as React from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  MapPin,
  AlertOctagon,
  Calendar,
  Sparkles,
  ShieldCheck,
  Clock,
  ArrowRight,
  AlertTriangle,
  Building,
  Bike,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { qrApi, QRLocationPublic } from "@/lib/api";

export default function QRLocationLandingPage() {
  const params = useParams();
  const router = useRouter();
  const code = params?.code as string;
  const { showToast } = useToast();

  const [location, setLocation] = React.useState<QRLocationPublic | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isNotFound, setIsNotFound] = React.useState(false);

  React.useEffect(() => {
    if (!code) return;
    setIsLoading(true);
    qrApi
      .resolve(code)
      .then(({ data, error }) => {
        setIsLoading(false);
        if (error || !data) {
          setIsNotFound(true);
        } else {
          setLocation(data);
        }
      })
      .catch(() => {
        setIsLoading(false);
        setIsNotFound(true);
      });
  }, [code]);

  if (isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center space-y-4">
        <div className="w-12 h-12 border-4 border-brand-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-slate-400">Đang nhận diện điểm cứu hộ Fix 24/7...</p>
      </div>
    );
  }

  if (isNotFound || !location) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center space-y-5">
        <div className="w-16 h-16 rounded-3xl bg-red-950/70 border border-red-500/40 text-red-400 flex items-center justify-center">
          <AlertTriangle className="w-8 h-8" />
        </div>
        <div className="space-y-1.5">
          <h2 className="text-xl font-bold text-white">Mã QR Không Hợp Lệ</h2>
          <p className="text-xs text-slate-400 max-w-xs mx-auto leading-relaxed">
            Điểm quét mã này không tồn tại hoặc đã ngưng hoạt động trên hệ thống Fix 24/7.
          </p>
        </div>
        <Button variant="primary" size="default" onClick={() => router.push("/")}>
          Về Trang Chủ Fix 24/7
        </Button>
      </div>
    );
  }

  const encodedAddress = encodeURIComponent(location.address);
  const latParam = location.lat ? `&lat=${location.lat}` : "";
  const lngParam = location.lng ? `&lng=${location.lng}` : "";

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 space-y-6 max-w-md mx-auto w-full">
      {/* Top Header */}
      <div className="text-center pt-3 space-y-1">
        <span className="text-xs font-bold text-brand-primary tracking-widest uppercase">
          Fix 24/7 Huế • Cứu Hộ Tại Điểm
        </span>
        <h1 className="text-xl font-black text-white">Điểm Hỗ Trợ Kỹ Thuật Nhanh</h1>
        <p className="text-xs text-slate-400">Không cần cài ứng dụng • Thợ đến sau 15 phút</p>
      </div>

      {/* Identified Location Card */}
      <Card className="bg-gradient-to-br from-brand-950/80 via-surface-card to-surface-card border-brand-500/40 shadow-xl">
        <CardContent className="p-4 space-y-3">
          <div className="flex items-center gap-2 text-brand-400 text-xs font-bold uppercase">
            <Building className="w-4 h-4" />
            <span>{location.location_type || "Khu vực cố định"}</span>
            <Badge variant="brand" className="text-[10px] ml-auto">
              Đã định vị
            </Badge>
          </div>

          <div>
            <h2 className="text-lg font-black text-white">{location.name}</h2>
            <p className="text-xs text-slate-300 mt-1 flex items-start gap-1.5">
              <MapPin className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span>{location.address}</span>
            </p>
          </div>

          <p className="text-[11px] text-slate-400 pt-1 border-t border-surface-border">
            Địa chỉ trên sẽ được tự động điền sẵn cho đơn cứu hộ của bạn.
          </p>
        </CardContent>
      </Card>

      {/* Primary Actions */}
      <div className="space-y-3">
        {/* Action 1: Emergency SOS Motorbike */}
        <Link
          href={`/book/direct?mode=emergency&qr=${code}&address=${encodedAddress}${latParam}${lngParam}`}
          className="block group"
        >
          <div className="relative p-4 bg-gradient-to-r from-emergency-950 via-surface-card to-surface-card border-2 border-emergency-600/80 rounded-2xl shadow-xl flex items-center justify-between group-hover:border-emergency-500 transition">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-emergency-600/20 text-emergency-400 border border-emergency-500/40 flex items-center justify-center shrink-0">
                <Bike className="w-7 h-7 animate-bounce" />
              </div>
              <div>
                <span className="text-xs font-bold text-emergency-400 uppercase tracking-wider block">
                  Cứu Hộ Khẩn Cấp
                </span>
                <h3 className="font-black text-base text-white">Xe Máy Hỏng Tại Đây</h3>
                <p className="text-xs text-slate-400">Thủng xăm, chết máy, đứt xích, hết ắc quy</p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-emergency-400 group-hover:translate-x-1 transition" />
          </div>
        </Link>

        {/* Action 2: Scheduled Home Appliance Repair */}
        <Link
          href={`/book/direct?mode=scheduled&qr=${code}&address=${encodedAddress}${latParam}${lngParam}`}
          className="block group"
        >
          <div className="p-4 bg-surface-card border border-surface-border hover:border-brand-500/60 rounded-2xl shadow-lg flex items-center justify-between transition">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-sky-950/60 text-sky-400 border border-sky-500/30 flex items-center justify-center shrink-0">
                <Wrench className="w-6 h-6" />
              </div>
              <div>
                <span className="text-xs font-bold text-sky-400 uppercase tracking-wider block">
                  Sửa Tại Phòng / Nhà
                </span>
                <h3 className="font-bold text-base text-white">Điện Máy & Đồ Gia Dụng</h3>
                <p className="text-xs text-slate-400">Máy lạnh, máy giặt, quạt điện, bếp điện</p>
              </div>
            </div>
            <ArrowRight className="w-5 h-5 text-slate-400 group-hover:translate-x-1 transition" />
          </div>
        </Link>

        {/* Action 3: AI Diagnosis first */}
        <Link
          href={`/diagnose?qr=${code}&address=${encodedAddress}`}
          className="block group"
        >
          <div className="p-3 bg-surface-card/60 border border-surface-border hover:border-slate-600 rounded-xl flex items-center justify-between text-xs text-slate-300 transition">
            <span className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-400" />
              <span>Chưa rõ nguyên nhân? Chẩn đoán sự cố trước bằng AI</span>
            </span>
            <ArrowRight className="w-4 h-4 text-slate-400" />
          </div>
        </Link>
      </div>

      {/* Trust & Guarantee Badges */}
      <div className="grid grid-cols-3 gap-2 p-3 bg-surface-card/60 border border-surface-border rounded-2xl text-center text-[11px] text-slate-400">
        <div className="flex flex-col items-center">
          <Clock className="w-4 h-4 text-brand-400 mb-1" />
          <span className="font-bold text-white">10 - 20 phút</span>
          <span>Thợ đến nơi</span>
        </div>
        <div className="flex flex-col items-center">
          <Sparkles className="w-4 h-4 text-emerald-400 mb-1" />
          <span className="font-bold text-white">Giá niêm yết</span>
          <span>Không chặt chém</span>
        </div>
        <div className="flex flex-col items-center">
          <ShieldCheck className="w-4 h-4 text-sky-400 mb-1" />
          <span className="font-bold text-white">Bảo hành</span>
          <span>7 - 30 ngày</span>
        </div>
      </div>
    </div>
  );
}

