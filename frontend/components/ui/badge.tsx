import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-slate-800 text-slate-200 hover:bg-slate-700",
        destructive:
          "border-transparent bg-red-900/60 text-red-200 border-red-800 hover:bg-red-900/80",
        outline: "text-slate-300 border-slate-700",
        success: "border-emerald-500/30 bg-emerald-950/60 text-emerald-300",
        warning: "border-amber-500/30 bg-amber-950/60 text-amber-300",
        cyan: "border-cyan-500/30 bg-cyan-950/60 text-cyan-300",
        purple: "border-purple-500/30 bg-purple-950/60 text-purple-300",
        agent: "border-emerald-500/40 bg-emerald-950/40 text-emerald-400 font-mono text-[11px]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
