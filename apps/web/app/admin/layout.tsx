"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  Users,
  Package,
  AlertTriangle,
  Tag,
  QrCode,
  Settings,
  FileText,
  ShieldCheck,
  LogOut,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { authApi } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/admin", label: "Tổng Quan", icon: BarChart3 },
  { href: "/admin/technicians", label: "Duyệt Thợ", icon: Users },
  { href: "/admin/orders", label: "Đơn Hàng", icon: Package },
  { href: "/admin/disputes", label: "Khiếu Nại", icon: AlertTriangle },
  { href: "/admin/catalog", label: "Bảng Giá", icon: Tag },
  { href: "/admin/qr", label: "Điểm QR", icon: QrCode },
  { href: "/admin/settings", label: "Cài Đặt", icon: Settings },
  { href: "/admin/audit-logs", label: "Nhật Ký", icon: FileText },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { showToast } = useToast();

  const [isAdmin, setIsAdmin] = React.useState<boolean | null>(null);
  const [adminPhone, setAdminPhone] = React.useState("0900000000");
  const [otp, setOtp] = React.useState("123456");
  const [isLoggingIn, setIsLoggingIn] = React.useState(false);

  // Check auth role on mount
  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("fix247_access_token");
    const role = localStorage.getItem("fix247_user_role");

    if (token && role === "admin") {
      setIsAdmin(true);
    } else {
      setIsAdmin(false);
    }
  }, []);

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoggingIn(true);

    // Request OTP then verify
    await authApi.requestOtp(adminPhone);
    const { data, error } = await authApi.verifyOtp(adminPhone, otp);
    setIsLoggingIn(false);

    if (error || !data) {
      showToast(error?.message || "Đăng nhập quản trị thất bại.", "error");
      return;
    }

    localStorage.setItem("fix247_access_token", data.access_token);
    localStorage.setItem("fix247_user_role", data.user.role);
    localStorage.setItem("fix247_user_phone", data.user.phone);

    if (data.user.role === "admin") {
      setIsAdmin(true);
      showToast("Đăng nhập quyền Quản trị viên thành công!", "success");
    } else {
      showToast("Tài khoản này không có vai trò Quản trị viên.", "error");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("fix247_access_token");
    localStorage.removeItem("fix247_user_role");
    localStorage.removeItem("fix247_user_phone");
    setIsAdmin(false);
    showToast("Đã đăng xuất khỏi cổng Quản trị viên.", "info");
    router.push("/");
  };

  // Checking state
  if (isAdmin === null) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-xs text-slate-400">
        Đang kiểm tra quyền quản trị...
      </div>
    );
  }

  // Not admin -> show login gate
  if (!isAdmin) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-sm mx-auto w-full space-y-5">
        <div className="w-16 h-16 rounded-3xl bg-brand-950 border border-brand-500/40 text-brand-400 flex items-center justify-center">
          <Lock className="w-8 h-8" />
        </div>
        <div className="text-center space-y-1">
          <h2 className="text-xl font-bold text-white">Cổng Quản Trị Fix 24/7</h2>
          <p className="text-xs text-slate-400">
            Yêu cầu tài khoản có vai trò Quản trị viên (ADMIN).
          </p>
        </div>

        <form onSubmit={handleAdminLogin} className="w-full space-y-3">
          <Input
            label="Số điện thoại Admin"
            value={adminPhone}
            onChange={(e) => setAdminPhone(e.target.value)}
            placeholder="0900000000"
            required
            helperText="Tài khoản admin mặc định: 0900000000"
          />
          <Input
            label="Mã OTP xác thực (Dev: 123456)"
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            placeholder="123456"
            required
            maxLength={6}
          />
          <Button type="submit" variant="primary" size="lg" className="w-full font-bold" isLoading={isLoggingIn}>
            Đăng Nhập Quản Trị
          </Button>
        </form>

        <Link href="/" className="text-xs text-slate-400 hover:text-white underline underline-offset-4">
          Quay lại trang chủ người dùng
        </Link>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-surface">
      {/* Top Admin Header */}
      <header className="p-3.5 bg-surface-card border-b border-surface-border flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-brand-500/20 text-brand-400 flex items-center justify-center">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-sm font-black text-white flex items-center gap-1.5">
              <span>Fix 24/7 Admin</span>
              <Badge variant="brand" className="text-[10px] px-1.5 py-0">
                P5
              </Badge>
            </h1>
            <p className="text-[11px] text-slate-400">TP. Huế • Hệ Thống Điều Hành</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href="/"
            className="text-xs text-slate-400 hover:text-white px-2 py-1 rounded-lg border border-surface-border hover:border-slate-500 transition"
          >
            Về App
          </Link>
          <button
            type="button"
            onClick={handleLogout}
            className="p-1.5 text-slate-400 hover:text-red-400 transition"
            title="Đăng xuất"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Horizontal Scroll Navigation Tabs */}
      <nav className="bg-surface-elevated/70 border-b border-surface-border px-2 py-1.5 flex gap-1 overflow-x-auto scrollbar-none sticky top-[57px] z-20">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition ${
                isActive
                  ? "bg-brand-600 text-white shadow-sm shadow-brand-900/50"
                  : "text-slate-400 hover:text-slate-200 hover:bg-surface-card"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Admin Page Content */}
      <main className="flex-1 flex flex-col p-4 pb-16">{children}</main>
    </div>
  );
}

