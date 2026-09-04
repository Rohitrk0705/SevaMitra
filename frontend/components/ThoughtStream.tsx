"use client";

import React, { useEffect, useRef, useState } from "react";
import { Terminal, PauseCircle, PlayCircle, ShieldCheck } from "lucide-react";
import { ReasoningStepEvent, AgentRole, ReasoningPhase } from "@/lib/events";
import { formatTime } from "@/lib/utils";

interface ThoughtStreamProps {
  events: ReasoningStepEvent[];
  isStreaming: boolean;
}

const AGENT_COLORS: Record<AgentRole, { text: string; bg: string; border: string }> = {
  orchestrator: {
    text: "text-emerald-400",
    bg: "bg-emerald-950/40",
    border: "border-emerald-700/50",
  },
  search: {
    text: "text-cyan-400",
    bg: "bg-cyan-950/40",
    border: "border-cyan-700/50",
  },
  validator: {
    text: "text-purple-400",
    bg: "bg-purple-950/40",
    border: "border-purple-700/50",
  },
  filler: {
    text: "text-teal-300",
    bg: "bg-teal-950/40",
    border: "border-teal-700/50",
  },
  monitor: {
    text: "text-amber-400",
    bg: "bg-amber-950/40",
    border: "border-amber-700/50",
  },
  escalation: {
    text: "text-rose-400",
    bg: "bg-rose-950/40",
    border: "border-rose-700/50",
  },
};

const PHASE_TITLES: Record<ReasoningPhase, string> = {
  trigger: "PHASE 1: INTAKE & PROFILE SYNTHESIS",
  discovery: "PHASE 2: WELFARE SCHEME DISCOVERY & MATCHING",
  verification: "PHASE 3: DIGILOCKER CREDENTIAL VERIFICATION",
  execution: "PHASE 4: APPLICATION DRAFTING & SUBMISSION",
  monitor: "PHASE 5: CITIZEN CHARTER SLA MONITORING",
  escalate: "PHASE 6: STATUTORY ADMINISTRATIVE RTI ESCALATION",
};

export function ThoughtStream({ events, isStreaming }: ThoughtStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll when new events arrive if autoScroll is enabled
  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [events, autoScroll]);

  // Track phase transitions to render dividers
  let lastPhase: ReasoningPhase | null = null;

  return (
    <div className="flex flex-col h-full bg-[#080c0e] rounded-xl border border-slate-800/80 shadow-2xl overflow-hidden relative">
      {/* Terminal Window Top Bar */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-[#0d1418] border-b border-slate-800 text-xs font-mono select-none">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80 inline-block"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80 inline-block"></span>
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80 inline-block"></span>
          </div>
          <div className="h-3.5 w-[1px] bg-slate-700 mx-1"></div>
          <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
            <Terminal className="h-3.5 w-3.5" />
            <span>sevamithra-agent-stream :: autonomous_runtime</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] text-slate-400 hidden sm:inline-block">
            {events.length} reasoning steps
          </span>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300 hover:text-white transition-colors"
            title={autoScroll ? "Pause auto-scrolling" : "Enable auto-scrolling"}
          >
            {autoScroll ? (
              <>
                <PauseCircle className="h-3 w-3 text-emerald-400" />
                <span>Auto-scroll ON</span>
              </>
            ) : (
              <>
                <PlayCircle className="h-3 w-3 text-slate-400" />
                <span>Auto-scroll OFF</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Terminal Body with CRT scanline effect */}
      <div
        ref={containerRef}
        className="flex-1 p-4 overflow-y-auto font-mono text-xs sm:text-[13px] leading-relaxed text-slate-300 terminal-scroll relative scanline-bg min-h-[480px] max-h-[720px]"
      >
        {events.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500 space-y-3">
            <ShieldCheck className="h-10 w-10 text-slate-700 animate-pulse" />
            <div className="space-y-1">
              <p className="text-slate-400 font-medium">Agent runtime standby.</p>
              <p className="text-xs text-slate-600">
                Click &quot;Start Stream&quot; above or delegate via the intake page to initiate autonomous processing.
              </p>
            </div>
            <div className="flex items-center gap-1 text-[11px] text-emerald-500/70 font-mono">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-ping"></span>
              Awaiting citizen authorization
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {events.map((event, idx) => {
              const showDivider = event.phase !== lastPhase;
              lastPhase = event.phase;
              const agentStyle = AGENT_COLORS[event.agent] || AGENT_COLORS.orchestrator;
              const isSchemeSpecific = !!event.scheme_id;

              return (
                <React.Fragment key={idx}>
                  {/* Phase Change Divider */}
                  {showDivider && (
                    <div className="my-4 pt-2">
                      <div className="flex items-center gap-3">
                        <div className="h-[1px] flex-1 bg-gradient-to-r from-transparent via-emerald-800/40 to-slate-800"></div>
                        <span className="text-[11px] font-bold tracking-wider px-2.5 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 shadow-sm">
                          {PHASE_TITLES[event.phase] || event.phase.toUpperCase()}
                        </span>
                        <div className="h-[1px] flex-1 bg-gradient-to-r from-slate-800 via-emerald-800/40 to-transparent"></div>
                      </div>
                    </div>
                  )}

                  {/* Reasoning Step Line */}
                  <div
                    className={`flex items-start gap-2.5 animate-fade-in-up transition-colors hover:bg-slate-900/40 px-2 py-1 rounded ${
                      isSchemeSpecific ? "ml-4 sm:ml-6 border-l-2 border-slate-700/60 pl-3" : ""
                    }`}
                  >
                    {/* Timestamp */}
                    <span className="text-slate-500 text-[11px] shrink-0 select-none">
                      [{formatTime(event.timestamp)}]
                    </span>

                    {/* Agent Tag */}
                    <span
                      className={`text-[11px] px-1.5 py-0.2 rounded border font-semibold uppercase tracking-tight shrink-0 select-none ${agentStyle.text} ${agentStyle.bg} ${agentStyle.border}`}
                    >
                      {event.agent}
                    </span>

                    {/* Scheme ID Tag if present */}
                    {event.scheme_id && (
                      <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700 shrink-0">
                        {event.scheme_id}
                      </span>
                    )}

                    {/* Message Body */}
                    <span className="text-emerald-200/90 break-words flex-1">
                      {event.message}
                    </span>
                  </div>
                </React.Fragment>
              );
            })}

            {/* Terminal Live Cursor */}
            {isStreaming && (
              <div className="flex items-center gap-2 pt-2 px-2 text-emerald-400">
                <span className="text-slate-600 text-[11px]">
                  [{formatTime(new Date().toISOString())}]
                </span>
                <span className="inline-block w-2.5 h-4 bg-emerald-400 animate-blink"></span>
                <span className="text-xs text-emerald-500/70 italic">
                  Autonomous agents reasoning in progress...
                </span>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>
    </div>
  );
}
