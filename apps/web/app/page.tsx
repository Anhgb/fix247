"use client";

import * as React from "react";
import Link from "next/link";
import {
  Wrench,
  AlertOctagon,
  Calendar,
  MapPin,
  ShieldCheck,
  Sparkles,
  Phone,
  Info,
  Clock,
  ArrowRight,
  UserCheck,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toast";
import { authApi } from "@/lib/api";

const POPULAR_SERVICES = [
  { id: "bike-puncture", name: "Vá xăm / Thay lốp", category: "Xe máy", icon: "🛵", price: "30.000đ - 120.000đ" },
  { id: "bike-battery", name: "Kích bình / Thay ắc quy", category: "Xe máy", icon: "⚡", price: "50.000đ - 350.000đ" },
  { id: "ac-clean", name: "Bảo dưỡng / Vệ sinh máy lạnh", category: "Điện lạnh", icon: "❄️", price: "150.000đ - 250.000đ" },
  { id: "wash-repair", name: "Sửa máy giặt không vắt/xả", category: "Gia dụng", icon: "🧺", price: "120.000đ - 300.000đ" },
];

export default function HomePage() {
  const { showToast } = useToast();

  // Auth & Terms Modal States
  const [showAuthModal, setShowAuthModal] = React.useState(false);
  const [showTermsModal, setShowTermsModal] = React.useState(false);
  const [currentUser, setCurrentUser] = React.useState<{
    phone: string;
    role: string;
    termsAccepted: boolean;
  } | null>(null);

  // Form states
  const [phone, setPhone] = React.useState("0905123456");
  const [otp, setOtp] = React.useState("");
  const [otpSent, setOtpSent] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);
  const [locationName, setLocationName] = React.useState("TP. Huế (Đang định vị...)");

  // Detect GPS on mount
  React.useEffect(() => {
    if (typeof window !== "undefined") {
      const storedToken = localStorage.getItem("fix247_access_token");
      const storedPhone = localStorage.getItem("fix247_user_phone");
      const termsAccepted = localStorage.getItem("fix247_terms_accepted") === "true";

      if (storedToken && storedPhone) {
        setCurrentUser({
          phone: storedPhone,
          role: "CUSTOMER",
          termsAccepted,
        });
      }

      if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            setLocationName(
              `Tọa độ: ${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`
            );
          },
          () => {
            setLocationName("Khu vực: Trung tâm TP. Huế");
          },
          { timeout: 8000 }
        );
      } else {
        setLocationName("Khu vực: Trung tâm TP. Huế");
      }
    }
  }, []);

  // Request OTP
  const handleRequestOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    const { data, error } = await authApi.requestOtp(phone);
    setIsLoading(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    setOtpSent(true);
    showToast("Mã OTP đã được gửi! (Xem console log [OTP-MOCK] trong môi trường dev)", "info");
  };

  // Verify OTP
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    const { data, error } = await authApi.verifyOtp(phone, otp);
    setIsLoading(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    if (data) {
      localStorage.setItem("fix247_access_token", data.access_token);
      localStorage.setItem("fix247_refresh_token", data.refresh_token);
      localStorage.setItem("fix247_user_phone", data.user.phone);
      const accepted = !!data.user.terms_accepted_at;
      localStorage.setItem("fix247_terms_accepted", accepted ? "true" : "false");

      setCurrentUser({
        phone: data.user.phone,
        role: data.user.role,
        termsAccepted: accepted,
      });

      setShowAuthModal(false);
      showToast("Đăng nhập thành công!", "success");

      if (!accepted) {
        setShowTermsModal(true);
      }
    }
  };

  // Accept Terms Gate
  const handleAcceptTerms = async () => {
    setIsLoading(true);
    const { error } = await authApi.acceptTerms();
    setIsLoading(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    localStorage.setItem("fix247_terms_accepted", "true");
    if (currentUser) {
      setCurrentUser({ ...currentUser, termsAccepted: true });
    }
    setShowTermsModal(false);
    showToast("Bạn đã chấp thuận Điều khoản Dịch vụ Fix 24/7", "success");
  };

  const handleLogout = () => {
    localStorage.removeItem("fix247_access_token");
    localStorage.removeItem("fix247_refresh_token");
    localStorage.removeItem("fix247_user_phone");
    localStorage.removeItem("fix247_terms_accepted");
    setCurrentUser(null);
    showToast("Đã đăng xuất", "info");
  };

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 space-y-6">
      {/* Header */}
      <header className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center text-white shadow-md shadow-brand-900/40 font-extrabold text-xl">
            24
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-xl tracking-tight text-white">Fix 24/7</span>
              <Badge variant="brand" className="text-[10px] px-1.5 py-0">Huế</Badge>
            </div>
            <p className="text-xs text-slate-400 flex items-center gap-1">
              <MapPin className="w-3 h-3 text-brand-400 shrink-0" />
              <span className="truncate max-w-[160px]">{locationName}</span>
            </p>
          </div>
        </div>

        <div>
          {currentUser ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-emerald-400 font-medium hidden sm:inline">
                {currentUser.phone}
              </span>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleLogout}
                className="text-xs min-h-[38px] px-3"
              >
                Đăng xuất
              </Button>
            </div>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowAuthModal(true)}
              className="text-xs min-h-[40px] px-3.5 gap-1.5"
            >
              <UserCheck className="w-4 h-4 text-brand-400" />
              <span>Đăng nhập</span>
            </Button>
          )}
        </div>
      </header>

      {/* AI Diagnosis Promo Pill */}
      <Link href="/diagnose" className="block group">
        <div className="p-3 bg-gradient-to-r from-brand-950/80 via-surface-card to-surface-card border border-brand-500/40 rounded-2xl flex items-center justify-between group-hover:border-brand-500/80 transition shadow-lg shadow-brand-950/30">
          <div className="flex items-center gap-2.5">
            <div className="p-2 bg-brand-500/20 rounded-xl text-brand-400">
              <Sparkles className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <p className="text-sm font-bold text-white group-hover:text-brand-300 transition">
                Chẩn đoán lỗi bằng AI
              </p>
              <p className="text-xs text-slate-400">Chụp ảnh/ghi âm, biết ngay giá niêm yết</p>
            </div>
          </div>
          <span className="text-xs font-semibold text-brand-400 group-hover:text-brand-300 underline underline-offset-4 flex items-center gap-1">
            Thử ngay <ArrowRight className="w-3 h-3" />
          </span>
        </div>
      </Link>

      {/* 2 LARGE PRIMARY CTAs – SRS §7.1 & P0-11 */}
      <section className="space-y-4">
        {/* CTA 1: Emergency SOS Motorbike */}
        <div className="relative group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-emergency-600 to-orange-600 rounded-3xl blur opacity-40 group-hover:opacity-75 transition duration-300" />
          <div className="relative p-5 bg-gradient-to-br from-emergency-950/90 via-surface-card to-surface-card border-2 border-emergency-600/70 rounded-2xl shadow-xl flex flex-col space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2 text-emergency-400">
                <AlertOctagon className="w-6 h-6 animate-bounce" />
                <Badge variant="emergency" className="uppercase font-bold tracking-wider">
                  Khẩn cấp 24/7
                </Badge>
              </div>
              <span className="text-xs text-slate-400 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5 text-emergency-400" />
                Thợ đến 10 - 20 phút
              </span>
            </div>

            <div>
              <h2 className="text-2xl font-black text-white leading-tight tracking-tight">
                Xe Hỏng Giữa Đường
              </h2>
              <p className="text-sm text-slate-300 mt-1 leading-relaxed">
                Thủng xăm, đứt xích, chết máy, hết xăng. Thợ gần nhất tự động định vị đến tận nơi trên đường phố Huế.
              </p>
            </div>

            <Button
              variant="emergency"
              size="lg"
              className="w-full font-bold text-lg shadow-xl shadow-emergency-950/60"
              onClick={() => {
                if (!currentUser) {
                  setShowAuthModal(true);
                  return;
                }
                if (!currentUser.termsAccepted) {
                  setShowTermsModal(true);
                  return;
                }
                showToast("Đang tìm thợ gần bạn trong bán kính 3km...", "info");
              }}
            >
              <AlertOctagon className="w-6 h-6 mr-2" />
              <span>GỌI CỨU HỘ KHẨN CẤP</span>
            </Button>
          </div>
        </div>

        {/* CTA 2: Scheduled Home Appliance Repair */}
        <div className="relative p-5 bg-gradient-to-br from-surface-card via-surface-card to-slate-900 border-2 border-brand-500/60 rounded-2xl shadow-lg flex flex-col space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2 text-brand-400">
              <Wrench className="w-6 h-6" />
              <Badge variant="brand" className="uppercase font-bold tracking-wider">
                Đặt lịch hẹn
              </Badge>
            </div>
            <span className="text-xs text-slate-400 flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5 text-brand-400" />
              07:00 - 21:00 hàng ngày
            </span>
          </div>

          <div>
            <h2 className="text-2xl font-black text-white leading-tight tracking-tight">
              Sửa Tại Nhà
            </h2>
            <p className="text-sm text-slate-300 mt-1 leading-relaxed">
              Máy lạnh, máy giặt, tủ lạnh, quạt điện, bình nước nóng. Thợ chuyên nghiệp đến tận nhà theo giờ hẹn của bạn.
            </p>
          </div>

          <Button
            variant="primary"
            size="lg"
            className="w-full font-bold text-lg shadow-xl shadow-brand-950/60"
            onClick={() => {
              if (!currentUser) {
                setShowAuthModal(true);
                return;
              }
              if (!currentUser.termsAccepted) {
                setShowTermsModal(true);
                return;
              }
              showToast("Vui lòng chọn dịch vụ hoặc mô tả sự cố để AI chẩn đoán", "info");
            }}
          >
            <Calendar className="w-6 h-6 mr-2" />
            <span>ĐẶT LỊCH SỬA TẠI NHÀ</span>
          </Button>
        </div>
      </section>

      {/* Popular Services & Standard Price Catalog */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <span>Dịch Vụ Phổ Biến</span>
            <Badge variant="neutral">Bảng giá chuẩn</Badge>
          </h3>
          <span className="text-xs text-brand-400">Minh bạch 100%</span>
        </div>

        <div className="grid grid-cols-1 gap-2.5">
          {POPULAR_SERVICES.map((s) => (
            <Link
              key={s.id}
              href={`/diagnose?group=${s.category === "Xe máy" ? "motorbike" : "home"}&desc=${encodeURIComponent(s.name)}`}
              className="block"
            >
              <Card interactive className="p-3.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl p-2 bg-surface-elevated rounded-xl">{s.icon}</span>
                    <div>
                      <h4 className="font-semibold text-sm text-white">{s.name}</h4>
                      <span className="text-xs text-slate-400">{s.category}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-bold text-brand-400 block">{s.price}</span>
                    <span className="text-[11px] text-slate-400">Giá niêm yết</span>
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      </section>

      {/* Trust & Guarantees */}
      <section className="p-4 bg-surface-card/60 border border-surface-border rounded-2xl grid grid-cols-3 gap-2 text-center">
        <div className="flex flex-col items-center">
          <ShieldCheck className="w-6 h-6 text-emerald-400 mb-1" />
          <span className="text-xs font-bold text-white">Thợ Xác Thực</span>
          <span className="text-[10px] text-slate-400">CCCD & Tay nghề</span>
        </div>
        <div className="flex flex-col items-center">
          <Sparkles className="w-6 h-6 text-brand-400 mb-1" />
          <span className="text-xs font-bold text-white">AI Định Giá</span>
          <span className="text-[10px] text-slate-400">Không chặt chém</span>
        </div>
        <div className="flex flex-col items-center">
          <CheckCircle2 className="w-6 h-6 text-sky-400 mb-1" />
          <span className="text-xs font-bold text-white">Bảo Hành</span>
          <span className="text-[10px] text-slate-400">7 - 30 ngày</span>
        </div>
      </section>

      {/* Quick SOS Guide Footer Link */}
      <footer className="pt-2 text-center space-y-2">
        <Link
          href="/sos-guide"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white underline underline-offset-4"
        >
          <Info className="w-3.5 h-3.5" />
          <span>Hướng dẫn an toàn khi gặp sự cố khẩn cấp (Hỗ trợ offline)</span>
        </Link>
        <p className="text-[11px] text-slate-500">
          Fix 24/7 Huế © 2026. Phục vụ toàn TP. Huế và vùng lân cận.
        </p>
      </footer>

      {/* AUTH MODAL (P0-7, P0-8) */}
      <BottomSheet
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
        title="Đăng Nhập / Đăng Ký Fix 24/7"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-300">
            Nhập số điện thoại của bạn. Hệ thống sẽ gửi mã OTP xác thực qua tin nhắn SMS (Dev mode: hiển thị tại console).
          </p>

          {!otpSent ? (
            <form onSubmit={handleRequestOtp} className="space-y-4">
              <Input
                label="Số điện thoại Việt Nam"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="0905xxxxxx"
                required
                helperText="Chấp nhận các đầu số 03, 05, 07, 08, 09 (10 chữ số)"
              />
              <Button type="submit" className="w-full" isLoading={isLoading}>
                Nhận Mã OTP
              </Button>
            </form>
          ) : (
            <form onSubmit={handleVerifyOtp} className="space-y-4">
              <Input
                label={`Nhập mã OTP gửi tới ${phone}`}
                value={otp}
                onChange={(e) => setOtp(e.target.value)}
                placeholder="6 chữ số (vd: 123456)"
                required
                maxLength={6}
                helperText="Mã có hiệu lực trong 5 phút. Sai quá 5 lần sẽ bị khóa 15 phút."
              />
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  className="w-1/3"
                  onClick={() => setOtpSent(false)}
                >
                  Đổi số
                </Button>
                <Button type="submit" className="w-2/3" isLoading={isLoading}>
                  Xác Nhận OTP
                </Button>
              </div>
            </form>
          )}
        </div>
      </BottomSheet>

      {/* TERMS ACCEPTANCE MODAL GATE (P0-9, FR-AUTH-04) */}
      <BottomSheet
        isOpen={showTermsModal}
        onClose={() => {
          if (!currentUser?.termsAccepted) {
            showToast("Bạn cần đồng ý Điều khoản để tiếp tục sử dụng dịch vụ", "error");
          }
          setShowTermsModal(false);
        }}
        title="Điều Khoản Dịch Vụ Fix 24/7"
      >
        <div className="space-y-4">
          <div className="p-3 bg-surface-elevated/50 border border-surface-border rounded-xl text-xs text-slate-300 space-y-2 max-h-56 overflow-y-auto leading-relaxed">
            <p className="font-bold text-white text-sm">Chấp thuận Điều khoản & Điều kiện (FR-AUTH-04)</p>
            <p>1. <strong>Minh bạch chi phí:</strong> Khách hàng chỉ thanh toán đúng mức giá thợ đã báo qua ứng dụng và được khách hàng xác nhận.</p>
            <p>2. <strong>Bảo hành:</strong> Mọi dịch vụ sửa chữa hoàn tất đều được kích hoạt bảo hành điện tử (7 ngày với xe máy, 30 ngày với điện máy).</p>
            <p>3. <strong>An toàn dữ liệu:</strong> Số điện thoại và thông tin cá nhân của bạn được bảo mật tuyệt đối, không chia sẻ cho bên thứ ba.</p>
            <p>4. <strong>Phí kiểm tra/khảo sát:</strong> Trường hợp thợ đến nơi kiểm tra nhưng khách không đồng ý sửa, mức phí khảo sát quy định là 30.000đ.</p>
          </div>

          <Button
            variant="primary"
            size="lg"
            className="w-full"
            onClick={handleAcceptTerms}
            isLoading={isLoading}
          >
            Tôi Đồng Ý Với Điều Khoản
          </Button>
        </div>
      </BottomSheet>
    </div>
  );
}
