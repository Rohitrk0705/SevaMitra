"use client";

import React from "react";
import { Clock, Hourglass, Zap } from "lucide-react";
import { Progress } from "@/components/ui/progress";

interface MonitorTimerWidgetProps {
  secondsRemaining: number | null;
}

export function MonitorTimerWidget({ secondsRemaining }: MonitorTimerWidgetProps) {
  if (secondsRemaining === null) return null;

  const totalSeconds = 60;
  const elapsed = Math.max(0, totalSeconds - secondsRemaining);
  const progressPercent = Math.min(100, Math.max(0, (elapsed / totalSeconds) * 100));

  const isComplete = secondsRemaining === 0;

  return (
    <div
      className={`w-full rounded-xl border p-5 transition-all duration-500 shadow-2xl relative overflow-hidden ${
        isComplete
          ? "border-emerald-500/50 bg-gradient-to-r from-slate-950 via-emerald-950/30 to-slate-950 shadow-emerald-950/40"
          : "border-amber-500/60 bg-gradient-to-r from-slate-950 via-amber-950/40 to-slate-950 shadow-amber-950/50 animate-glow"
      }`}
    >
      {/* Background Glow Effect */}
      <div className="absolute -right-16 -top-16 w-48 h-48 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -left-16 -bottom-16 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Left narrative & context */}
        <div className="space-y-2 text-center md:text-left">
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-mono font-medium">
            <Hourglass className="h-3.5 w-3.5 animate-spin" />
            TIME-DILATION SIMULATION ACTIVE
          </div>

          <h3 className="text-lg sm:text-xl font-bold tracking-tight text-white flex items-center justify-center md:justify-start gap-2">
            <span>Autonomous Statutory SLA Audit</span>
            <Zap className="h-4 w-4 text-amber-400 fill-amber-400" />
          </h3>

          <p className="text-sm font-semibold text-amber-200/90 max-w-xl">
            &ldquo;In production this waits 8 months. Right now, 60 seconds.&rdquo;
          </p>

          <p className="text-xs text-slate-400 max-w-xl leading-relaxed">
            SevaMithra continuously monitors official state government e-portals across the 30-day Citizen&apos;s Charter SLA window. When departments miss their statutory deadlines, automated legal escalations trigger instantly.
          </p>
        </div>

        {/* Right large visual countdown ticker */}
        <div className="flex flex-col items-center justify-center bg-slate-900/90 border border-amber-500/30 rounded-2xl p-4 sm:p-5 min-w-[200px] shadow-inner text-center shrink-0">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1">
            <Clock className="h-3 w-3 text-amber-400" />
            Audit Countdown
          </div>

          <div className="flex items-baseline justify-center gap-1">
            <span
              className={`text-4xl sm:text-5xl font-black font-mono tracking-tight tabular-nums ${
                isComplete
                  ? "text-emerald-400"
                  : secondsRemaining <= 10
                  ? "text-rose-400 animate-pulse"
                  : "text-amber-400"
              }`}
            >
              {String(secondsRemaining).padStart(2, "0")}
            </span>
            <span className="text-xs font-mono text-slate-400">sec</span>
          </div>

          <div className="w-full mt-3 space-y-1">
            <Progress
              value={progressPercent}
              className="h-2 bg-slate-800"
              indicatorClassName={
                isComplete
                  ? "bg-emerald-500"
                  : secondsRemaining <= 10
                  ? "bg-rose-500"
                  : "bg-amber-500"
              }
            />
            <div className="flex justify-between text-[10px] font-mono text-slate-500">
              <span>Day 0</span>
              <span>Day 240 (8 mo)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
