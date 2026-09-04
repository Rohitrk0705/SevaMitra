"use client";

import React, { useState } from "react";
import {
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertTriangle,
  Clock,
  FileText,
  FileCheck,
  ExternalLink,
} from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { SchemeThreadState, SCHEME_PHASES, SchemePhase } from "@/lib/events";
import { formatTime } from "@/lib/utils";

interface SchemeCardProps {
  scheme: SchemeThreadState;
  onOpenRti: (scheme: SchemeThreadState) => void;
}

const PHASE_INDEX_MAP: Record<SchemePhase, number> = {
  matched: 0,
  eligibility_checked: 1,
  documents_requested: 2,
  documents_verified: 3,
  documents_missing: 3, // alternate branch
  form_fetched: 4,
  form_filled: 5,
  submitted: 6,
  monitoring: 7,
  deadline_crossed: 8,
  escalation_drafted: 9,
  rti_drafted: 10,
  completed: 11,
};

export function SchemeCard({ scheme, onOpenRti }: SchemeCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const currentIndex = PHASE_INDEX_MAP[scheme.phase] ?? 0;
  const isCompleted = scheme.phase === "completed";
  const isBlocked = scheme.phase === "documents_missing";
  const isEscalating =
    scheme.phase === "deadline_crossed" ||
    scheme.phase === "escalation_drafted" ||
    scheme.phase === "rti_drafted";
  const isMonitoring = scheme.phase === "monitoring";

  // Calculate progress percentage across primary stages
  const progressPercent = isBlocked
    ? 30
    : Math.min(100, Math.round(((currentIndex + 1) / 12) * 100));

  return (
    <Card
      className={`border transition-all duration-300 ${
        isCompleted
          ? "border-emerald-500/40 bg-emerald-950/20 shadow-emerald-950/30"
          : isEscalating
          ? "border-rose-500/40 bg-rose-950/20 shadow-rose-950/30"
          : isBlocked
          ? "border-amber-500/40 bg-amber-950/20"
          : isMonitoring
          ? "border-cyan-500/40 bg-cyan-950/20"
          : "border-slate-800 bg-slate-900/60"
      }`}
    >
      <CardHeader className="p-4 pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-semibold">
                {scheme.scheme_id}
              </span>

              {/* Status Badge */}
              {isCompleted ? (
                <Badge variant="success" className="text-[10px] gap-1 py-0">
                  <CheckCircle2 className="h-3 w-3" />
                  DISBURSED / COMPLETED
                </Badge>
              ) : isEscalating ? (
                <Badge variant="destructive" className="text-[10px] gap-1 py-0 animate-pulse">
                  <AlertTriangle className="h-3 w-3" />
                  SLA OVERDUE &bull; RTI DRAFTED
                </Badge>
              ) : isBlocked ? (
                <Badge variant="warning" className="text-[10px] gap-1 py-0">
                  <AlertTriangle className="h-3 w-3" />
                  DOCS BLOCKED (EXPIRED)
                </Badge>
              ) : isMonitoring ? (
                <Badge variant="cyan" className="text-[10px] gap-1 py-0">
                  <Clock className="h-3 w-3 animate-spin" />
                  MONITORING 30-DAY SLA
                </Badge>
              ) : (
                <Badge variant="secondary" className="text-[10px] py-0 text-slate-300">
                  {scheme.phase.replace("_", " ").toUpperCase()}
                </Badge>
              )}
            </div>

            <CardTitle className="text-sm sm:text-base font-semibold text-white leading-snug pt-0.5">
              {scheme.scheme_name}
            </CardTitle>
          </div>

          {/* Confidence indicator */}
          {scheme.confidence !== undefined && (
            <div className="text-right shrink-0">
              <div className="text-[10px] text-slate-400 font-mono">MATCH FIT</div>
              <div
                className={`text-sm font-bold font-mono ${
                  scheme.confidence > 0.9
                    ? "text-emerald-400"
                    : scheme.confidence > 0.7
                    ? "text-teal-400"
                    : "text-amber-400"
                }`}
              >
                {Math.round(scheme.confidence * 100)}%
              </div>
            </div>
          )}
        </div>

        {/* Progress Bar & Phase Stepper */}
        <div className="pt-3 space-y-1.5">
          <div className="flex justify-between items-center text-[11px] font-mono">
            <span className="text-slate-400">
              Phase:{" "}
              <strong className="text-slate-200 capitalize">
                {scheme.phase.replace(/_/g, " ")}
              </strong>
            </span>
            <span className="text-slate-500">{progressPercent}%</span>
          </div>

          <Progress
            value={progressPercent}
            className="h-1.5 bg-slate-800"
            indicatorClassName={
              isCompleted
                ? "bg-emerald-500"
                : isEscalating
                ? "bg-rose-500"
                : isBlocked
                ? "bg-amber-500"
                : "bg-teal-500"
            }
          />

          {/* 13-step miniature visual pipeline */}
          <div className="grid grid-cols-6 sm:grid-cols-12 gap-1 pt-1">
            {SCHEME_PHASES.filter(
              (p) =>
                p.phase !== "documents_missing" ||
                scheme.phase === "documents_missing"
            )
              .slice(0, 12)
              .map((p, idx) => {
                const isStepPassed = idx <= currentIndex;
                const isStepCurrent = p.phase === scheme.phase;
                return (
                  <div
                    key={p.phase}
                    title={`${p.label} (${p.phase})`}
                    className={`h-1 rounded-sm transition-all ${
                      isStepCurrent
                        ? isEscalating
                          ? "bg-rose-400 ring-1 ring-rose-300"
                          : isBlocked
                          ? "bg-amber-400 ring-1 ring-amber-300"
                          : "bg-emerald-400 ring-1 ring-emerald-300"
                        : isStepPassed
                        ? isCompleted
                          ? "bg-emerald-600/70"
                          : isEscalating
                          ? "bg-rose-800/60"
                          : "bg-teal-700/60"
                        : "bg-slate-800"
                    }`}
                  />
                );
              })}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-4 pt-1 space-y-3">
        {/* Application ID if submitted */}
        {scheme.application_id && (
          <div className="flex items-center justify-between p-2 rounded bg-slate-950/70 border border-slate-800 text-xs font-mono">
            <span className="text-slate-400 flex items-center gap-1.5">
              <FileCheck className="h-3.5 w-3.5 text-emerald-400" />
              App ID:
            </span>
            <span className="text-emerald-300 font-semibold select-all">
              {scheme.application_id}
            </span>
          </div>
        )}

        {/* RTI Button if RTI is available */}
        {(scheme.rti_markdown || scheme.phase === "rti_drafted") && (
          <Button
            size="sm"
            onClick={() => onOpenRti(scheme)}
            className="w-full bg-rose-600/90 hover:bg-rose-500 text-white text-xs gap-1.5 shadow-md shadow-rose-950 font-medium py-1.5"
          >
            <FileText className="h-3.5 w-3.5" />
            Inspect RTI Escalation Petition
            <ExternalLink className="h-3 w-3 ml-auto opacity-70" />
          </Button>
        )}

        {/* Expand / Collapse Details */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between text-[11px] text-slate-400 hover:text-slate-200 py-1 transition-colors border-t border-slate-800/60 pt-2"
        >
          <span>{isExpanded ? "Hide detailed audit" : "Show lifecycle detail"}</span>
          {isExpanded ? (
            <ChevronUp className="h-3.5 w-3.5" />
          ) : (
            <ChevronDown className="h-3.5 w-3.5" />
          )}
        </button>

        {isExpanded && (
          <div className="pt-2 space-y-2 text-xs border-t border-slate-800/80 animate-fade-in-up">
            <div className="grid grid-cols-2 gap-2 text-slate-400 text-[11px]">
              <div>
                <span className="block text-slate-500 font-mono text-[10px]">
                  LAST EVENT
                </span>
                <span>{formatTime(scheme.updated_at)}</span>
              </div>
              <div>
                <span className="block text-slate-500 font-mono text-[10px]">
                  STATUS
                </span>
                <span className="font-mono capitalize text-slate-300">
                  {scheme.phase}
                </span>
              </div>
            </div>

            {scheme.cited_clauses && scheme.cited_clauses.length > 0 && (
              <div>
                <span className="block text-slate-500 font-mono text-[10px] mb-1">
                  CITED STATUTORY CLAUSES
                </span>
                <div className="flex flex-wrap gap-1">
                  {scheme.cited_clauses.map((c) => (
                    <Badge
                      key={c}
                      variant="outline"
                      className="text-[10px] font-mono border-rose-800/50 text-rose-300"
                    >
                      {c}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
