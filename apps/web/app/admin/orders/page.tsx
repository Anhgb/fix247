"use client";

import * as React from "react";
import {
  Package,
  Search,
  Filter,
  MapPin,
  Clock,
  Phone,
  User,
  Wrench,
  AlertOctagon,
  RefreshCw,
  Eye,
  Edit3,
  UserCheck,
  XCircle,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { BottomSheet } from "@/components/ui/BottomSheet";
import { useToast } from "@/components/ui/Toast";
import { adminApi, AdminOrderItem } from "@/lib/api";

const ORDER_STATUSES = [
  "ALL",
  "SEARCHING",
  "ACCEPTED",
  "ON_THE_WAY",
  "SURVEYING",
  "QUOTE_PENDING",
  "IN_REPAIR",
  "AWAITING_CONFIRM",
  "COMPLETED",
  "DISPUTED",
  "NO_TECH",
  "CANCELLED",
  "REFUNDED",
];

export default function AdminOrdersPage() {
  const { showToast } = useToast();

  const [orders, setOrders] = React.useState<AdminOrderItem[]>([]);
  const [totalCount, setTotalCount] = React.useState(0);
  const [statusFilter, setStatusFilter] = React.useState("ALL");
  const [search, setSearch] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(true);

  // Detail & Intervention Modal
  const [selectedOrderId, setSelectedOrderId] = React.useState<string | null>(null);
  const [orderDetail, setOrderDetail] = React.useState<any>(null);
  const [isLoadingDetail, setIsLoadingDetail] = React.useState(false);

  // Intervention forms
  const [activeIntervention, setActiveIntervention] = React.useState<"transition" | "reassign" | "cancel" | "note" | null>(null);
  const [targetStatus, setTargetStatus] = React.useState("COMPLETED");
  const [interventionReason, setInterventionReason] = React.useState("");
  const [targetTechId, setTargetTechId] = React.useState("");
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const loadOrders = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await adminApi.getOrders({
      status: statusFilter === "ALL" ? undefined : statusFilter,
      search: search.trim() || undefined,
    });
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setOrders(data.items);
      setTotalCount(data.total);
    }
  }, [statusFilter, search, showToast]);

  React.useEffect(() => {
    loadOrders();
  }, [loadOrders]);

  const handleOpenDetail = async (orderId: string) => {
    setSelectedOrderId(orderId);
    setIsLoadingDetail(true);
    const { data, error } = await adminApi.getOrderDetail(orderId);
    setIsLoadingDetail(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    setOrderDetail(data);
  };

  const handleInterventionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrderId || !activeIntervention) return;

    setIsSubmitting(true);
    let res;
    if (activeIntervention === "transition") {
      res = await adminApi.transitionOrder(selectedOrderId, targetStatus, interventionReason);
    } else if (activeIntervention === "reassign") {
      res = await adminApi.reassignTechnician(selectedOrderId, targetTechId, interventionReason);
    } else if (activeIntervention === "cancel") {
      res = await adminApi.cancelOrder(selectedOrderId, interventionReason);
    } else {
      res = await adminApi.addOrderNote(selectedOrderId, interventionReason);
    }
    setIsSubmitting(false);

    if (res.error) {
      showToast(res.error.message, "error");
      return;
    }

    showToast("Đã thực hiện can thiệp đơn hàng thành công!", "success");
    setActiveIntervention(null);
    setInterventionReason("");
    // Refresh detail and list
    handleOpenDetail(selectedOrderId);
    loadOrders();
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
          <h2 className="text-lg font-black text-white">Tra Cứu & Can Thiệp Đơn Hàng</h2>
          <p className="text-xs text-slate-400">Kiểm soát tiến độ và can thiệp qua State Machine (FR-ADM-03)</p>
        </div>
      </div>

      {/* Search & Status Filters */}
      <div className="space-y-2">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3.5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm theo địa chỉ hoặc ghi chú khách hàng..."
            className="w-full bg-surface-card border border-surface-border rounded-xl pl-9 pr-3 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        {/* Status scroll tags */}
        <div className="flex gap-1.5 overflow-x-auto scrollbar-none pb-1">
          {ORDER_STATUSES.map((st) => (
            <button
              key={st}
              type="button"
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold whitespace-nowrap transition ${
                statusFilter === st
                  ? "bg-brand-600 text-white"
                  : "bg-surface-card text-slate-400 hover:text-white border border-surface-border"
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Orders List */}
      {isLoading ? (
        <div className="py-16 text-center text-xs text-slate-400">Đang tải danh sách đơn hàng...</div>
      ) : orders.length === 0 ? (
        <div className="p-8 text-center bg-surface-card border border-surface-border rounded-2xl text-xs text-slate-400">
          Không tìm thấy đơn hàng nào phù hợp với bộ lọc.
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map((o) => (
            <Card key={o.id} className="bg-surface-card border-surface-border">
              <CardContent className="p-3.5 space-y-2.5">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-brand-primary">
                      #{o.id.slice(0, 8)}
                    </span>
                    <Badge variant={o.mode === "emergency" ? "emergency" : "brand"} className="text-[10px]">
                      {o.mode === "emergency" ? "Khẩn Cấp" : "Hẹn Giờ"}
                    </Badge>
                  </div>
                  <Badge variant="neutral" className="text-[10px] font-mono">
                    {o.status}
                  </Badge>
                </div>

                <div className="space-y-1 text-xs">
                  <p className="text-white font-medium flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span className="truncate">{o.address}</span>
                  </p>
                  <p className="text-slate-400 flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                    <span>Khách: {o.customer_name} ({o.customer_phone})</span>
                  </p>
                  {o.technician_phone && (
                    <p className="text-slate-400 flex items-center gap-1.5">
                      <Wrench className="w-3.5 h-3.5 text-brand-400 shrink-0" />
                      <span>Thợ: {o.technician_name || o.technician_phone}</span>
                    </p>
                  )}
                </div>

                <div className="pt-2 border-t border-surface-border flex items-center justify-between text-xs">
                  <div>
                    <span className="text-[11px] text-slate-400">Tổng tiền: </span>
                    <strong className="text-emerald-400">{formatVND(o.total || o.final_quote)}</strong>
                  </div>

                  <Button
                    variant="secondary"
                    size="default"
                    className="min-h-[36px] text-xs px-2.5"
                    onClick={() => handleOpenDetail(o.id)}
                  >
                    <Eye className="w-3.5 h-3.5 mr-1" />
                    <span>Chi Tiết & Can Thiệp</span>
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Order Detail & Interventions BottomSheet */}
      <BottomSheet
        isOpen={selectedOrderId !== null}
        onClose={() => {
          setSelectedOrderId(null);
          setOrderDetail(null);
          setActiveIntervention(null);
        }}
        title={`Chi Tiết Đơn Hàng #${selectedOrderId?.slice(0, 8)}`}
      >
        {isLoadingDetail || !orderDetail ? (
          <div className="py-12 text-center text-xs text-slate-400">Đang tải thông tin chi tiết đơn...</div>
        ) : (
          <div className="space-y-4">
            {/* Order status banner */}
            <div className="p-3 bg-surface-elevated rounded-xl flex items-center justify-between text-xs">
              <div>
                <span className="text-slate-400 block text-[11px]">Trạng thái hiện tại:</span>
                <strong className="text-white text-sm font-mono">{orderDetail.status}</strong>
              </div>
              <div className="text-right">
                <span className="text-slate-400 block text-[11px]">Tổng hóa đơn:</span>
                <strong className="text-emerald-400 text-sm font-bold">{formatVND(orderDetail.total)}</strong>
              </div>
            </div>

            {/* Customer & Tech Info */}
            <div className="p-3 bg-surface-elevated rounded-xl space-y-1.5 text-xs">
              <p className="text-slate-300">
                Khách hàng: <strong>{orderDetail.customer?.name}</strong> ({orderDetail.customer?.phone})
              </p>
              <p className="text-slate-300">
                Thợ kỹ thuật: <strong>{orderDetail.technician?.name || "Chưa gán thợ"}</strong>{" "}
                {orderDetail.technician?.phone ? `(${orderDetail.technician?.phone})` : ""}
              </p>
              <p className="text-slate-300">Địa chỉ: {orderDetail.address}</p>
            </div>

            {/* Line Items */}
            {orderDetail.items && orderDetail.items.length > 0 && (
              <div className="space-y-1 text-xs">
                <span className="font-bold text-slate-300 block">Hạng mục báo giá:</span>
                <div className="p-2 bg-surface-elevated rounded-xl space-y-1">
                  {orderDetail.items.map((it: any, iIdx: number) => (
                    <div key={iIdx} className="flex justify-between items-center text-slate-300">
                      <span>• {it.name} (x{it.qty})</span>
                      <span>{formatVND(it.qty * it.unit_price)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Timeline of Order Events */}
            <div className="space-y-1 text-xs">
              <span className="font-bold text-slate-300 block">Dòng thời gian sự kiện:</span>
              <div className="p-2.5 bg-surface-elevated rounded-xl space-y-2 max-h-36 overflow-y-auto">
                {orderDetail.events?.map((ev: any, evIdx: number) => (
                  <div key={evIdx} className="text-[11px] border-b border-surface-border/50 pb-1.5 last:border-none">
                    <div className="flex justify-between text-slate-400">
                      <span className="font-mono text-brand-300">
                        {ev.from_status ? `${ev.from_status} → ` : ""}{ev.to_status}
                      </span>
                      <span>{formatDate(ev.created_at)}</span>
                    </div>
                    {ev.note && <p className="text-slate-300 mt-0.5">{ev.note}</p>}
                  </div>
                ))}
              </div>
            </div>

            {/* Intervention Action Buttons (FR-ADM-03) */}
            <div className="space-y-2 pt-2 border-t border-surface-border">
              <span className="text-xs font-bold text-white block">Hành động can thiệp Quản trị:</span>

              <div className="grid grid-cols-2 gap-2">
                <Button
                  variant="secondary"
                  size="default"
                  className="min-h-[40px] text-xs"
                  onClick={() => setActiveIntervention("transition")}
                >
                  <Edit3 className="w-3.5 h-3.5 mr-1" />
                  <span>Đổi Trạng Thái</span>
                </Button>

                <Button
                  variant="secondary"
                  size="default"
                  className="min-h-[40px] text-xs text-brand-400"
                  onClick={() => setActiveIntervention("reassign")}
                >
                  <UserCheck className="w-3.5 h-3.5 mr-1" />
                  <span>Gán Lại Thợ</span>
                </Button>

                <Button
                  variant="secondary"
                  size="default"
                  className="min-h-[40px] text-xs text-red-400"
                  onClick={() => setActiveIntervention("cancel")}
                >
                  <XCircle className="w-3.5 h-3.5 mr-1" />
                  <span>Hủy Đơn Hàng</span>
                </Button>

                <Button
                  variant="secondary"
                  size="default"
                  className="min-h-[40px] text-xs"
                  onClick={() => setActiveIntervention("note")}
                >
                  <FileText className="w-3.5 h-3.5 mr-1" />
                  <span>Ghi Chú Admin</span>
                </Button>
              </div>
            </div>

            {/* Inline Intervention Form */}
            {activeIntervention && (
              <form onSubmit={handleInterventionSubmit} className="p-3 bg-surface-elevated rounded-xl space-y-3 border border-brand-500/30">
                <h4 className="text-xs font-bold text-brand-400">
                  {activeIntervention === "transition"
                    ? "Chuyển Trạng Thái (State Machine)"
                    : activeIntervention === "reassign"
                    ? "Điều Phối Lại Cho Thợ Khác"
                    : activeIntervention === "cancel"
                    ? "Hủy Đơn Hàng Này"
                    : "Thêm Ghi Chú Nội Bộ"}
                </h4>

                {activeIntervention === "transition" && (
                  <div className="space-y-1">
                    <label className="text-[11px] text-slate-300 block">Trạng thái mục tiêu</label>
                    <select
                      value={targetStatus}
                      onChange={(e) => setTargetStatus(e.target.value)}
                      className="w-full bg-surface-card border border-surface-border rounded-xl p-2.5 text-xs text-white"
                    >
                      {ORDER_STATUSES.filter((s) => s !== "ALL").map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>
                )}

                {activeIntervention === "reassign" && (
                  <Input
                    label="User ID của Thợ mới *"
                    value={targetTechId}
                    onChange={(e) => setTargetTechId(e.target.value)}
                    placeholder="Nhập UUID của đối tác thợ..."
                    required
                  />
                )}

                <Input
                  label="Lý do / Nội dung can thiệp *"
                  value={interventionReason}
                  onChange={(e) => setInterventionReason(e.target.value)}
                  placeholder="Nhập giải trình can thiệp..."
                  required
                />

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    size="default"
                    className="flex-1"
                    onClick={() => setActiveIntervention(null)}
                  >
                    Hủy
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    size="default"
                    className="flex-1 font-bold"
                    isLoading={isSubmitting}
                  >
                    Xác Nhận Can Thiệp
                  </Button>
                </div>
              </form>
            )}
          </div>
        )}
      </BottomSheet>
    </div>
  );
}

