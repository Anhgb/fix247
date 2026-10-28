"use client";

import * as React from "react";
import {
  BarChart3,
  TrendingUp,
  DollarSign,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  MapPin,
  AlertOctagon,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { adminApi, AdminDashboardStats } from "@/lib/api";

export default function AdminDashboardPage() {
  const { showToast } = useToast();
  const [stats, setStats] = React.useState<AdminDashboardStats | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  const loadStats = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await adminApi.getDashboard();
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setStats(data);
    }
  }, [showToast]);

  React.useEffect(() => {
    loadStats();
  }, [loadStats]);

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat("vi-VN").format(amount) + " đ";
  };

  const formatSec = (sec?: number | null) => {
    if (!sec) return "--";
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}p ${s}s`;
  };

  return (
    <div className="space-y-5">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-white">Chỉ Số Vận Hành Hệ Thống</h2>
          <p className="text-xs text-slate-400">Thời gian thực • Khu vực TP. Huế (FR-ADM-01)</p>
        </div>
        <Button variant="secondary" size="default" onClick={loadStats} isLoading={isLoading} className="text-xs">
          <RefreshCw className="w-3.5 h-3.5 mr-1" />
          <span>Làm mới</span>
        </Button>
      </div>

      {/* Budget Alerts (>= 80%) */}
      {(stats?.ai_budget_alert || stats?.maps_budget_alert) && (
        <div className="p-4 bg-red-950/50 border border-red-500/50 rounded-2xl space-y-1.5 animate-pulse">
          <div className="flex items-center gap-2 text-red-400 font-bold text-xs uppercase tracking-wider">
            <AlertOctagon className="w-4 h-4" />
            <span>Cảnh Báo Vượt Hạn Mức Chi Phí (&ge; 80% Ngân Sách)</span>
          </div>
          {stats?.ai_budget_alert && (
            <p className="text-xs text-slate-300">
              • <strong>Chi phí AI (Gemini):</strong> Đã tiêu {formatVND(stats.ai_monthly_spend_vnd)} / {formatVND(stats.ai_monthly_budget_vnd)} tháng này.
            </p>
          )}
          {stats?.maps_budget_alert && (
            <p className="text-xs text-slate-300">
              • <strong>Chi phí Bản đồ (Maps/Geocoding):</strong> Đã tiêu {formatVND(stats.maps_monthly_spend_vnd)} / {formatVND(stats.maps_monthly_budget_vnd)} tháng này.
            </p>
          )}
        </div>
      )}

      {/* KPI Summary Cards */}
      <div className="grid grid-cols-2 gap-3">
        {/* GMV */}
        <Card className="bg-gradient-to-br from-emerald-950/60 to-surface-card border-emerald-500/30">
          <CardContent className="p-3.5 space-y-1">
            <span className="text-xs text-emerald-300 font-semibold flex items-center gap-1">
              <DollarSign className="w-3.5 h-3.5" />
              Tổng GMV Hoàn Thành
            </span>
            <strong className="text-lg font-black text-white block">
              {formatVND(stats?.gmv_total || 0)}
            </strong>
            <span className="text-[11px] text-slate-400 block">
              Hôm nay: {formatVND(stats?.gmv_today || 0)}
            </span>
          </CardContent>
        </Card>

        {/* Commission */}
        <Card className="bg-gradient-to-br from-brand-950/60 to-surface-card border-brand-500/30">
          <CardContent className="p-3.5 space-y-1">
            <span className="text-xs text-brand-300 font-semibold flex items-center gap-1">
              <TrendingUp className="w-3.5 h-3.5" />
              Hoa Hồng Nền Tảng
            </span>
            <strong className="text-lg font-black text-white block">
              {formatVND(stats?.commission_total || 0)}
            </strong>
            <span className="text-[11px] text-slate-400 block">Tỷ lệ mặc định: 10%</span>
          </CardContent>
        </Card>

        {/* Orders */}
        <Card className="bg-surface-card border-surface-border">
          <CardContent className="p-3.5 space-y-1">
            <span className="text-xs text-slate-400 font-semibold block">Tổng Đơn Hàng</span>
            <strong className="text-lg font-black text-white block">{stats?.orders_total || 0}</strong>
            <span className="text-[11px] text-slate-400 block">Đơn hôm nay: {stats?.orders_today || 0}</span>
          </CardContent>
        </Card>

        {/* Time to accept */}
        <Card className="bg-surface-card border-surface-border">
          <CardContent className="p-3.5 space-y-1">
            <span className="text-xs text-slate-400 font-semibold flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-amber-400" />
              Thời Gian Nhận Đơn
            </span>
            <strong className="text-lg font-black text-white block">
              {formatSec(stats?.median_time_to_accept_sec)}
            </strong>
            <span className="text-[11px] text-slate-400 block">Trung vị (Median SOS)</span>
          </CardContent>
        </Card>
      </div>

      {/* Operational Rates */}
      <div className="grid grid-cols-2 gap-3">
        <div className="p-3 bg-surface-card border border-surface-border rounded-2xl space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">Tỷ lệ hoàn thành</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <strong className="text-base font-bold text-white block">{stats?.completion_rate_pct || 0}%</strong>
        </div>

        <div className="p-3 bg-surface-card border border-surface-border rounded-2xl space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400">Tỷ lệ khiếu nại</span>
            <AlertTriangle className="w-4 h-4 text-red-400" />
          </div>
          <strong className="text-base font-bold text-white block">{stats?.dispute_rate_pct || 0}%</strong>
        </div>
      </div>

      {/* AI Performance & Cost Tracking */}
      <Card className="bg-surface-card border-surface-border">
        <CardContent className="p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-surface-border pb-2.5">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-400" />
              <h3 className="font-bold text-white text-sm">Chỉ Số Trí Tuệ Nhân Tạo (Gemini)</h3>
            </div>
            <Badge variant="brand">{stats?.ai_top3_accuracy_pct || 0}% Chính xác</Badge>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-2.5 bg-surface-elevated rounded-xl">
              <span className="text-slate-400 block text-[11px]">Tổng lượt gọi AI</span>
              <strong className="text-white text-sm">{stats?.ai_calls_total || 0} lượt</strong>
            </div>
            <div className="p-2.5 bg-surface-elevated rounded-xl">
              <span className="text-slate-400 block text-[11px]">Chi phí ước tính / lượt</span>
              <strong className="text-emerald-400 text-sm">~{stats?.ai_cost_per_call_vnd || 150} đ</strong>
            </div>
            <div className="p-2.5 bg-surface-elevated rounded-xl">
              <span className="text-slate-400 block text-[11px]">Chi phí AI hôm nay</span>
              <strong className="text-slate-200 text-sm">{formatVND(stats?.ai_daily_spend_vnd || 0)}</strong>
            </div>
            <div className="p-2.5 bg-surface-elevated rounded-xl">
              <span className="text-slate-400 block text-[11px]">Chi phí AI tháng này</span>
              <strong className="text-slate-200 text-sm">{formatVND(stats?.ai_monthly_spend_vnd || 0)}</strong>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Maps & Geocoding Spend Tracking */}
      <Card className="bg-surface-card border-surface-border">
        <CardContent className="p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-surface-border pb-2.5">
            <div className="flex items-center gap-2">
              <MapPin className="w-4 h-4 text-emerald-400" />
              <h3 className="font-bold text-white text-sm">Chi Phí Bản Đồ & Định Vị</h3>
            </div>
            <Badge variant="neutral">OpenStreetMap (Free)</Badge>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="p-2.5 bg-surface-elevated rounded-xl">
              <span className="text-slate-400 block text-[11px]">Chi phí bản đồ hôm nay</span>
              <strong className="text-slate-200 text-sm">{formatVND(stats?.maps_daily_spend_vnd || 0)}</strong>
            </div>
            <div className="p-2.5 bg-surface-elevated rounded-xl">
              <span className="text-slate-400 block text-[11px]">Chi phí bản đồ tháng này</span>
              <strong className="text-slate-200 text-sm">{formatVND(stats?.maps_monthly_spend_vnd || 0)}</strong>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
