import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "emergency" | "secondary" | "outline" | "ghost";
  size?: "default" | "sm" | "lg" | "icon";
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "default",
      isLoading = false,
      children,
      disabled,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-semibold rounded-xl transition-all duration-200 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 disabled:opacity-50 disabled:pointer-events-none select-none";

    const variants = {
      primary:
        "bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-900/30",
      emergency:
        "bg-emergency-600 hover:bg-emergency-500 text-white shadow-lg shadow-emergency-900/40 animate-pulse-slow",
      secondary:
        "bg-surface-elevated hover:bg-slate-700 text-slate-100 border border-surface-border",
      outline:
        "border-2 border-brand-500 text-brand-400 hover:bg-brand-500/10",
      ghost: "text-slate-300 hover:text-white hover:bg-surface-elevated/50",
    };

    // Strict WCAG AA & Mobile-first: touch targets >= 48px
    const sizes = {
      default: "min-h-[48px] px-6 py-3 text-base",
      sm: "min-h-[40px] px-4 py-2 text-sm",
      lg: "min-h-[56px] px-8 py-4 text-lg",
      icon: "min-h-[48px] min-w-[48px] p-2",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <svg
              className="animate-spin -ml-1 mr-2 h-5 w-5 text-current"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8H4z"
              />
            </svg>
            <span>Đang xử lý...</span>
          </span>
        ) : (
          children
        )}
      </button>
    );
  }
);
Button.displayName = "Button";
