"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  Power,
  MapPin,
  Clock,
  AlertOctagon,
  Wrench,
  CheckCircle2,
  XCircle,
  Bell,
  Wallet,
  Star,
  UserCheck,
  History,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { apiRequest } from "@/lib/api";

export default function TechnicianDashboard() {
  const router = useRouter();
  const { showToast } = useToast();

  const [isOnline, setIsOnline] = React.useState(false);
  const [approvalStatus, setApprovalStatus] = React.useState("pending");
  const [stats, setStats] = React.useState<any>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  // Incoming job invite state
  const [incomingJob, setIncomingJob] = React.useState<any>(null);
  const [countdown, setCountdown] = React.useState(60);

  // Load dashboard info
  const loadDashboard = React.useCallback(async () => {
    const { data } = await apiRequest<any>("/tech/dashboard-info");
    setIsLoading(false);
    if (data) {
      setIsOnline(data.is_online);
      setApprovalStatus(data.approval_status);
      setStats(data);
    }
  }, []);

  React.useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  // Online GPS reporter
  React.useEffect(() => {
    if (!isOnline) return;

    const interval = setInterval(() => {
      if (typeof window !== "undefined" && "geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            apiRequest("/tech/location", {
              method: "POST",
              body: JSON.stringify({
                lat: pos.coords.latitude,
                lng: pos.coords.longitude,
              }),
            });
          },
          () => {
            // Default Hue center coordinate report if GPS denied
            apiRequest("/tech/location", {
              method: "POST",
              body: JSON.stringify({
                lat: 16.4637,
                lng: 107.5909,
              }),
            });
          }
        );
      }
    }, 20000); // Every 20s

    return () => clearInterval(interval);
  }, [isOnline]);

  // Toggle online/offline
  const handleToggleOnline = async () => {
    const nextState = !isOnline;
    const { data, error } = await apiRequest<any>("/tech/status", {
      method: "PATCH",
      body: JSON.stringify({ is_online: nextState }),
    });

    if (error) {
      showToast(error.message, "error");
      return;
    }

    setIsOnline(data.is_online);
    showToast(data.message, "success");
  };

  // Countdown timer for job invite
  React.useEffect(() => {
    if (!incomingJob) return;

    const timer = setInterval(() => {
      setCountdown((c) => {
        if (c <= 1) {
          clearInterval(timer);
          handleDeclineJob();
          return 0;
        }
        return c - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [incomingJob]);

  const handleAcceptJob = async () => {
    if (!incomingJob) return;
    const { error } = await apiRequest(`/orders/${incomingJob.order_id}/accept`, {
      method: "POST",
    });
    if (error) {
      showToast(error.message, "error");
      return;
    }
    const orderId = incomingJob.order_id;
    setIncomingJob(null);
    showToast("Đã nhận đơn thành công! Đang chuyển đến đơn hàng...", "success");
    router.push(`/tech/orders/${orderId}`);
  };

  const handleDeclineJob = async () => {
    if (!incomingJob) return;
    await apiRequest(`/orders/${incomingJob.order_id}/decline`, {
      method: "POST",
    });
    setIncomingJob(null);
    showToast("Đã từ chối đơn hàng.", "info");
  };

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 max-w-lg mx-auto w-full space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-black text-white">Cổng Thợ Sửa Chữa</h1>
          <p className="text-xs text-slate-400">Fix 24/7 Huế – Đối tác kỹ thuật</p>
        </div>
        <Badge variant={isOnline ? "brand" : "neutral"} className="px-3 py-1">
          {isOnline ? "Trực tuyến" : "Ngoại tuyến"}
        </Badge>
      </div>

      {/* Online Toggle Card */}
      <div className="p-5 bg-surface-card border border-surface-border rounded-3xl shadow-xl flex items-center justify-between">
        <div className="space-y-1">
          <p className="text-sm font-bold text-white">
            {isOnline ? "Đang sẵn sàng nhận đơn" : "Đang tắt trực tuyến"}
          </p>
          <p className="text-xs text-slate-400">
            {isOnline
              ? "Hệ thống sẽ điều phối khách hàng trong bán kính 3 - 5km"
              : "Bật trực tuyến để bắt đầu nhận yêu cầu cứu hộ"}
          </p>
        </div>

        <button
          type="button"
          onClick={handleToggleOnline}
          className={`w-16 h-16 rounded-2xl flex items-center justify-center transition shadow-lg ${
            isOnline
              ? "bg-emerald-600 text-white shadow-emerald-950/60 ring-4 ring-emerald-500/20"
              : "bg-surface-elevated text-slate-400 border border-surface-border"
          }`}
        >
          <Power className="w-8 h-8" />
        </button>
      </div>

      {/* Technician Stats Recap */}
      <div className="grid grid-cols-3 gap-3">
        <div className="p-3.5 bg-surface-card border border-surface-border rounded-2xl text-center">
          <Star className="w-5 h-5 text-amber-400 mx-auto mb-1" />
          <span className="text-xs text-slate-400 block">Đánh giá</span>
          <span className="text-sm font-black text-white">
            {stats?.rating_avg ? `${stats.rating_avg} / 5` : "5.0"}
          </span>
        </div>

        <div className="p-3.5 bg-surface-card border border-surface-border rounded-2xl text-center">
          <Wallet className="w-5 h-5 text-emerald-400 mx-auto mb-1" />
          <span className="text-xs text-slate-400 block">Thu nhập</span>
          <span className="text-sm font-black text-white truncate block">
            {stats?.total_earned ? `${(stats.total_earned / 1000).toFixed(0)}k` : "0đ"}
          </span>
        </div>

        <div className="p-3.5 bg-surface-card border border-surface-border rounded-2xl text-center">
          <Wrench className="w-5 h-5 text-brand-400 mx-auto mb-1" />
          <span className="text-xs text-slate-400 block">Trạng thái</span>
          <span className="text-xs font-bold text-white uppercase">
            {approvalStatus === "approved" ? "Đã duyệt" : "Chờ duyệt"}
          </span>
        </div>
      </div>

      {/* Tech Quick Navigation Links (P4) */}
      <div className="space-y-2">
        <Link
          href="/tech/profile"
          className="flex items-center justify-between p-3.5 bg-surface-card border border-surface-border hover:border-slate-600 rounded-2xl transition"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-950/60 text-emerald-400 border border-emerald-500/30 flex items-center justify-center">
              <UserCheck className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-white">Hồ Sơ & Chứng Chỉ Nghề</h4>
              <p className="text-xs text-slate-400">CCCD mã hóa, chứng chỉ, chuyên môn & khu vực</p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </Link>

        <Link
          href="/tech/history"
          className="flex items-center justify-between p-3.5 bg-surface-card border border-surface-border hover:border-slate-600 rounded-2xl transition"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-brand-950/60 text-brand-400 border border-brand-500/30 flex items-center justify-center">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-white">Lịch Sử Ca Sửa Chữa</h4>
              <p className="text-xs text-slate-400">Danh sách đơn đã làm, thực nhận và đánh giá</p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </Link>

        <Link
          href="/tech/wallet"
          className="flex items-center justify-between p-3.5 bg-surface-card border border-surface-border hover:border-slate-600 rounded-2xl transition"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-amber-950/60 text-amber-400 border border-amber-500/30 flex items-center justify-center">
              <Wallet className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-white">Ví & Đối Soát Công Nợ</h4>
              <p className="text-xs text-slate-400">Nạp ví, đối soát hoa hồng 10% và trả nợ</p>
            </div>
          </div>
          <ChevronRight className="w-4 h-4 text-slate-400" />
        </Link>
      </div>

      {/* Demo Test Trigger Button (Allows manual testing of job invite modal) */}
      <div className="p-4 bg-surface-card/60 border border-surface-border/50 rounded-2xl text-center space-y-2">
        <p className="text-xs text-slate-400">Kiểm tra thông báo đơn điều phối:</p>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => {
            setIncomingJob({
              order_id: "demo-test-order",
              address: "Ngã 6 Hùng Vương, TP. Huế",
              distance_m: 850,
            });
            setCountdown(60);
          }}
          className="text-xs"
        >
          Giả lập nhận yêu cầu cứu hộ
        </Button>
      </div>

      {/* Incoming Job Modal with 60s Countdown (FR-BOOK-02) */}
      {incomingJob && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-sm bg-gradient-to-b from-emergency-950 via-surface-card to-surface-card border-2 border-emergency-500 rounded-3xl p-6 shadow-2xl space-y-5 animate-in zoom-in-95">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-emergency-400 font-bold text-sm uppercase tracking-wider">
                <AlertOctagon className="w-5 h-5 animate-bounce" />
                Yêu Cầu Cứu Hộ Mới!
              </span>
              <span className="w-10 h-10 rounded-full bg-emergency-600/30 border border-emergency-500 text-emergency-400 font-black flex items-center justify-center text-sm">
                {countdown}s
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="p-3 bg-surface-elevated rounded-xl space-y-1">
                <span className="text-slate-400 block">Địa điểm sự cố:</span>
                <p className="font-bold text-white text-sm flex items-center gap-1.5">
                  <MapPin className="w-4 h-4 text-brand-400 shrink-0" />
                  <span>{incomingJob.address}</span>
                </p>
                <span className="text-slate-400 text-[11px] block mt-1">
                  Khoảng cách: ~{(incomingJob.distance_m / 1000).toFixed(2)} km
                </span>
              </div>
            </div>

            <div className="flex gap-3">
              <Button
                variant="secondary"
                className="w-1/2 min-h-[48px] text-red-400 hover:text-red-300 border-red-500/40"
                onClick={handleDeclineJob}
              >
                <XCircle className="w-5 h-5 mr-1" />
                <span>Từ Chối</span>
              </Button>

              <Button
                variant="emergency"
                className="w-1/2 min-h-[48px] font-bold text-base shadow-lg shadow-emergency-950/60"
                onClick={handleAcceptJob}
              >
                <CheckCircle2 className="w-5 h-5 mr-1" />
                <span>Nhận Đơn</span>
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

