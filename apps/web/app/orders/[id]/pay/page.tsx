"use client";

/**
 * Payment Screen – FR-PAY-01, FR-PAY-02, FR-PAY-03
 * Shows invoice breakdown and lets customer choose cash or VietQR.
 */

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Receipt,
  QrCode,
  Banknote,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { ordersApi, InvoiceResponse, PaymentCreateResponse } from "@/lib/api";

function formatVnd(amount: number) {
  return amount.toLocaleString("vi-VN") + "đ";
}

export default function PaymentPage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params?.id as string;
  const { showToast } = useToast();

  const [invoice, setInvoice] = React.useState<InvoiceResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const [method, setMethod] = React.useState<"cash" | "vietqr">("cash");
  const [paying, setPaying] = React.useState(false);
  const [payment, setPayment] = React.useState<PaymentCreateResponse | null>(null);

  React.useEffect(() => {
    (async () => {
      const { data, error } = await ordersApi.getInvoice(orderId);
      if (error) {
        showToast(error.message, "error");
      } else if (data) {
        setInvoice(data);
      }
      setIsLoading(false);
    })();
  }, [orderId, showToast]);

  const handlePay = async () => {
    if (!invoice) return;
    setPaying(true);
    const { data, error } = await ordersApi.createPayment(orderId, method);
    setPaying(false);
    if (error) {
      showToast(error.message, "error");
      return;
    }
    setPayment(data!);
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <Loader2 className="w-8 h-8 animate-spin text-brand-primary" />
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-slate-400 text-sm text-center">
        <AlertCircle className="w-5 h-5 mr-2" />
        Không tải được hóa đơn. Vui lòng thử lại.
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 max-w-lg mx-auto w-full space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => router.back()}
          className="h-10 w-10 p-0 rounded-full"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div>
          <h1 className="text-xl font-black text-white">Thanh Toán</h1>
          <p className="text-xs text-slate-400 font-mono">#{orderId.slice(0, 8)}...</p>
        </div>
      </div>

      {/* Invoice breakdown */}
      <div className="p-5 bg-surface-card border border-surface-border rounded-2xl space-y-3">
        <h2 className="font-bold text-white flex items-center gap-2">
          <Receipt className="w-5 h-5 text-brand-primary" />
          Tóm Tắt Hóa Đơn
        </h2>

        {invoice.items.length > 0 && (
          <div className="space-y-1.5">
            {invoice.items.map((item, i) => (
              <div key={i} className="flex justify-between text-sm">
                <span className="text-slate-300 flex-1 pr-2">
                  {item.name}
                  {item.qty > 1 && (
                    <span className="text-slate-500 ml-1">x{item.qty}</span>
                  )}
                  <span className="ml-1 text-xs text-slate-500">
                    ({item.item_type === "labor" ? "Công" : "Phụ tùng"})
                  </span>
                </span>
                <span className="text-white font-medium whitespace-nowrap">
                  {formatVnd(item.line_total)}
                </span>
              </div>
            ))}
          </div>
        )}

        <div className="border-t border-surface-border pt-2 space-y-1.5">
          <div className="flex justify-between text-sm text-slate-400">
            <span>Tiền công</span>
            <span>{formatVnd(invoice.labor_subtotal)}</span>
          </div>
          <div className="flex justify-between text-sm text-slate-400">
            <span>Phụ tùng</span>
            <span>{formatVnd(invoice.parts_subtotal)}</span>
          </div>
          {invoice.night_surcharge > 0 && (
            <div className="flex justify-between text-sm text-amber-400">
              <span>Phụ thu đêm (BR-04)</span>
              <span>+{formatVnd(invoice.night_surcharge)}</span>
            </div>
          )}
        </div>

        <div className="border-t border-surface-border pt-2 flex justify-between items-center">
          <span className="font-bold text-white text-base">Tổng Cộng</span>
          <span className="font-black text-emerald-400 text-2xl">
            {formatVnd(invoice.total)}
          </span>
        </div>

        <p className="text-xs text-slate-500 text-center">
          Bảo hành {invoice.warranty_days} ngày kể từ ngày hoàn thành
        </p>
      </div>

      {/* Payment method selector */}
      {!payment && (
        <>
          <div className="space-y-2">
            <h2 className="font-bold text-white text-sm">Phương Thức Thanh Toán</h2>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setMethod("cash")}
                className={`p-4 rounded-2xl border-2 flex flex-col items-center gap-2 transition-all min-h-[80px] ${
                  method === "cash"
                    ? "border-brand-primary bg-brand-primary/10 text-white"
                    : "border-surface-border bg-surface-card text-slate-400"
                }`}
              >
                <Banknote className="w-6 h-6" />
                <span className="text-sm font-semibold">Tiền mặt</span>
              </button>

              <button
                type="button"
                onClick={() => setMethod("vietqr")}
                className={`p-4 rounded-2xl border-2 flex flex-col items-center gap-2 transition-all min-h-[80px] ${
                  method === "vietqr"
                    ? "border-brand-primary bg-brand-primary/10 text-white"
                    : "border-surface-border bg-surface-card text-slate-400"
                }`}
              >
                <QrCode className="w-6 h-6" />
                <span className="text-sm font-semibold">VietQR</span>
              </button>
            </div>
          </div>

          <Button
            variant="primary"
            size="lg"
            className="w-full min-h-[52px] font-bold"
            onClick={handlePay}
            isLoading={paying}
          >
            {method === "cash" ? "Xác Nhận Thanh Toán Tiền Mặt" : "Tạo Mã QR Thanh Toán"}
          </Button>
        </>
      )}

      {/* Payment result */}
      {payment && (
        <div className="p-5 bg-surface-card border border-emerald-500/40 rounded-2xl space-y-4">
          {payment.method === "vietqr" && payment.qr_url ? (
            <div className="space-y-3 text-center">
              <h3 className="font-bold text-white">Quét Mã QR Để Thanh Toán</h3>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={payment.qr_url}
                alt="VietQR"
                className="mx-auto w-48 h-48 rounded-xl bg-white p-1"
              />
              <p className="text-xs text-slate-400">
                Số tiền: <strong className="text-white">{formatVnd(payment.amount)}</strong>
              </p>
              <p className="text-xs text-slate-500">
                Mã giao dịch: <span className="font-mono">{payment.payment_id.slice(0, 8)}</span>
              </p>
              <p className="text-sm text-slate-300">
                Sau khi quét mã, giao dịch sẽ được xác nhận tự động.
              </p>
            </div>
          ) : (
            <div className="text-center space-y-3">
              <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
              <h3 className="font-bold text-white">Thanh Toán Tiền Mặt Đã Ghi Nhận</h3>
              <p className="text-sm text-slate-300">
                Vui lòng thanh toán <strong className="text-emerald-400">{formatVnd(payment.amount)}</strong> cho
                thợ và chờ xác nhận.
              </p>
            </div>
          )}

          <Button
            variant="secondary"
            size="lg"
            className="w-full"
            onClick={() => router.push(`/orders/${orderId}`)}
          >
            Quay Về Đơn Hàng
          </Button>
        </div>
      )}
    </div>
  );
}

