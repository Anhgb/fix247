"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Clock,
  MapPin,
  AlertOctagon,
  Calendar,
  ChevronRight,
  ArrowLeft,
  Wrench,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { apiRequest } from "@/lib/api";

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  CREATED: { label: "Đã tạo", color: "bg-slate-700 text-slate-300" },
  SEARCHING: { label: "Đang tìm thợ", color: "bg-amber-600/30 text-amber-300 border border-amber-500/40" },
  SCHEDULED: { label: "Đã đặt lịch", color: "bg-blue-600/30 text-blue-300 border border-blue-500/40" },
  ACCEPTED: { label: "Thợ đã nhận", color: "bg-emerald-600/30 text-emerald-300 border border-emerald-500/40" },
  ON_THE_WAY: { label: "Thợ đang đến", color: "bg-sky-600/30 text-sky-300 border border-sky-500/40" },
  SURVEYING: { label: "Đang khảo sát", color: "bg-indigo-600/30 text-indigo-300 border border-indigo-500/40" },
  QUOTE_PENDING: { label: "Chờ duyệt giá", color: "bg-yellow-600/30 text-yellow-300 border border-yellow-500/40" },
  IN_REPAIR: { label: "Đang sửa chữa", color: "bg-purple-600/30 text-purple-300 border border-purple-500/40" },
  AWAITING_CONFIRM: { label: "Chờ xác nhận", color: "bg-orange-600/30 text-orange-300 border border-orange-500/40" },
  COMPLETED: { label: "Hoàn tất", color: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/50" },
  CANCELLED: { label: "Đã hủy", color: "bg-red-950/60 text-red-400 border border-red-500/30" },
  NO_TECH: { label: "Không có thợ", color: "bg-amber-950/60 text-amber-400 border border-amber-500/30" },
  QUOTE_REJECTED: { label: "Từ chối báo giá", color: "bg-slate-800 text-slate-400" },
};

export default function OrdersListPage() {
  const router = useRouter();
  const [orders, setOrders] = React.useState<any[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);

  React.useEffect(() => {
    apiRequest<any>("/orders").then(({ data }) => {
      setIsLoading(false);
      if (data && data.items) {
        setOrders(data.items);
      }
    });
  }, []);

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 max-w-lg mx-auto w-full space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => router.push("/")}
          className="h-10 w-10 p-0 rounded-full"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-xl font-black text-white">Lịch Sử Đơn Hàng</h1>
          <p className="text-xs text-slate-400">Theo dõi tiến độ và lịch sử sửa chữa</p>
        </div>
      </div>

      {/* Orders List */}
      {isLoading ? (
        <div className="p-12 text-center text-sm text-slate-400 animate-pulse">
          Đang tải danh sách đơn hàng...
        </div>
      ) : orders.length === 0 ? (
        <div className="p-8 bg-surface-card border border-surface-border rounded-2xl text-center space-y-4">
          <Wrench className="w-12 h-12 text-slate-600 mx-auto" />
          <div>
            <h3 className="font-bold text-white text-base">Chưa có đơn hàng nào</h3>
            <p className="text-xs text-slate-400 mt-1">
              Bạn chưa tạo yêu cầu cứu hộ hoặc đặt lịch sửa chữa nào.
            </p>
          </div>
          <Button
            variant="primary"
            onClick={() => router.push("/")}
            className="w-full min-h-[48px]"
          >
            Đặt Thợ Ngay
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map((order) => {
            const statusConfig = STATUS_LABELS[order.status] || {
              label: order.status,
              color: "bg-slate-700 text-slate-300",
            };

            return (
              <Link
                key={order.id}
                href={`/orders/${order.id}`}
                className="block p-4 bg-surface-card hover:bg-surface-elevated border border-surface-border rounded-2xl transition shadow-md"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    {order.mode === "emergency" ? (
                      <span className="p-1.5 bg-emergency-950/70 text-emergency-400 rounded-lg">
                        <AlertOctagon className="w-4 h-4" />
                      </span>
                    ) : (
                      <span className="p-1.5 bg-brand-950/70 text-brand-400 rounded-lg">
                        <Calendar className="w-4 h-4" />
                      </span>
                    )}
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      {order.mode === "emergency" ? "Cứu hộ khẩn cấp" : "Hẹn lịch"}
                    </span>
                  </div>

                  <span
                    className={`text-[11px] font-semibold px-2.5 py-1 rounded-full ${statusConfig.color}`}
                  >
                    {statusConfig.label}
                  </span>
                </div>

                <div className="mt-3 space-y-1.5">
                  <p className="text-xs text-slate-300 flex items-center gap-1.5 truncate">
                    <MapPin className="w-3.5 h-3.5 text-brand-400 shrink-0" />
                    <span>{order.address}</span>
                  </p>

                  <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-surface-border/50">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" />
                      {new Date(order.created_at).toLocaleDateString("vi-VN", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>

                    {order.total && (
                      <span className="font-bold text-white">
                        {order.total.toLocaleString("vi-VN")} đ
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

