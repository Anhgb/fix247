"use client";

import * as React from "react";
import { Settings, Save, ShieldCheck, DollarSign, Clock, MapPin, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { adminApi, PlatformSettings } from "@/lib/api";

export default function AdminSettingsPage() {
  const { showToast } = useToast();

  const [settings, setSettings] = React.useState<PlatformSettings | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isSaving, setIsSaving] = React.useState(false);

  // Editable form fields
  const [commissionRate, setCommissionRate] = React.useState(0.10);
  const [nightSurcharge, setNightSurcharge] = React.useState(15000);
  const [surveyFee, setSurveyFee] = React.useState(30000);
  const [travelFee, setTravelFee] = React.useState(20000);
  const [emergencyRadiusKm, setEmergencyRadiusKm] = React.useState(3.0);
  const [aiDailyQuotaAnon, setAiDailyQuotaAnon] = React.useState(2);
  const [aiDailyQuotaUser, setAiDailyQuotaUser] = React.useState(10);
  const [monthlyAiBudgetVnd, setMonthlyAiBudgetVnd] = React.useState(5000000);
  const [monthlyMapsBudgetVnd, setMonthlyMapsBudgetVnd] = React.useState(3000000);

  const loadSettings = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await adminApi.getSettings();
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setSettings(data);
      setCommissionRate(data.commission_rate);
      setNightSurcharge(data.night_surcharge);
      setSurveyFee(data.survey_fee);
      setTravelFee(data.travel_fee);
      setEmergencyRadiusKm(data.emergency_radius_km);
      setAiDailyQuotaAnon(data.ai_daily_quota_anon);
      setAiDailyQuotaUser(data.ai_daily_quota_user);
      setMonthlyAiBudgetVnd(data.monthly_ai_budget_vnd);
      setMonthlyMapsBudgetVnd(data.monthly_maps_budget_vnd);
    }
  }, [showToast]);

  React.useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    const payload: Partial<PlatformSettings> = {
      commission_rate: Number(commissionRate),
      night_surcharge: Number(nightSurcharge),
      survey_fee: Number(surveyFee),
      travel_fee: Number(travelFee),
      emergency_radius_km: Number(emergencyRadiusKm),
      ai_daily_quota_anon: Number(aiDailyQuotaAnon),
      ai_daily_quota_user: Number(aiDailyQuotaUser),
      monthly_ai_budget_vnd: Number(monthlyAiBudgetVnd),
      monthly_maps_budget_vnd: Number(monthlyMapsBudgetVnd),
    };

    const { data, error } = await adminApi.updateSettings(payload);
    setIsSaving(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast("Đã lưu cấu hình nền tảng thành công (Hiệu lực cho đơn mới)!", "success");
    if (data) {
      setSettings(data);
    }
  };

  if (isLoading) {
    return <div className="py-16 text-center text-xs text-slate-400">Đang tải cấu hình hệ thống...</div>;
  }

  return (
    <div className="space-y-4">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-white">Cấu Hình Nền Tảng Fix 24/7</h2>
          <p className="text-xs text-slate-400">Thay đổi có hiệu lực cho các đơn hàng mới (FR-ADM-04)</p>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-4">
        {/* Commission & Fees Card */}
        <Card className="bg-surface-card border-surface-border">
          <CardContent className="p-4 space-y-3">
            <h3 className="font-bold text-white text-sm flex items-center gap-2 border-b border-surface-border pb-2">
              <DollarSign className="w-4 h-4 text-emerald-400" />
              <span>Hoa Hồng & Biểu Phí Dịch Vụ</span>
            </h3>

            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Tỷ lệ hoa hồng nền tảng (0.08 - 0.12)"
                type="number"
                step="0.01"
                min="0.05"
                max="0.20"
                value={commissionRate}
                onChange={(e) => setCommissionRate(Number(e.target.value))}
                helperText="Mặc định: 0.10 (10%)"
                required
              />

              <Input
                label="Phụ thu ban đêm (22h - 5h) (VND)"
                type="number"
                step="1000"
                value={nightSurcharge}
                onChange={(e) => setNightSurcharge(Number(e.target.value))}
                helperText="100% trả cho thợ (BR-04)"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Phí khảo sát kiểm tra (VND)"
                type="number"
                step="1000"
                value={surveyFee}
                onChange={(e) => setSurveyFee(Number(e.target.value))}
                helperText="Thu khi khách từ chối sửa (BR-07)"
                required
              />

              <Input
                label="Phí di chuyển / hủy sau đi (VND)"
                type="number"
                step="1000"
                value={travelFee}
                onChange={(e) => setTravelFee(Number(e.target.value))}
                helperText="Đền bù cho thợ (BR-06)"
                required
              />
            </div>
          </CardContent>
        </Card>

        {/* Dispatch & AI Quotas Card */}
        <Card className="bg-surface-card border-surface-border">
          <CardContent className="p-4 space-y-3">
            <h3 className="font-bold text-white text-sm flex items-center gap-2 border-b border-surface-border pb-2">
              <MapPin className="w-4 h-4 text-brand-400" />
              <span>Bán Kính Điều Phối & Hạn Mức AI</span>
            </h3>

            <Input
              label="Bán kính điều phối khẩn cấp ban đầu (km)"
              type="number"
              step="0.5"
              min="1"
              max="20"
              value={emergencyRadiusKm}
              onChange={(e) => setEmergencyRadiusKm(Number(e.target.value))}
              helperText="Mặc định 3km, tự mở rộng 5km sau 90 giây"
              required
            />

            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Quota AI khách vãng lai / ngày"
                type="number"
                value={aiDailyQuotaAnon}
                onChange={(e) => setAiDailyQuotaAnon(Number(e.target.value))}
                helperText="FR-DIAG-07: Mặc định 2"
                required
              />

              <Input
                label="Quota AI khách đăng nhập / ngày"
                type="number"
                value={aiDailyQuotaUser}
                onChange={(e) => setAiDailyQuotaUser(Number(e.target.value))}
                helperText="FR-DIAG-07: Mặc định 10"
                required
              />
            </div>
          </CardContent>
        </Card>

        {/* Budgets Card */}
        <Card className="bg-surface-card border-surface-border">
          <CardContent className="p-4 space-y-3">
            <h3 className="font-bold text-white text-sm flex items-center gap-2 border-b border-surface-border pb-2">
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>Ngân Sách Tháng & Cảnh Báo (VND)</span>
            </h3>

            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Ngân sách AI (Gemini) tháng"
                type="number"
                step="100000"
                value={monthlyAiBudgetVnd}
                onChange={(e) => setMonthlyAiBudgetVnd(Number(e.target.value))}
                helperText="Cảnh báo khi chạm 80%"
                required
              />

              <Input
                label="Ngân sách Bản đồ tháng"
                type="number"
                step="100000"
                value={monthlyMapsBudgetVnd}
                onChange={(e) => setMonthlyMapsBudgetVnd(Number(e.target.value))}
                helperText="Cảnh báo khi chạm 80%"
                required
              />
            </div>
          </CardContent>
        </Card>

        <Button type="submit" variant="primary" size="lg" className="w-full font-bold" isLoading={isSaving}>
          <Save className="w-4 h-4 mr-2" />
          <span>Lưu Thay Đổi Cấu Hình Nền Tảng</span>
        </Button>
      </form>
    </div>
  );
}

