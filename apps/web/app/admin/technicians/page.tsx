"use client";

import * as React from "react";
import {
  Users,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Star,
  ShieldCheck,
  Search,
  ExternalLink,
  Award,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { useToast } from "@/components/ui/Toast";
import { adminApi, AdminTechnicianItem } from "@/lib/api";

export default function AdminTechniciansPage() {
  const { showToast } = useToast();

  const [technicians, setTechnicians] = React.useState<AdminTechnicianItem[]>([]);
  const [statusFilter, setStatusFilter] = React.useState<string>("pending");
  const [isLoading, setIsLoading] = React.useState(true);
  const [selectedTech, setSelectedTech] = React.useState<AdminTechnicianItem | null>(null);

  // Action modal
  const [actionType, setActionType] = React.useState<"approve" | "reject" | "suspend" | null>(null);
  const [actionReason, setActionReason] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const loadTechnicians = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await adminApi.getTechnicians(statusFilter || undefined);
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setTechnicians(data.items);
    }
  }, [statusFilter, showToast]);

  React.useEffect(() => {
    loadTechnicians();
  }, [loadTechnicians]);

  const handleAction = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTech || !actionType) return;

    setIsSubmitting(true);
    let res;
    if (actionType === "approve") {
      res = await adminApi.approveTechnician(selectedTech.user_id, actionReason || undefined);
    } else if (actionType === "reject") {
      res = await adminApi.rejectTechnician(selectedTech.user_id, actionReason);
    } else {
      res = await adminApi.suspendTechnician(selectedTech.user_id, actionReason);
    }
    setIsSubmitting(false);

    if (res.error) {
      showToast(res.error.message, "error");
      return;
    }

    showToast(res.data?.message || "Đã xử lý hồ sơ thợ thành công!", "success");
    setActionType(null);
    setActionReason("");
    loadTechnicians();
  };

  const formatVND = (amount: number) => {
    return new Intl.NumberFormat("vi-VN").format(amount) + " đ";
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "approved":
        return <Badge variant="brand">Đã Duyệt</Badge>;
      case "pending":
        return (
          <span className="text-[11px] font-bold text-amber-400 bg-amber-950/70 border border-amber-500/30 px-2 py-0.5 rounded-full">
            Chờ Duyệt
          </span>
        );
      case "rejected":
        return <Badge variant="emergency">Từ Chối</Badge>;
      case "suspended":
        return (
          <span className="text-[11px] font-bold text-red-400 bg-red-950/70 border border-red-500/40 px-2 py-0.5 rounded-full">
            Tạm Khóa
          </span>
        );
      default:
        return <Badge variant="neutral">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-white">Duyệt & Quản Lý Đối Tác Thợ</h2>
          <p className="text-xs text-slate-400">Xác thực CCCD, bằng cấp và kiểm soát trực tuyến (AT-07)</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="grid grid-cols-4 gap-1 p-1 bg-surface-card border border-surface-border rounded-xl text-xs">
        {[
          { id: "pending", label: "Chờ Duyệt" },
          { id: "approved", label: "Đã Duyệt" },
          { id: "suspended", label: "Tạm Khóa" },
          { id: "", label: "Tất Cả" },
        ].map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setStatusFilter(tab.id)}
            className={`py-1.5 rounded-lg font-semibold transition ${
              statusFilter === tab.id
                ? "bg-brand-600 text-white shadow-sm"
                : "text-slate-400 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Technicians List */}
      {isLoading ? (
        <div className="py-16 text-center text-xs text-slate-400">Đang tải danh sách đối tác thợ...</div>
      ) : technicians.length === 0 ? (
        <div className="p-8 text-center bg-surface-card border border-surface-border rounded-2xl text-xs text-slate-400">
          Không có thợ nào trong danh mục này.
        </div>
      ) : (
        <div className="space-y-3">
          {technicians.map((tech) => (
            <Card key={tech.profile_id} className="bg-surface-card border-surface-border">
              <CardContent className="p-4 space-y-3">
                {/* Header row */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={tech.portrait_url || "https://images.unsplash.com/photo-1540569014015-19a7be504e3a?w=100"}
                      alt={tech.name}
                      className="w-12 h-12 rounded-xl object-cover border border-surface-border shrink-0"
                    />
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-white text-sm">{tech.name}</h3>
                        {getStatusBadge(tech.approval_status)}
                      </div>
                      <p className="text-xs text-slate-400">
                        SĐT: <strong className="text-slate-200">{tech.phone}</strong> • CCCD:{" "}
                        <span className="font-mono text-brand-300">{tech.id_number_masked}</span>
                      </p>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        Khu vực: {tech.service_areas?.join(", ") || "Chưa chọn"}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Specialties & Badges */}
                <div className="space-y-1 text-xs">
                  <div className="flex flex-wrap gap-1">
                    {tech.specialties?.map((s, idx) => (
                      <span
                        key={idx}
                        className="text-[10px] bg-surface-elevated text-slate-300 px-2 py-0.5 rounded-md border border-surface-border"
                      >
                        {s}
                      </span>
                    ))}
                    {tech.badges?.map((b) => (
                      <span
                        key={b.id}
                        className="text-[10px] bg-amber-950/60 text-amber-300 px-2 py-0.5 rounded-md border border-amber-500/40"
                      >
                        {b.icon} {b.name}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Financials & Rating */}
                <div className="grid grid-cols-3 gap-2 p-2 bg-surface-elevated rounded-xl text-center text-xs border border-surface-border/50">
                  <div>
                    <span className="text-[10px] text-slate-400 block">Đánh giá</span>
                    <strong className="text-white flex items-center justify-center gap-1">
                      <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                      {tech.rating_avg.toFixed(1)} ({tech.rating_count})
                    </strong>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Thu nhập</span>
                    <strong className="text-emerald-400">{formatVND(tech.total_earned)}</strong>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-400 block">Nợ cước</span>
                    <strong className={tech.debt_amount > 500000 ? "text-red-400" : "text-slate-300"}>
                      {formatVND(tech.debt_amount)}
                    </strong>
                  </div>
                </div>

                {/* Certificates preview */}
                {tech.certificate_urls && tech.certificate_urls.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[11px] text-slate-400 block">
                      Chứng chỉ hành nghề ({tech.certificate_urls.length} file):
                    </span>
                    <div className="flex gap-2 overflow-x-auto pb-1">
                      {tech.certificate_urls.map((url, cIdx) => (
                        <a
                          key={cIdx}
                          href={url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[11px] text-brand-primary hover:underline flex items-center gap-1 shrink-0 bg-surface-elevated px-2 py-1 rounded-md border border-surface-border"
                        >
                          <span>Chứng chỉ #{cIdx + 1}</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action Buttons (AT-07) */}
                <div className="pt-2 border-t border-surface-border flex items-center justify-end gap-2">
                  {tech.approval_status !== "approved" && (
                    <Button
                      variant="primary"
                      size="default"
                      className="min-h-[40px] text-xs bg-emerald-600 hover:bg-emerald-500"
                      onClick={() => {
                        setSelectedTech(tech);
                        setActionType("approve");
                        setActionReason("Hồ sơ và chứng chỉ đã được thẩm định đạt chuẩn");
                      }}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                      <span>Phê Duyệt</span>
                    </Button>
                  )}

                  {tech.approval_status === "pending" && (
                    <Button
                      variant="secondary"
                      size="default"
                      className="min-h-[40px] text-xs text-red-400 border-red-500/40"
                      onClick={() => {
                        setSelectedTech(tech);
                        setActionType("reject");
                        setActionReason("");
                      }}
                    >
                      <XCircle className="w-3.5 h-3.5 mr-1" />
                      <span>Từ Chối</span>
                    </Button>
                  )}

                  {tech.approval_status === "approved" && (
                    <Button
                      variant="secondary"
                      size="default"
                      className="min-h-[40px] text-xs text-amber-400 border-amber-500/40"
                      onClick={() => {
                        setSelectedTech(tech);
                        setActionType("suspend");
                        setActionReason("");
                      }}
                    >
                      <AlertTriangle className="w-3.5 h-3.5 mr-1" />
                      <span>Tạm Khóa</span>
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Confirmation BottomSheet Modal */}
      <BottomSheet
        isOpen={actionType !== null}
        onClose={() => setActionType(null)}
        title={
          actionType === "approve"
            ? "Phê Duyệt Đối Tác Thợ"
            : actionType === "reject"
            ? "Từ Chối Hồ Sơ Thợ"
            : "Tạm Khóa Tài Khoản Thợ"
        }
      >
        <form onSubmit={handleAction} className="space-y-4">
          <p className="text-xs text-slate-300">
            Thao tác đối với thợ <strong>{selectedTech?.name}</strong> (SĐT: {selectedTech?.phone}). Hành động này sẽ được ghi nhận vào nhật ký kiểm toán hệ thống.
          </p>

          <Input
            label={actionType === "approve" ? "Ghi chú phê duyệt (tùy chọn)" : "Lý do *" }
            value={actionReason}
            onChange={(e) => setActionReason(e.target.value)}
            placeholder={
              actionType === "approve"
                ? "Chứng chỉ hợp lệ, kinh nghiệm 3 năm..."
                : "Nhập cụ thể lý do từ chối hoặc tạm đình chỉ..."
            }
            required={actionType !== "approve"}
          />

          <Button
            type="submit"
            variant={actionType === "approve" ? "primary" : "emergency"}
            size="lg"
            className="w-full font-bold"
            isLoading={isSubmitting}
          >
            {actionType === "approve"
              ? "Xác Nhận Phê Duyệt"
              : actionType === "reject"
              ? "Xác Nhận Từ Chối"
              : "Xác Nhận Tạm Khóa"}
          </Button>
        </form>
      </BottomSheet>
    </div>
  );
}

