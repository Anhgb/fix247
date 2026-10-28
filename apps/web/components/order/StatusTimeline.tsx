"use client";

import * as React from "react";
import {
  Clock,
  Search,
  CheckCircle2,
  Navigation,
  FileSearch,
  Receipt,
  Wrench,
  ShieldCheck,
  XCircle,
  AlertTriangle,
} from "lucide-react";

export interface StatusTimelineProps {
  status: string;
}

const ORDER_STEPS = [
  { key: "SEARCHING", label: "Tìm thợ", icon: Search },
  { key: "ACCEPTED", label: "Đã nhận", icon: CheckCircle2 },
  { key: "ON_THE_WAY", label: "Đang đến", icon: Navigation },
  { key: "SURVEYING", label: "Khảo sát", icon: FileSearch },
  { key: "QUOTE_PENDING", label: "Báo giá", icon: Receipt },
  { key: "IN_REPAIR", label: "Đang sửa", icon: Wrench },
  { key: "COMPLETED", label: "Hoàn tất", icon: ShieldCheck },
];

export function StatusTimeline({ status }: StatusTimelineProps) {
  if (status === "CANCELLED") {
    return (
      <div className="p-4 bg-red-950/40 border border-red-500/50 rounded-2xl flex items-center gap-3 text-red-300">
        <XCircle className="w-6 h-6 text-red-400 shrink-0" />
        <div>
          <p className="font-bold text-sm">Đơn hàng đã hủy</p>
          <p className="text-xs text-red-300/80">Yêu cầu đã kết thúc.</p>
        </div>
      </div>
    );
  }

  if (status === "NO_TECH") {
    return (
      <div className="p-4 bg-amber-950/40 border border-amber-500/50 rounded-2xl flex items-center gap-3 text-amber-300">
        <AlertTriangle className="w-6 h-6 text-amber-400 shrink-0" />
        <div>
          <p className="font-bold text-sm">Chưa tìm thấy thợ phù hợp</p>
          <p className="text-xs text-amber-300/80">Bạn có thể thử tìm lại hoặc gọi Hotline cứu hộ.</p>
        </div>
      </div>
    );
  }

  if (status === "QUOTE_REJECTED" || status === "CLOSED") {
    return (
      <div className="p-4 bg-slate-800/60 border border-slate-700 rounded-2xl flex items-center gap-3 text-slate-300">
        <XCircle className="w-6 h-6 text-slate-400 shrink-0" />
        <div>
          <p className="font-bold text-sm">Đã từ chối báo giá</p>
          <p className="text-xs text-slate-400">Đơn hàng đã đóng sau bước khảo sát.</p>
        </div>
      </div>
    );
  }

  const currentIdx = ORDER_STEPS.findIndex((s) => s.key === status);
  const activeIndex = currentIdx === -1 ? (status === "CREATED" ? -1 : 0) : currentIdx;

  return (
    <div className="w-full py-2">
      <div className="flex items-center justify-between overflow-x-auto pb-2 scrollbar-none">
        {ORDER_STEPS.map((step, idx) => {
          const isDone = idx < activeIndex;
          const isCurrent = idx === activeIndex;
          const Icon = step.icon;

          return (
            <div key={step.key} className="flex flex-col items-center min-w-[56px] relative">
              <div
                className={`w-9 h-9 rounded-full flex items-center justify-center transition-all ${
                  isCurrent
                    ? "bg-brand-500 text-white shadow-lg shadow-brand-500/40 ring-4 ring-brand-500/20 animate-pulse"
                    : isDone
                    ? "bg-emerald-600 text-white"
                    : "bg-surface-elevated text-slate-500 border border-surface-border"
                }`}
              >
                <Icon className="w-4 h-4" />
              </div>
              <span
                className={`text-[11px] mt-1.5 text-center font-medium ${
                  isCurrent
                    ? "text-brand-400 font-bold"
                    : isDone
                    ? "text-slate-300"
                    : "text-slate-500"
                }`}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
