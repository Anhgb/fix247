import Link from "next/link";
import { ArrowLeft, ShieldAlert, PhoneCall, AlertTriangle, CheckCircle, Wrench } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

export default function SosGuidePage() {
  return (
    <div className="flex-1 flex flex-col p-4 pb-12 space-y-5">
      {/* Top Bar */}
      <div className="flex items-center gap-3 pt-2">
        <Link
          href="/"
          className="p-2 min-h-[44px] min-w-[44px] rounded-xl bg-surface-card border border-surface-border text-slate-300 hover:text-white flex items-center justify-center"
          aria-label="Quay lại"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-xl font-bold text-white">Cẩm Nang Cứu Hộ Khẩn Cấp</h1>
      </div>

      {/* Hotline Banner */}
      <div className="p-4 bg-emergency-950/60 border border-emergency-600/50 rounded-2xl flex items-center justify-between">
        <div className="space-y-1">
          <p className="text-xs uppercase font-bold tracking-wider text-emergency-400">
            Tổng Đài Cứu Hộ Huế 24/7
          </p>
          <p className="text-xl font-extrabold text-white">1900 8888 24</p>
        </div>
        <a href="tel:1900888824">
          <Button variant="emergency" size="sm" className="gap-2">
            <PhoneCall className="w-4 h-4" />
            <span>Gọi ngay</span>
          </Button>
        </a>
      </div>

      {/* Guide 1: Xe hỏng giữa đường */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2 text-brand-400">
            <ShieldAlert className="w-5 h-5" />
            <CardTitle>Xử Lý Khi Xe Máy Hỏng Giữa Đường</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-300">
          <div className="flex items-start gap-3">
            <span className="w-6 h-6 rounded-full bg-brand-500/20 text-brand-400 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
              1
            </span>
            <p>
              <strong className="text-white">Tấp vào lề an toàn:</strong> Ngay lập tức bật đèn xi-nhan, quan sát gương và từ từ dắt xe sát lề phải hoặc vỉa hè.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <span className="w-6 h-6 rounded-full bg-brand-500/20 text-brand-400 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
              2
            </span>
            <p>
              <strong className="text-white">Cảnh báo từ xa:</strong> Dựng chân chống đứng, bật đèn cảnh báo (hazard) hoặc đặt vật báo hiệu cách đuôi xe 5-10m vào ban đêm.
            </p>
          </div>
          <div className="flex items-start gap-3">
            <span className="w-6 h-6 rounded-full bg-brand-500/20 text-brand-400 font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
              3
            </span>
            <p>
              <strong className="text-white">Kiểm tra cơ bản:</strong> Xem đồng hồ xăng, kiểm tra chân chống điện đã gạt lên chưa, nút ngắt động cơ khẩn cấp (nếu có).
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Guide 2: Chập cháy đồ điện gia dụng */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2 text-emergency-400">
            <AlertTriangle className="w-5 h-5" />
            <CardTitle>Sự Cố Điện Gia Dụng Khẩn Cấp</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-slate-300">
          <div className="p-3 bg-emergency-900/30 border border-emergency-700/40 rounded-xl text-emergency-200">
            <strong>CẢNH BÁO:</strong> Tuyệt đối không chạm vào thiết bị nếu đang có khói, mùi khét hoặc rò rỉ nước gần ổ điện!
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <p>Ngắt cầu dao (Aptomat) tổng của nhà hoặc khu vực xảy ra sự cố ngay lập tức.</p>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <p>Rút phích cắm khi đã ngắt nguồn điện và mang găng tay cách điện khô.</p>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            <p>Gọi thợ có chứng chỉ trên Fix 24/7 để kiểm tra an toàn trước khi cấp điện trở lại.</p>
          </div>
        </CardContent>
      </Card>

      <div className="pt-2">
        <Link href="/">
          <Button variant="primary" className="w-full">
            <Wrench className="w-5 h-5 mr-2" />
            Đặt Thợ Sửa Ngay Trên Ứng Dụng
          </Button>
        </Link>
      </div>
    </div>
  );
}
