"use client";

import * as React from "react";
import { AlertTriangle, CheckCircle2, XCircle, Info } from "lucide-react";
import { Button } from "@/components/ui/Button";

export interface QuoteItemData {
  id?: string;
  item_type: "labor" | "part";
  name: string;
  qty: number;
  unit_price: number;
  photo_url?: string | null;
}

interface QuoteSheetProps {
  items: QuoteItemData[];
  finalQuote: number;
  estMax?: number | null;
  surcharge?: number;
  quoteReason?: string | null;
  isLoading?: boolean;
  onAccept: () => Promise<void>;
  onReject: () => Promise<void>;
}

export function QuoteSheet({
  items,
  finalQuote,
  estMax,
  surcharge = 0,
  quoteReason,
  isLoading = false,
  onAccept,
  onReject,
}: QuoteSheetProps) {
  const isOverThreshold = estMax && estMax > 0 && finalQuote > estMax * 1.2;
  const totalAmount = finalQuote + surcharge;

  return (
    <div className="p-5 bg-gradient-to-b from-surface-card to-surface-elevated border-2 border-brand-500/50 rounded-3xl shadow-2xl space-y-4">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-surface-border pb-3">
        <div>
          <h3 className="text-lg font-black text-white">Báo Giá Sửa Chữa</h3>
          <p className="text-xs text-slate-400">Thợ đã hoàn tất khảo sát thực tế</p>
        </div>
        <div className="text-right">
          <span className="text-xl font-black text-brand-400">
            {totalAmount.toLocaleString("vi-VN")} đ
          </span>
          <span className="text-[10px] text-slate-400 block">Tổng chi phí</span>
        </div>
      </div>

      {/* Warning if exceeds 20% */}
      {isOverThreshold && (
        <div className="p-3 bg-amber-950/60 border border-amber-500/50 rounded-2xl flex items-start gap-2.5 text-amber-300">
          <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
          <div className="text-xs space-y-1">
            <p className="font-bold">Báo giá vượt 20% so với giá tham khảo (BR-05)</p>
            {quoteReason && (
              <p className="text-slate-300 italic">
                Lý do từ thợ: &ldquo;{quoteReason}&rdquo;
              </p>
            )}
          </div>
        </div>
      )}

      {/* Items list */}
      <div className="space-y-2 max-h-48 overflow-y-auto">
        {items.map((it, idx) => (
          <div
            key={idx}
            className="p-2.5 bg-surface-card border border-surface-border rounded-xl flex items-center justify-between text-xs"
          >
            <div>
              <span className="font-semibold text-white block">{it.name}</span>
              <span className="text-slate-400">
                {it.item_type === "labor" ? "Tiền công" : "Linh kiện"} × {it.qty}
              </span>
            </div>
            <span className="font-bold text-slate-200">
              {(it.qty * it.unit_price).toLocaleString("vi-VN")} đ
            </span>
          </div>
        ))}

        {surcharge > 0 && (
          <div className="p-2.5 bg-surface-card border border-surface-border rounded-xl flex items-center justify-between text-xs">
            <span className="text-slate-300">Phụ thu đêm (22:00 - 05:00)</span>
            <span className="font-bold text-amber-400">
              +{surcharge.toLocaleString("vi-VN")} đ
            </span>
          </div>
        )}
      </div>

      {/* Notice on survey fee */}
      <div className="p-2.5 bg-surface-card/60 rounded-xl flex items-start gap-2 text-[11px] text-slate-400">
        <Info className="w-4 h-4 text-brand-400 shrink-0 mt-0.5" />
        <p>
          Nếu bạn từ chối báo giá, đơn sẽ đóng và bạn cần thanh toán{" "}
          <strong className="text-white">phí khảo sát 30.000đ</strong> cho thợ
          (Quy tắc BR-07).
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex gap-3 pt-1">
        <Button
          variant="secondary"
          className="w-1/2 min-h-[48px] text-red-400 hover:text-red-300 border-red-500/30"
          onClick={onReject}
          isLoading={isLoading}
        >
          <XCircle className="w-5 h-5 mr-1.5" />
          <span>Từ Chối</span>
        </Button>

        <Button
          variant="primary"
          className="w-1/2 min-h-[48px] font-bold text-base bg-emerald-600 hover:bg-emerald-500"
          onClick={onAccept}
          isLoading={isLoading}
        >
          <CheckCircle2 className="w-5 h-5 mr-1.5" />
          <span>Đồng Ý Sửa</span>
        </Button>
      </div>
    </div>
  );
}

