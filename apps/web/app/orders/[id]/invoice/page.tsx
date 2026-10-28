"use client";

/**
 * Invoice View – FR-PAY-01
 * Detailed breakdown of labor, parts, surcharge, total, warranty.
 */

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Receipt,
  Hammer,
  Package,
  Moon,
  ShieldCheck,
  Loader2,
  AlertCircle,
  Printer,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { ordersApi, InvoiceResponse } from "@/lib/api";

function formatVnd(amount: number) {
  return amount.toLocaleString("vi-VN") + "đ";
}

function formatDate(iso: string) {
  const d = new Date(iso);
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  return `${dd}/${mm}/${yyyy}`;
}

export default function InvoicePage() {
  const params = useParams();
  const router = useRouter();
  const orderId = params?.id as string;
  const { showToast } = useToast();

  const [invoice, setInvoice] = React.useState<InvoiceResponse | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

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

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <Loader2 className="w-8 h-8 animate-spin text-brand-primary" />
      </div>
    );
  }

  if (!invoice) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 gap-3 text-center">
        <AlertCircle className="w-10 h-10 text-slate-500" />
        <p className="text-slate-400 text-sm">Không tải được hóa đơn. Vui lòng thử lại.</p>
        <Button variant="secondary" size="sm" onClick={() => router.back()}>
          Quay lại
        </Button>
      </div>
    );
  }

  const laborItems = invoice.items.filter((i) => i.item_type === "labor");
  const partItems = invoice.items.filter((i) => i.item_type === "part");
  const today = formatDate(new Date().toISOString());

  return (
    <div className="flex-1 flex flex-col p-4 pb-12 max-w-lg mx-auto w-full space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
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
            <h1 className="text-xl font-black text-white">Hóa Đơn</h1>
            <p className="text-xs text-slate-400">Ngày {today}</p>
          </div>
        </div>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => window.print()}
          className="gap-1.5"
        >
          <Printer className="w-4 h-4" />
          <span className="text-xs">In</span>
        </Button>
      </div>

      {/* Order ref */}
      <div className="p-4 bg-surface-card border border-surface-border rounded-2xl">
        <div className="flex items-center gap-2 mb-2">
          <Receipt className="w-5 h-5 text-brand-primary" />
          <h2 className="font-bold text-white">Fix 24/7 – Hóa Đơn Dịch Vụ</h2>
        </div>
        <p className="text-xs text-slate-500 font-mono">Mã đơn: {orderId}</p>
      </div>

      {/* Labor items */}
      {laborItems.length > 0 && (
        <div className="p-4 bg-surface-card border border-surface-border rounded-2xl space-y-3">
          <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
            <Hammer className="w-4 h-4 text-sky-400" />
            Công Lao Động
          </h3>
          <div className="space-y-2">
            {laborItems.map((item, i) => (
              <div key={i} className="flex justify-between text-sm">
                <div className="flex-1 pr-2">
                  <p className="text-slate-200">{item.name}</p>
                  {item.qty > 1 && (
                    <p className="text-xs text-slate-500">
                      {item.qty} x {formatVnd(item.unit_price)}
                    </p>
                  )}
                </div>
                <span className="text-white font-semibold whitespace-nowrap">
                  {formatVnd(item.line_total)}
                </span>
              </div>
            ))}
          </div>
          <div className="border-t border-surface-border pt-2 flex justify-between text-sm">
            <span className="text-slate-400">Tổng công</span>
            <span className="text-white font-semibold">{formatVnd(invoice.labor_subtotal)}</span>
          </div>
        </div>
      )}

      {/* Part items */}
      {partItems.length > 0 && (
        <div className="p-4 bg-surface-card border border-surface-border rounded-2xl space-y-3">
          <h3 className="font-semibold text-white flex items-center gap-2 text-sm">
            <Package className="w-4 h-4 text-violet-400" />
            Phụ Tùng & Vật Tư
          </h3>
          <div className="space-y-2">
            {partItems.map((item, i) => (
              <div key={i} className="flex justify-between text-sm">
                <div className="flex-1 pr-2">
                  <p className="text-slate-200">{item.name}</p>
                  {item.qty > 1 && (
                    <p className="text-xs text-slate-500">
                      {item.qty} x {formatVnd(item.unit_price)}
                    </p>
                  )}
                </div>
                <span className="text-white font-semibold whitespace-nowrap">
                  {formatVnd(item.line_total)}
                </span>
              </div>
            ))}
          </div>
          <div className="border-t border-surface-border pt-2 flex justify-between text-sm">
            <span className="text-slate-400">Tổng phụ tùng</span>
            <span className="text-white font-semibold">{formatVnd(invoice.parts_subtotal)}</span>
          </div>
        </div>
      )}

      {/* Night surcharge */}
      {invoice.night_surcharge > 0 && (
        <div className="p-4 bg-amber-950/40 border border-amber-500/30 rounded-2xl flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Moon className="w-4 h-4 text-amber-400" />
            <div>
              <p className="text-amber-300 text-sm font-semibold">Phụ Thu Giờ Đêm (BR-04)</p>
              <p className="text-amber-500 text-xs">22:00 – 06:00</p>
            </div>
          </div>
          <span className="text-amber-300 font-bold">+{formatVnd(invoice.night_surcharge)}</span>
        </div>
      )}

      {/* Grand total */}
      <div className="p-5 bg-gradient-to-br from-emerald-950/70 via-surface-card to-surface-card border-2 border-emerald-500/50 rounded-2xl">
        <div className="flex justify-between items-center">
          <span className="text-white font-bold text-base">TỔNG CỘNG</span>
          <span className="text-emerald-400 font-black text-3xl">{formatVnd(invoice.total)}</span>
        </div>
        <p className="text-xs text-slate-500 mt-1 text-right">Đã bao gồm tất cả chi phí</p>
      </div>

      {/* Warranty note */}
      <div className="p-4 bg-surface-card border border-surface-border rounded-2xl flex items-center gap-3">
        <ShieldCheck className="w-8 h-8 text-emerald-400 flex-shrink-0" />
        <div>
          <p className="text-white text-sm font-semibold">Bảo Hành {invoice.warranty_days} Ngày</p>
          <p className="text-xs text-slate-400">
            Dịch vụ được bảo hành {invoice.warranty_days} ngày từ ngày hoàn thành. Liên hệ ngay
            nếu có vấn đề.
          </p>
        </div>
      </div>

      {/* Actions */}
      <Button
        variant="secondary"
        size="lg"
        className="w-full"
        onClick={() => router.back()}
      >
        Đóng
      </Button>
    </div>
  );
}

