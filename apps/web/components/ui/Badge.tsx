import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "brand" | "emergency" | "success" | "warning" | "neutral";
}

export function Badge({
  className,
  variant = "neutral",
  children,
  ...props
}: BadgeProps) {
  const variants = {
    brand: "bg-brand-500/20 text-brand-300 border-brand-500/40",
    emergency: "bg-emergency-500/20 text-emergency-300 border-emergency-500/40",
    success: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
    warning: "bg-amber-500/20 text-amber-300 border-amber-500/40",
    neutral: "bg-slate-700/50 text-slate-300 border-slate-600/50",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border tracking-wide",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
}
