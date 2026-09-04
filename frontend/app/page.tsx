"use client";

import React, { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/Header";
import { ThoughtStream } from "@/components/ThoughtStream";
import { SchemeThreadsPanel } from "@/components/SchemeThreadsPanel";
import { MonitorTimerWidget } from "@/components/MonitorTimerWidget";
import { RtiModal } from "@/components/RtiModal";
import {
  ReasoningStepEvent,
  SchemeThreadState,
  SevaEvent,
} from "@/lib/events";

function DashboardContent() {
  const searchParams = useSearchParams();
  const initialPersona = (searchParams.get("persona") as "rekha" | "rajesh") || "rekha";
  const shouldAutoStart = searchParams.get("stream") === "true";

  const [persona, setPersona] = useState<"rekha" | "rajesh">(initialPersona);
  const [isStreaming, setIsStreaming] = useState(false);
  const [reasoningEvents, setReasoningEvents] = useState<ReasoningStepEvent[]>([]);
  const [schemesMap, setSchemesMap] = useState<Map<string, SchemeThreadState>>(
    new Map()
  );
  const [countdown, setCountdown] = useState<number | null>(null);
  const [rtiModalData, setRtiModalData] = useState<{
    scheme_id: string;
    scheme_name?: string;
    markdown: string;
    cited_clauses: string[];
  } | null>(null);
  const [isRtiModalOpen, setIsRtiModalOpen] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);

  const resetStream = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsStreaming(false);
    setReasoningEvents([]);
    setSchemesMap(new Map());
    setCountdown(null);
    setRtiModalData(null);
    setIsRtiModalOpen(false);
  }, []);

  const startStream = useCallback(
    (speed: "normal" | "fast" = "normal") => {
      // Close previous connection if active
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }

      setReasoningEvents([]);
      setSchemesMap(new Map());
      setCountdown(null);
      setRtiModalData(null);
      setIsRtiModalOpen(false);
      setIsStreaming(true);

      const baseUrl = process.env.NEXT_PUBLIC_SSE_URL || "/api/stream";
      const streamUrl = `${baseUrl}?persona=${persona}${
        speed === "fast" ? "&speed=fast" : ""
      }`;

      const es = new EventSource(streamUrl);
      eventSourceRef.current = es;

      es.onmessage = (e) => {
        try {
          const event: SevaEvent = JSON.parse(e.data);

          if (event.type === "reasoning_step") {
            setReasoningEvents((prev) => [...prev, event]);
          } else if (event.type === "scheme_thread_update") {
            setSchemesMap((prev) => {
              const updated = new Map(prev);
              const existing = updated.get(event.scheme_id);
              updated.set(event.scheme_id, {
                scheme_id: event.scheme_id,
                scheme_name: event.scheme_name,
                phase: event.phase,
                confidence: event.confidence ?? existing?.confidence,
                application_id: event.application_id ?? existing?.application_id,
                rti_markdown: event.rti_markdown ?? existing?.rti_markdown,
                cited_clauses: existing?.cited_clauses,
                updated_at: event.timestamp,
              });
              return updated;
            });
          } else if (event.type === "monitor_countdown") {
            setCountdown(event.seconds_remaining);
          } else if (event.type === "rti_draft_ready") {
            // Update scheme state with RTI data
            setSchemesMap((prev) => {
              const updated = new Map(prev);
              const existing = updated.get(event.scheme_id);
              if (existing) {
                updated.set(event.scheme_id, {
                  ...existing,
                  rti_markdown: event.markdown,
                  cited_clauses: event.cited_clauses,
                  updated_at: event.timestamp,
                });
              }
              return updated;
            });

            // Set modal data & open automatically
            setRtiModalData({
              scheme_id: event.scheme_id,
              markdown: event.markdown,
              cited_clauses: event.cited_clauses,
            });
            setIsRtiModalOpen(true);
          }
        } catch (err) {
          console.error("Failed to parse SSE event:", err);
        }
      };

      es.onerror = () => {
        setIsStreaming(false);
        es.close();
        eventSourceRef.current = null;
      };
    },
    [persona]
  );

  // Auto-start on mount if redirected with ?stream=true
  useEffect(() => {
    if (shouldAutoStart) {
      startStream("normal");
    }
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [shouldAutoStart, startStream]);

  const handleOpenRti = (scheme: SchemeThreadState) => {
    if (scheme.rti_markdown) {
      setRtiModalData({
        scheme_id: scheme.scheme_id,
        scheme_name: scheme.scheme_name,
        markdown: scheme.rti_markdown,
        cited_clauses: scheme.cited_clauses || ["RTI-2005-S6-1"],
      });
      setIsRtiModalOpen(true);
    }
  };

  const schemesList = Array.from(schemesMap.values());

  return (
    <div className="min-h-screen flex flex-col bg-[#05080a] text-slate-100 antialiased font-sans">
      <Header
        persona={persona}
        onPersonaChange={(p) => {
          setPersona(p);
          resetStream();
        }}
        isStreaming={isStreaming}
        onStartStream={startStream}
        onResetStream={resetStream}
        hasEvents={reasoningEvents.length > 0}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Main 60/40 Split Columns */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left 60% Width: Agent Thought Stream */}
          <div className="lg:col-span-7 h-[580px] sm:h-[680px]">
            <ThoughtStream
              events={reasoningEvents}
              isStreaming={isStreaming}
            />
          </div>

          {/* Right 40% Width: Scheme Threads Panel */}
          <div className="lg:col-span-5 h-[580px] sm:h-[680px] bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 sm:p-5 flex flex-col backdrop-blur-sm shadow-xl">
            <SchemeThreadsPanel
              schemes={schemesList}
              onOpenRti={handleOpenRti}
              isStreaming={isStreaming}
            />
          </div>
        </div>

        {/* Bottom: Timer Widget (Shown when countdown is triggered) */}
        <div className="transition-all duration-500">
          <MonitorTimerWidget secondsRemaining={countdown} />
        </div>
      </main>

      {/* RTI Rendered Markdown Modal */}
      <RtiModal
        isOpen={isRtiModalOpen}
        onClose={() => setIsRtiModalOpen(false)}
        rtiData={rtiModalData}
      />
    </div>
  );
}

export default function HomePage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#05080a] flex items-center justify-center text-slate-400 font-mono text-xs">
          Loading SevaMithra runtime...
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  );
}
