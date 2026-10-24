"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { X } from "lucide-react";

export interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  className?: string;
}

export function BottomSheet({
  isOpen,
  onClose,
  title,
  children,
  className,
}: BottomSheetProps) {
  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/70 backdrop-blur-sm transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sheet Container */}
      <div
        className={cn(
          "relative z-50 w-full max-w-lg bg-surface-card border-t sm:border border-surface-border rounded-t-3xl sm:rounded-2xl p-5 shadow-2xl transition-transform max-h-[90vh] flex flex-col",
          className
        )}
      >
        {/* Grab Handle for Mobile */}
        <div className="mx-auto -mt-2 mb-3 h-1.5 w-12 rounded-full bg-slate-600 sm:hidden" />

        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-surface-border">
          {title ? (
            <h2 className="text-lg font-bold text-white leading-none">{title}</h2>
          ) : <div />}
          <button
            onClick={onClose}
            className="min-h-[44px] min-w-[44px] p-2 text-slate-400 hover:text-white rounded-lg flex items-center justify-center focus:outline-none"
            aria-label="Đóng"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="overflow-y-auto pt-4 flex-1">{children}</div>
      </div>
    </div>
  );
}
