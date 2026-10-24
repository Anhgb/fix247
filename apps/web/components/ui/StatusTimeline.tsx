import * as React from "react";
import { cn } from "@/lib/utils";
import { Check, Clock, Wrench, Navigation, CheckCircle2 } from "lucide-react";

export type TimelineStage =
  | "CREATED"
  | "DISPATCHING"
  | "ON_THE_WAY"
  | "IN_PROGRESS"
  | "COMPLETED";

export interface StatusTimelineProps {
  currentStage: TimelineStage;
  className?: string;
}

const STAGES: Array<{ key: TimelineStage; label: string; icon: React.ElementType }> = [
  { key: "CREATED", label: "Đã tiếp nhận", icon: Clock },
  { key: "DISPATCHING", label: "Tìm thợ", icon: Clock },
  { key: "ON_THE_WAY", label: "Thợ đang đến", icon: Navigation },
  { key: "IN_PROGRESS", label: "Đang sửa", icon: Wrench },
  { key: "COMPLETED", label: "Hoàn tất", icon: CheckCircle2 },
];

export function StatusTimeline({ currentStage, className }: StatusTimelineProps) {
  const currentIndex = STAGES.findIndex((s) => s.key === currentStage);

  return (
    <div className={cn("w-full py-4", className)}>
      <div className="relative flex items-center justify-between">
        {/* Track Line */}
        <div className="absolute top-1/2 left-4 right-4 -translate-y-1/2 h-1 bg-surface-elevated -z-0" />
        <div
          className="absolute top-1/2 left-4 -translate-y-1/2 h-1 bg-brand-500 transition-all duration-500 -z-0"
          style={{
            width: `${(Math.max(0, currentIndex) / (STAGES.length - 1)) * 92}%`,
          }}
        />

        {/* Step Nodes */}
        {STAGES.map((stage, idx) => {
          const isDone = idx < currentIndex;
          const isCurrent = idx === currentIndex;
          const Icon = stage.icon;

          return (
            <div
              key={stage.key}
              className="relative z-10 flex flex-col items-center group"
            >
              <div
                className={cn(
                  "w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300 border-2",
                  isDone && "bg-brand-600 border-brand-500 text-white shadow-md shadow-brand-900/50",
                  isCurrent && "bg-surface-card border-brand-500 text-brand-400 ring-4 ring-brand-500/20 animate-pulse",
                  !isDone && !isCurrent && "bg-surface-elevated border-surface-border text-slate-400"
                )}
              >
                {isDone ? <Check className="w-5 h-5 text-white" /> : <Icon className="w-5 h-5" />}
              </div>
              <span
                className={cn(
                  "mt-2 text-xs font-medium text-center whitespace-nowrap",
                  isCurrent ? "text-brand-400 font-bold" : isDone ? "text-slate-200" : "text-slate-500"
                )}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
