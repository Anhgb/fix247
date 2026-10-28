"use client";

import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Clock,
  RotateCcw,
  DollarSign,
  User,
  Package,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { useToast } from "@/components/ui/Toast";
import { adminApi, AdminDisputeItem } from "@/lib/api";

export default function AdminDisputesPage() {
  const { showToast } = useToast();

  const [disputes, setDisputes] = React.useState<AdminDisputeItem[]>([]);
  const [statusFilter, setStatusFilter] = React.useState<string>("open");
  const [isLoading, setIsLoading] = React.useState(true);

  // Resolution modal
  const [selectedDispute, setSelectedDispute] = React.useState<AdminDisputeItem | null>(null);
  const [resolutionAction, setResolutionAction] = React.useState<"refund" | "reject" | null>(null);
  const [resolutionNote, setResolutionNote] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const loadDisputes = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await adminApi.getDisputes(statusFilter || undefined);
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setDisputes(data.items);
    }
  }, [statusFilter, showToast]);

  React.useEffect(() => {
    loadDisputes();
  }, [loadDisputes]);

  const handleResolve = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDispute || !resolutionAction) return;

    setIsSubmitting(true);
    const { data, error } = await adminApi.resolveDispute(
      selectedDispute.id,
      resolutionAction,
      resolutionNote
    );
    setIsSubmitting(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast(data?.message || "Đã xử lý khiếu nại thành công!", "success");
    setSelectedDispute(null);
    setResolutionAction(null);
    setResolutionNote("");
    loadDisputes();
  };

  const formatVND = (amount?: number | null) => {
    if (!amount) return "0 đ";
    return new Intl.NumberFormat("vi-VN").format(amount) + " đ";
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "--";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-black text-white">Xử Lý Khiếu Nại & Hoàn Tiền</h2>
          <p className="text-xs text-slate-400">Trọng tài tranh chấp & hoàn tiền qua State Machine (UC-11)</p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="grid grid-cols-3 gap-1 p-1 bg-surface-card border border-surface-border rounded-xl text-xs">
        {[
          { id: "open", label: "Đang Mở" },
          { id: "resolved", label: "Đã Hoàn Tiền" },
          { id: "closed", label: "Đã Đóng / Bác Bỏ" },
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

      {/* Disputes List */}
      {isLoading ? (
        <div className="py-16 text-center text-xs text-slate-400">Đang tải danh sách khiếu nại...</div>
      ) : disputes.length === 0 ? (
        <div className="p-8 text-center bg-surface-card border border-surface-border rounded-2xl text-xs text-slate-400">
          Không có khiếu nại nào trong mục này.
        </div>
      ) : (
        <div className="space-y-3">
          {disputes.map((d) => (
            <Card key={d.id} className="bg-surface-card border-surface-border">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-0.5">
                    <span className="font-mono text-xs font-bold text-brand-primary">
                      Đơn #{d.order_code || d.order_id.slice(0, 8)}
                    </span>
                    <p className="text-xs text-slate-400">
                      Người gửi: <strong>{d.opened_by_name || d.opened_by_phone || "Khách hàng"}</strong>
                    </p>
                  </div>

                  <Badge
                    variant={d.status === "open" ? "emergency" : d.status === "resolved" ? "brand" : "neutral"}
                  >
                    {d.status === "open" ? "Đang Mở" : d.status === "resolved" ? "Đã Hoàn Tiền" : "Đã Đóng"}
                  </Badge>
                </div>

                <div className="p-3 bg-surface-elevated rounded-xl space-y-1.5 text-xs">
                  <span className="text-slate-400 block text-[11px]">Lý do khiếu nại từ khách:</span>
                  <p className="text-white leading-relaxed font-medium">{d.reason}</p>
                </div>

                {d.resolution && (
                  <div className="p-2.5 bg-brand-950/40 border border-brand-500/30 rounded-xl text-xs text-slate-300">
                    <span className="text-brand-300 font-bold block text-[11px]">Kết quả giải quyết:</span>
                    <p>{d.resolution}</p>
                  </div>
                )}

                <div className="pt-2 border-t border-surface-border flex items-center justify-between text-xs">
                  <div>
                    <span className="text-[11px] text-slate-400">Giá trị đơn: </span>
                    <strong className="text-emerald-400">{formatVND(d.order_total)}</strong>
                  </div>

                  {d.status === "open" && (
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        size="default"
                        className="min-h-[36px] text-xs text-emerald-400 border-emerald-500/40"
                        onClick={() => {
                          setSelectedDispute(d);
                          setResolutionAction("refund");
                          setResolutionNote("Chấp thuận hoàn tiền cho khách hàng sau khi xác minh sự việc.");
                        }}
                      >
                        <RotateCcw className="w-3.5 h-3.5 mr-1" />
                        <span>Duyệt Hoàn Tiền</span>
                      </Button>

                      <Button
                        variant="secondary"
                        size="default"
                        className="min-h-[36px] text-xs text-slate-400"
                        onClick={() => {
                          setSelectedDispute(d);
                          setResolutionAction("reject");
                          setResolutionNote("");
                        }}
                      >
                        <XCircle className="w-3.5 h-3.5 mr-1" />
                        <span>Bác Bỏ</span>
                      </Button>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Resolution BottomSheet Modal */}
      <BottomSheet
        isOpen={resolutionAction !== null}
        onClose={() => {
          setResolutionAction(null);
          setSelectedDispute(null);
        }}
        title={resolutionAction === "refund" ? "Duyệt Hoàn Tiền Đơn Hàng" : "Bác Bỏ Khiếu Nại"}
      >
        <form onSubmit={handleResolve} className="space-y-4">
          <p className="text-xs text-slate-300">
            {resolutionAction === "refund"
              ? `Xác nhận chuyển trạng thái đơn hàng #${selectedDispute?.order_code} sang REFUNDED (hoàn trả ${formatVND(selectedDispute?.order_total)}). Thao tác này sẽ được ghi vào nhật ký kiểm toán.`
              : `Bác bỏ khiếu nại của đơn hàng #${selectedDispute?.order_code}. Khách hàng sẽ nhận được thông báo giải thích.`}
          </p>

          <Input
            label="Nội dung giải quyết / Lý do *"
            value={resolutionNote}
            onChange={(e) => setResolutionNote(e.target.value)}
            placeholder="Nhập nội dung giải trình..."
            required
          />

          <Button
            type="submit"
            variant={resolutionAction === "refund" ? "primary" : "emergency"}
            size="lg"
            className="w-full font-bold"
            isLoading={isSubmitting}
          >
            {resolutionAction === "refund" ? "Xác Nhận Hoàn Tiền (REFUNDED)" : "Xác Nhận Bác Bỏ"}
          </Button>
        </form>
      </BottomSheet>
    </div>
  );
}

