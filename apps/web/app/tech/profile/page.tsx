"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ShieldCheck,
  Award,
  Star,
  CheckCircle2,
  Clock,
  AlertTriangle,
  XCircle,
  Camera,
  FileText,
  Plus,
  Trash2,
  Wallet,
  Wrench,
  MapPin,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { Card, CardContent } from "@/components/ui/Card";
import { useToast } from "@/components/ui/Toast";
import { techApi, TechProfileResponse, TechProfileOnboardingRequest, apiUpload } from "@/lib/api";

const AVAILABLE_SPECIALTIES = [
  { id: "motorbike_rescue", name: "Cứu hộ xe máy lưu động" },
  { id: "motorbike_engine", name: "Động cơ & truyền động xe máy" },
  { id: "ac_cooling", name: "Điều hòa & máy lạnh gia đình" },
  { id: "washing_machine", name: "Máy giặt & sấy" },
  { id: "refrigerator", name: "Tủ lạnh & tủ đông" },
  { id: "home_electrical", name: "Hệ thống điện & thiết bị gia dụng" },
];

const AVAILABLE_AREAS = [
  "TP. Huế (Trung tâm)",
  "Khu vực Bắc Sông Hương (Phú Hội, Vỹ Dạ, An Cựu)",
  "Khu vực Nam Sông Hương (Kim Long, Hương Long)",
  "Thị xã Hương Trà",
  "Thị xã Hương Thủy",
  "Huyện Phú Vang",
];

export default function TechnicianProfilePage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [profile, setProfile] = React.useState<TechProfileResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isSaving, setIsSaving] = React.useState(false);

  // Form states
  const [idNumber, setIdNumber] = React.useState("");
  const [portraitUrl, setPortraitUrl] = React.useState("");
  const [certificateUrls, setCertificateUrls] = React.useState<string[]>([]);
  const [specialties, setSpecialties] = React.useState<string[]>([]);
  const [serviceAreas, setServiceAreas] = React.useState<string[]>([]);
  const [certInput, setCertInput] = React.useState("");

  const loadProfile = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await techApi.getProfile();
    setIsLoading(false);
    if (error) {
      // Profile may not exist yet, ignore 404
      return;
    }
    if (data) {
      setProfile(data);
      setPortraitUrl(data.portrait_url || "");
      setCertificateUrls(data.certificate_urls || []);
      setSpecialties(data.specialties || []);
      setServiceAreas(data.service_areas || []);
    }
  }, []);

  React.useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  const handleToggleSpecialty = (id: string) => {
    setSpecialties((prev) =>
      prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
    );
  };

  const handleToggleArea = (area: string) => {
    setServiceAreas((prev) =>
      prev.includes(area) ? prev.filter((a) => a !== area) : [...prev, area]
    );
  };

  const handleAddCertUrl = () => {
    if (!certInput.trim()) return;
    if (certificateUrls.length >= 5) {
      showToast("Tối đa 5 chứng chỉ/bằng cấp (SRS A-11)", "error");
      return;
    }
    setCertificateUrls((prev) => [...prev, certInput.trim()]);
    setCertInput("");
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!profile && !idNumber.trim()) {
      showToast("Vui lòng nhập số Căn cước công dân (CCCD).", "error");
      return;
    }
    if (specialties.length === 0) {
      showToast("Vui lòng chọn ít nhất 1 chuyên môn sửa chữa.", "error");
      return;
    }
    if (serviceAreas.length === 0) {
      showToast("Vui lòng chọn ít nhất 1 khu vực hoạt động.", "error");
      return;
    }

    setIsSaving(true);
    const payload: TechProfileOnboardingRequest = {
      id_number: idNumber.trim() || (profile ? "UNCHANGED" : ""),
      portrait_url: portraitUrl.trim() || "https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=400",
      certificate_urls: certificateUrls,
      specialties,
      service_areas: serviceAreas,
    };

    const { data, error } = await techApi.saveProfile(payload);
    setIsSaving(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast("Đã lưu hồ sơ đối tác thợ thành công!", "success");
    if (data) setProfile(data);
  };

  const getStatusBadge = (status: "pending" | "approved" | "rejected" | "suspended") => {
    switch (status) {
      case "approved":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-400 bg-emerald-950/70 border border-emerald-500/40 px-3 py-1 rounded-full">
            <CheckCircle2 className="w-4 h-4" />
            Đã Phê Duyệt
          </span>
        );
      case "pending":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-amber-400 bg-amber-950/70 border border-amber-500/40 px-3 py-1 rounded-full">
            <Clock className="w-4 h-4" />
            Đang Chờ Duyệt
          </span>
        );
      case "rejected":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-red-400 bg-red-950/70 border border-red-500/40 px-3 py-1 rounded-full">
            <XCircle className="w-4 h-4" />
            Từ Chối
          </span>
        );
      case "suspended":
        return (
          <span className="inline-flex items-center gap-1 text-xs font-bold text-red-500 bg-red-950/80 border border-red-500 px-3 py-1 rounded-full">
            <AlertTriangle className="w-4 h-4" />
            Tạm Khóa (Điểm Thấp / Nợ Cước)
          </span>
        );
    }
  };

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat("vi-VN").format(amount) + " đ";
  };

  return (
    <div className="flex-1 flex flex-col p-4 pb-16 space-y-5">
      {/* Top Header */}
      <div className="flex items-center justify-between pt-2">
        <div className="flex items-center gap-3">
          <Link
            href="/tech/dashboard"
            className="p-2 min-h-[44px] min-w-[44px] rounded-xl bg-surface-card border border-surface-border text-slate-300 hover:text-white flex items-center justify-center"
            aria-label="Quay lại bàn điều phối thợ"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-white flex items-center gap-2">
              <span>Hồ Sơ Đối Tác Thợ</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </h1>
            <p className="text-xs text-slate-400">Xác minh danh tính & chứng chỉ hành nghề</p>
          </div>
        </div>

        {profile && getStatusBadge(profile.approval_status)}
      </div>

      {/* Approval Status Banner */}
      {profile && (
        <div
          className={`p-4 rounded-2xl border text-xs space-y-1.5 leading-relaxed ${
            profile.approval_status === "approved"
              ? "bg-emerald-950/40 border-emerald-500/30 text-emerald-300"
              : profile.approval_status === "pending"
              ? "bg-amber-950/40 border-amber-500/30 text-amber-300"
              : "bg-red-950/40 border-red-500/30 text-red-300"
          }`}
        >
          <div className="flex items-center gap-2 font-bold text-sm">
            {profile.approval_status === "approved" ? (
              <>
                <CheckCircle2 className="w-4 h-4" />
                <span>Hồ sơ đã được xác minh & phê duyệt</span>
              </>
            ) : profile.approval_status === "pending" ? (
              <>
                <Clock className="w-4 h-4" />
                <span>Hồ sơ đang chờ duyệt xác minh (UC-08, FR-TECH-01)</span>
              </>
            ) : (
              <>
                <AlertTriangle className="w-4 h-4" />
                <span>Tài khoản hiện đang bị hạn chế nhận việc</span>
              </>
            )}
          </div>
          <p className="text-slate-300">
            {profile.approval_status === "approved"
              ? "Bạn đã đủ điều kiện bật chế độ Trực tuyến để nhận các đơn cứu hộ và sửa chữa trong khu vực."
              : profile.approval_status === "pending"
              ? "Hệ thống Fix 24/7 đang kiểm tra tính hợp lệ của CCCD và chứng chỉ nghề của bạn. Quá trình kiểm tra thông thường mất từ 1 - 24 giờ."
              : profile.approval_note ||
                "Vui lòng liên hệ ban quản trị Fix 24/7 qua hotline để được hướng dẫn mở khóa tài khoản."}
          </p>
        </div>
      )}

      {/* Rating & Badges Card */}
      {profile && (
        <Card className="bg-surface-card border-surface-border">
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Star className="w-5 h-5 text-amber-400 fill-amber-400" />
                <span className="font-black text-white text-base">
                  {profile.rating_avg ? profile.rating_avg.toFixed(1) : "5.0"}
                </span>
                <span className="text-xs text-slate-400">({profile.rating_count} đánh giá)</span>
              </div>

              <div className="text-right">
                <span className="text-[11px] text-slate-400 block">Thu nhập lũy kế</span>
                <strong className="text-sm font-bold text-emerald-400">
                  {formatVND(profile.total_earned)}
                </strong>
              </div>
            </div>

            {/* Badges List (FR-TECH-04) */}
            {profile.badges && profile.badges.length > 0 && (
              <div className="pt-2 border-t border-surface-border space-y-1.5">
                <span className="text-xs font-semibold text-slate-300 block">Huy hiệu đạt được:</span>
                <div className="flex flex-wrap gap-1.5">
                  {profile.badges.map((b) => (
                    <span
                      key={b.id}
                      className="inline-flex items-center gap-1.5 text-[11px] font-bold bg-amber-950/60 border border-amber-500/40 text-amber-300 px-2.5 py-1 rounded-xl"
                      title={b.description}
                    >
                      <span>{b.icon}</span>
                      <span>{b.name}</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Onboarding & Edit Form */}
      <form onSubmit={handleSaveProfile} className="space-y-4">
        {/* CCCD / ID Card (Encrypted AES-256) */}
        <div className="p-4 bg-surface-card border border-surface-border rounded-2xl space-y-2">
          <div className="flex items-center gap-2 text-slate-300 text-xs font-semibold">
            <Lock className="w-4 h-4 text-brand-400" />
            <span>Căn Cước Công Dân (CCCD) - Mã Hóa Tuyệt Đối (NFR-04)</span>
          </div>

          {profile?.id_number_masked ? (
            <div className="flex items-center justify-between p-3 bg-surface-elevated rounded-xl border border-surface-border">
              <div>
                <span className="text-[11px] text-slate-400 block">Số định danh đã lưu:</span>
                <strong className="text-sm font-bold text-white tracking-widest">
                  {profile.id_number_masked}
                </strong>
              </div>
              <Badge variant="brand" className="text-[11px]">
                Đã mã hóa AES-256
              </Badge>
            </div>
          ) : (
            <Input
              label="Số Căn cước công dân (12 chữ số) *"
              value={idNumber}
              onChange={(e) => setIdNumber(e.target.value)}
              placeholder="046093xxxxxx"
              required={!profile}
              helperText="Số CCCD được mã hóa bằng chuẩn AES-256-GCM, không hiển thị công khai"
            />
          )}
        </div>

        {/* Portrait Photo */}
        <div className="p-4 bg-surface-card border border-surface-border rounded-2xl space-y-2">
          <label className="text-xs font-semibold text-slate-300 block">
            Ảnh chân dung thợ (Hiển thị cho khách khi nhận đơn)
          </label>
          <Input
            value={portraitUrl}
            onChange={(e) => setPortraitUrl(e.target.value)}
            placeholder="URL ảnh chân dung đại diện"
          />
          {portraitUrl && (
            <div className="pt-1 flex items-center gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={portraitUrl}
                alt="Chân dung thợ"
                className="w-14 h-14 rounded-full object-cover border-2 border-brand-primary"
              />
              <span className="text-xs text-slate-400">Xem trước ảnh đại diện</span>
            </div>
          )}
        </div>

        {/* Certificate URLs (Max 5, A-11) */}
        <div className="p-4 bg-surface-card border border-surface-border rounded-2xl space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-xs font-semibold text-slate-300">
              Chứng chỉ nghề / Bằng cấp ({certificateUrls.length}/5)
            </label>
            <span className="text-[11px] text-slate-400">Tối đa 5 chứng chỉ</span>
          </div>

          <div className="flex gap-2">
            <Input
              value={certInput}
              onChange={(e) => setCertInput(e.target.value)}
              placeholder="Dán đường dẫn ảnh chứng chỉ..."
              className="text-xs"
              disabled={certificateUrls.length >= 5}
            />
            <Button
              type="button"
              variant="secondary"
              size="default"
              onClick={handleAddCertUrl}
              disabled={certificateUrls.length >= 5 || !certInput.trim()}
              className="shrink-0 text-xs"
            >
              <Plus className="w-4 h-4 mr-1" />
              <span>Thêm</span>
            </Button>
          </div>

          {certificateUrls.length > 0 && (
            <div className="space-y-1.5 pt-1">
              {certificateUrls.map((url, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between p-2.5 bg-surface-elevated rounded-xl border border-surface-border text-xs"
                >
                  <span className="truncate max-w-[240px] text-slate-300">
                    📄 Chứng chỉ #{idx + 1}: {url}
                  </span>
                  <button
                    type="button"
                    onClick={() => setCertificateUrls((prev) => prev.filter((_, i) => i !== idx))}
                    className="text-slate-400 hover:text-red-400 p-1"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Specialties */}
        <div className="p-4 bg-surface-card border border-surface-border rounded-2xl space-y-2.5">
          <label className="text-xs font-semibold text-slate-300 block">
            Chuyên môn sửa chữa (Chọn các lĩnh vực thành thạo) *
          </label>
          <div className="grid grid-cols-1 gap-2">
            {AVAILABLE_SPECIALTIES.map((spec) => {
              const selected = specialties.includes(spec.id);
              return (
                <button
                  key={spec.id}
                  type="button"
                  onClick={() => handleToggleSpecialty(spec.id)}
                  className={`p-3 rounded-xl border text-left text-xs font-semibold transition flex items-center justify-between min-h-[44px] ${
                    selected
                      ? "bg-brand-950/70 border-brand-500 text-brand-300 ring-2 ring-brand-500/20"
                      : "bg-surface-elevated border-surface-border text-slate-400"
                  }`}
                >
                  <span>{spec.name}</span>
                  {selected && <CheckCircle2 className="w-4 h-4 text-brand-400" />}
                </button>
              );
            })}
          </div>
        </div>

        {/* Service Areas */}
        <div className="p-4 bg-surface-card border border-surface-border rounded-2xl space-y-2.5">
          <label className="text-xs font-semibold text-slate-300 block">
            Khu vực hoạt động sẵn sàng nhận đơn *
          </label>
          <div className="grid grid-cols-1 gap-2">
            {AVAILABLE_AREAS.map((area) => {
              const selected = serviceAreas.includes(area);
              return (
                <button
                  key={area}
                  type="button"
                  onClick={() => handleToggleArea(area)}
                  className={`p-3 rounded-xl border text-left text-xs font-semibold transition flex items-center justify-between min-h-[44px] ${
                    selected
                      ? "bg-brand-950/70 border-brand-500 text-brand-300 ring-2 ring-brand-500/20"
                      : "bg-surface-elevated border-surface-border text-slate-400"
                  }`}
                >
                  <span className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-400" />
                    {area}
                  </span>
                  {selected && <CheckCircle2 className="w-4 h-4 text-brand-400" />}
                </button>
              );
            })}
          </div>
        </div>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="w-full min-h-[48px] font-bold text-base"
          isLoading={isSaving}
        >
          {profile ? "Cập Nhật Hồ Sơ Thợ" : "Gửi Hồ Sơ Xét Duyệt Đối Tác"}
        </Button>
      </form>
    </div>
  );
}

