"use client";

import React from "react";
import { Layers, Activity, FolderSearch } from "lucide-react";
import { SchemeThreadState } from "@/lib/events";
import { SchemeCard } from "@/components/SchemeCard";
import { Badge } from "@/components/ui/badge";

interface SchemeThreadsPanelProps {
  schemes: SchemeThreadState[];
  onOpenRti: (scheme: SchemeThreadState) => void;
  isStreaming: boolean;
}

export function SchemeThreadsPanel({
  schemes,
  onOpenRti,
  isStreaming,
}: SchemeThreadsPanelProps) {
  const completedCount = schemes.filter((s) => s.phase === "completed").length;
  const escalatedCount = schemes.filter(
    (s) =>
      s.phase === "deadline_crossed" ||
      s.phase === "escalation_drafted" ||
      s.phase === "rti_drafted"
  ).length;

  return (
    <div className="flex flex-col h-full space-y-4">
      {/* Panel Title Bar */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-emerald-400" />
          <h2 className="text-sm font-semibold tracking-tight text-white uppercase">
            Active Scheme Threads
          </h2>
          <Badge variant="outline" className="text-[10px] font-mono px-1.5 py-0">
            {schemes.length}
          </Badge>
        </div>

        {schemes.length > 0 && (
          <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400">
            {completedCount > 0 && (
              <span className="text-emerald-400 font-medium">
                {completedCount} filed
              </span>
            )}
            {escalatedCount > 0 && (
              <span className="text-rose-400 font-medium">
                {escalatedCount} RTI drafted
              </span>
            )}
          </div>
        )}
      </div>

      {/* Scheme Cards List */}
      <div className="space-y-3.5 flex-1 overflow-y-auto pr-1">
        {schemes.length === 0 ? (
          <div className="h-[380px] rounded-xl border border-dashed border-slate-800 bg-slate-950/40 p-6 flex flex-col items-center justify-center text-center text-slate-500 space-y-3">
            <FolderSearch className="h-8 w-8 text-slate-700 animate-bounce" />
            <div className="space-y-1">
              <p className="text-xs text-slate-400 font-medium">
                No active scheme threads yet.
              </p>
              <p className="text-[11px] text-slate-600 max-w-[240px]">
                As the Discovery agent extracts candidate welfare schemes, dedicated lifecycle tracking threads will populate here.
              </p>
            </div>
            {isStreaming && (
              <div className="flex items-center gap-1.5 text-[11px] text-teal-400 font-mono">
                <Activity className="h-3.5 w-3.5 animate-spin" />
                Discovery agent indexing schemes...
              </div>
            )}
          </div>
        ) : (
          schemes.map((scheme) => (
            <SchemeCard
              key={scheme.scheme_id}
              scheme={scheme}
              onOpenRti={onOpenRti}
            />
          ))
        )}
      </div>
    </div>
  );
}
