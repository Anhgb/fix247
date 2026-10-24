import * as React from "react";
import { cn } from "@/lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  interactive?: boolean;
}

export function Card({
  className,
  interactive = false,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "bg-surface-card border border-surface-border rounded-2xl p-4 sm:p-5 shadow-sm text-slate-100",
        interactive &&
          "cursor-pointer hover:border-brand-500/50 hover:bg-surface-elevated/40 transition-all duration-200 active:scale-[0.99]",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("mb-3 flex flex-col space-y-1.5", className)} {...props}>
      {children}
    </div>
  );
}

export function CardTitle({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn("text-lg font-bold leading-tight text-white", className)}
      {...props}
    >
      {children}
    </h3>
  );
}

export function CardDescription({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p className={cn("text-sm text-slate-400 leading-normal", className)} {...props}>
      {children}
    </p>
  );
}

export function CardContent({
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("pt-0", className)} {...props}>
      {children}
    </div>
  );
}
