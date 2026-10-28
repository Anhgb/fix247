"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Clock,
  DollarSign,
  MapPin,
  Receipt,
  Star,
  User,
  Wallet,
  Wrench,
  Sparkles,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { useToast } from "@/components/ui/Toast";
import { techApi, TechOrderHistoryResponse, TechOrderHistoryItem } from "@/lib/api";

export default function TechnicianHistoryPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [history, setHistory] = React.useState<TechOrderHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  const loadHistory = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await techApi.getHistory();
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setHistory(data);
    }
  }, [showToast]);

  React.useEffect(() => {
    loadHistory();
  }, [loadHistory]);

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return "--";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("vi-VN", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
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
              <span>Lịch Sử Nhận Đơn</span>
              <Sparkles className="w-4 h-4 text-brand-400" />
            </h1>
            <p className="text-xs text-slate-400">Danh sách các ca cứu hộ & sửa chữa hoàn tất</p>
          </div>
        </div>

        <Button
          variant="secondary"
          size="default"
          className="min-h-[44px] text-xs font-semibold text-emerald-400 border-emerald-500/40"
          onClick={() => router.push("/tech/wallet")}
        >
          <Wallet className="w-3.5 h-3.5 mr-1" />
          <span>Ví Thợ</span>
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-3">
        <Card className="bg-gradient-to-br from-emerald-950/60 to-surface-card border-emerald-500/30">
          <CardContent className="p-4 space-y-1 text-center">
            <span className="text-xs text-emerald-300 font-semibold block">Tổng thực nhận</span>
            <strong className="text-lg font-black text-white">
              {formatVND(history?.total_earnings || 0)}
            </strong>
            <span className="text-[10px] text-slate-400 block">(Đã trừ hoa hồng nền tảng)</span>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-brand-950/60 to-surface-card border-brand-500/30">
          <CardContent className="p-4 space-y-1 text-center">
            <span className="text-xs text-brand-300 font-semibold block">Đơn hoàn thành</span>
            <strong className="text-lg font-black text-white">
              {history?.total || 0} ca
            </strong>
            <span className="text-[10px] text-slate-400 block">Tỷ lệ hoàn tất 100%</span>
          </CardContent>
        </Card>
      </div>

      {/* Orders List */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
          <Wrench className="w-4 h-4 text-brand-primary" />
          <span>Chi Tiết Từng Ca Sửa Chữa</span>
        </h3>

        {isLoading ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-10 h-10 border-4 border-brand-primary border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-slate-400">Đang tải lịch sử công việc...</p>
          </div>
        ) : !history || history.items.length === 0 ? (
          <div className="p-8 text-center bg-surface-card border border-surface-border rounded-2xl space-y-3">
            <CheckCircle2 className="w-10 h-10 text-slate-500 mx-auto" />
            <h4 className="text-base font-bold text-white">Chưa Có Đơn Nào Hoàn Tất</h4>
            <p className="text-xs text-slate-400 max-w-xs mx-auto">
              Bật trực tuyến trên bàn điều phối để bắt đầu nhận các đơn cứu hộ xe máy và sửa điện máy
              gần bạn.
            </p>
            <Button
              variant="primary"
              size="default"
              onClick={() => router.push("/tech/dashboard")}
            >
              Về Bàn Điều Phối
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {history.items.map((item) => (
              <Card key={item.order_id} className="bg-surface-card border-surface-border">
                <CardContent className="p-4 space-y-3">
                  {/* Top: Code & Date */}
                  <div className="flex items-center justify-between border-b border-surface-border/70 pb-2">
                    <span className="text-xs font-mono font-bold text-brand-primary">
                      #{item.code}
                    </span>
                    <span className="text-[11px] text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatDate(item.completed_at)}
                    </span>
                  </div>

                  {/* Service info */}
                  <div className="space-y-1">
                    <h4 className="font-bold text-white text-sm">{item.service_name}</h4>
                    <p className="text-xs text-slate-400 flex items-center gap-1">
                      <MapPin className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      <span className="truncate">{item.address}</span>
                    </p>
                    <p className="text-xs text-slate-400 flex items-center gap-1">
                      <User className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      <span>Khách hàng: {item.customer_name}</span>
                    </p>
                  </div>

                  {/* Financials: Bill vs Earnings */}
                  <div className="grid grid-cols-2 gap-2 p-2.5 bg-surface-elevated/70 rounded-xl border border-surface-border/50 text-xs">
                    <div>
                      <span className="text-[11px] text-slate-400 block">Tổng hóa đơn:</span>
                      <strong className="text-slate-200">{formatVND(item.total_amount)}</strong>
                    </div>
                    <div className="text-right">
                      <span className="text-[11px] text-emerald-400 font-semibold block">
                        Thực nhận về ví:
                      </span>
                      <strong className="text-emerald-300 font-bold">
                        +{formatVND(item.tech_earnings)}
                      </strong>
                    </div>
                  </div>

                  {/* Customer Review if any */}
                  {item.customer_rating && (
                    <div className="p-2.5 bg-amber-950/30 border border-amber-500/30 rounded-xl space-y-1">
                      <div className="flex items-center gap-1">
                        <span className="text-xs text-slate-400">Khách đánh giá:</span>
                        <div className="flex items-center">
                          {Array.from({ length: 5 }).map((_, i) => (
                            <Star
                              key={i}
                              className={`w-3.5 h-3.5 ${
                                i < item.customer_rating!
                                  ? "text-amber-400 fill-amber-400"
                                  : "text-slate-600"
                              }`}
                            />
                          ))}
                        </div>
                        <span className="text-xs font-bold text-amber-300 ml-1">
                          {item.customer_rating}.0
                        </span>
                      </div>
                      {item.customer_comment && (
                        <p className="text-xs text-slate-300 italic">
                          &ldquo;{item.customer_comment}&rdquo;
                        </p>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="pt-2 border-t border-surface-border flex items-center justify-end gap-2">
                    <Link
                      href={`/orders/${item.order_id}/invoice`}
                      className="inline-flex items-center gap-1 text-xs text-slate-300 hover:text-white font-medium p-1"
                    >
                      <Receipt className="w-3.5 h-3.5 text-brand-primary" />
                      <span>Xem hóa đơn</span>
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

