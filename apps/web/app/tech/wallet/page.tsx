"use client";

/**
 * Technician Wallet & Commission Settlement – BR-09, FR-PAY-04, FR-PAY-05
 * Displays total earned, commission debt, blocking status, and settlement actions.
 */

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Wallet,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  DollarSign,
  ShieldAlert,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/components/ui/Toast";
import { techApi, WalletInfoResponse } from "@/lib/api";

function formatVnd(amount: number) {
  return amount.toLocaleString("vi-VN") + " đ";
}

export default function TechnicianWalletPage() {
  const router = useRouter();
  const { showToast } = useToast();

  const [wallet, setWallet] = React.useState<WalletInfoResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isSettling, setIsSettling] = React.useState(false);
  const [customAmount, setCustomAmount] = React.useState<string>("");

  const fetchWallet = React.useCallback(async () => {
    setIsLoading(true);
    const { data, error } = await techApi.getWallet();
    setIsLoading(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    if (data) {
      setWallet(data);
      if (data.debt_amount > 0) {
        setCustomAmount(data.debt_amount.toString());
      }
    }
  }, [showToast]);

  React.useEffect(() => {
    fetchWallet();
  }, [fetchWallet]);

  const handleSettle = async (amount: number) => {
    if (amount <= 0) {
      showToast("Vui lòng nhập số tiền thanh toán hợp lệ.", "error");
      return;
    }

    setIsSettling(true);
    const { error } = await techApi.settleDebt(amount);
    setIsSettling(false);

    if (error) {
      showToast(error.message, "error");
      return;
    }

    showToast(`Đã thanh toán đối soát ${formatVnd(amount)} thành công!`, "success");
    fetchWallet();
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <Loader2 className="w-8 h-8 animate-spin text-brand-primary" />
      </div>
    );
  }

  const debtAmount = wallet?.debt_amount ?? 0;
  const isBlocked = wallet?.is_blocked ?? false;

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 max-w-lg mx-auto w-full space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => router.push("/tech/dashboard")}
            className="h-10 w-10 p-0 rounded-full"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="text-xl font-black text-white">Ví & Đối Soát Thợ</h1>
            <p className="text-xs text-slate-400">Quản lý thu nhập & hoa hồng (BR-09)</p>
          </div>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={fetchWallet}
          className="h-10 w-10 p-0 rounded-full"
        >
          <RefreshCw className="w-4 h-4 text-slate-300" />
        </Button>
      </div>

      {/* Blocked or Warning Banner */}
      {isBlocked ? (
        <div className="p-4 bg-red-950/60 border-2 border-red-500 rounded-2xl flex items-start gap-3 shadow-lg">
          <ShieldAlert className="w-6 h-6 text-red-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <p className="font-black text-red-200 text-sm">TÀI KHOẢN BỊ KHÓA NHẬN ĐƠN (BR-09)</p>
            <p className="text-red-300/90 leading-relaxed">
              Bạn đang nợ hoa hồng vượt hạn mức 500.000đ hoặc quá hạn 7 ngày chưa thanh toán. Vui lòng nộp đối soát ngay bên dưới để mở lại quyền nhận đơn.
            </p>
          </div>
        </div>
      ) : debtAmount >= 400000 ? (
        <div className="p-4 bg-amber-950/60 border border-amber-500/50 rounded-2xl flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs text-amber-200">
            <p className="font-bold text-amber-300 text-sm">Cảnh báo hạn mức nợ hoa hồng</p>
            <p>
              Nợ hoa hồng của bạn đang ở mức {formatVnd(debtAmount)}. Hãy thanh toán sớm trước khi vượt 500.000đ để tránh bị gián đoạn nhận đơn.
            </p>
          </div>
        </div>
      ) : null}

      {/* Main Stats Cards */}
      <div className="grid grid-cols-2 gap-3">
        {/* Total Earned */}
        <div className="p-4 bg-surface-card border border-surface-border rounded-2xl space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span>Tổng Thu Nhập</span>
          </div>
          <p className="text-xl font-black text-white">
            {formatVnd(wallet?.total_earned ?? 0)}
          </p>
          <p className="text-[10px] text-slate-500">Từ các đơn hoàn tất</p>
        </div>

        {/* Debt Amount */}
        <div
          className={`p-4 rounded-2xl space-y-1 border ${
            debtAmount > 0
              ? "bg-red-950/30 border-red-500/40"
              : "bg-surface-card border-surface-border"
          }`}
        >
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <DollarSign className="w-4 h-4 text-red-400" />
            <span>Nợ Hoa Hồng (10%)</span>
          </div>
          <p
            className={`text-xl font-black ${
              debtAmount > 0 ? "text-red-400" : "text-emerald-400"
            }`}
          >
            {formatVnd(debtAmount)}
          </p>
          <p className="text-[10px] text-slate-500">
            {wallet?.debt_overdue_at
              ? `Hạn chót: ${new Date(wallet.debt_overdue_at).toLocaleDateString("vi-VN")}`
              : "Chưa có nợ quá hạn"}
          </p>
        </div>
      </div>

      {/* Settle Debt Section */}
      <div className="p-5 bg-surface-card border border-surface-border rounded-2xl space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <Wallet className="w-5 h-5 text-brand-primary" />
          Nộp Tiền Đối Soát Hoa Hồng
        </h2>

        <p className="text-xs text-slate-400 leading-relaxed">
          Hoa hồng nền tảng là 10% trên tổng tiền công và linh kiện (miễn thu trên phụ phí đêm). Bạn có thể thanh toán một phần hoặc toàn bộ số dư nợ hiện tại.
        </p>

        <div className="space-y-2">
          <label className="text-xs font-semibold text-slate-300">
            Số tiền thanh toán (VND)
          </label>
          <Input
            type="number"
            value={customAmount}
            onChange={(e) => setCustomAmount(e.target.value)}
            placeholder="Ví dụ: 100000"
            className="text-base font-bold text-emerald-400"
            min={1000}
            step={1000}
          />
        </div>

        {/* Quick Amount Buttons */}
        {debtAmount > 0 && (
          <div className="flex gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setCustomAmount(debtAmount.toString())}
              className="text-xs font-semibold border-emerald-500/40 text-emerald-300"
            >
              Toàn bộ ({formatVnd(debtAmount)})
            </Button>
            {debtAmount > 100000 && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setCustomAmount("100000")}
                className="text-xs"
              >
                100.000 đ
              </Button>
            )}
            {debtAmount > 200000 && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setCustomAmount("200000")}
                className="text-xs"
              >
                200.000 đ
              </Button>
            )}
          </div>
        )}

        <Button
          variant="primary"
          size="lg"
          className="w-full min-h-[48px] font-bold bg-emerald-600 hover:bg-emerald-500 text-white"
          onClick={() => handleSettle(Number(customAmount))}
          isLoading={isSettling}
          disabled={!customAmount || Number(customAmount) <= 0}
        >
          <CheckCircle2 className="w-5 h-5 mr-2" />
          Xác Nhận Nộp Đối Soát
        </Button>
      </div>

      {/* Rules Explanations (BR-01, BR-09) */}
      <div className="p-4 bg-surface-elevated border border-surface-border rounded-xl space-y-2 text-xs text-slate-400">
        <h3 className="font-bold text-white text-xs">Quy chế đối soát & hoa hồng Fix 24/7 (BR-01, BR-09):</h3>
        <ul className="list-disc list-inside space-y-1 pl-1">
          <li>Tỷ lệ hoa hồng nền tảng: 10% (chỉ tính trên tiền công + linh kiện).</li>
          <li>100% phụ thu ban đêm (22h - 6h) thuộc về thợ kỹ thuật.</li>
          <li>Chu kỳ đối soát: Hàng tuần (thứ Hai hàng tuần).</li>
          <li>Khi nợ hoa hồng vượt 500.000đ hoặc quá hạn 7 ngày, hệ thống sẽ tạm dừng phân phối đơn mới cho đến khi được thanh toán.</li>
        </ul>
      </div>
    </div>
  );
}

