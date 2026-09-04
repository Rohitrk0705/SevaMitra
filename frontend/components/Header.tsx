"use client";

import React from "react";
import Link from "next/link";
import { Shield, Radio, Play, RotateCcw, Mic, FastForward } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface HeaderProps {
  persona: "rekha" | "rajesh";
  onPersonaChange: (p: "rekha" | "rajesh") => void;
  isStreaming: boolean;
  onStartStream: (speed?: "normal" | "fast") => void;
  onResetStream: () => void;
  hasEvents: boolean;
}

export function Header({
  persona,
  onPersonaChange,
  isStreaming,
  onStartStream,
  onResetStream,
  hasEvents,
}: HeaderProps) {
  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        {/* Brand & Tagline */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-600 via-teal-500 to-emerald-400 p-[1px] shadow-lg shadow-emerald-900/30">
            <div className="h-full w-full bg-slate-950 rounded-[11px] flex items-center justify-center">
              <Shield className="h-5 w-5 text-emerald-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                SevaMithra
              </h1>
              <Badge variant="agent" className="py-0 px-2 tracking-wider text-[10px]">
                AUTONOMOUS CIVIC AGENT
              </Badge>
            </div>
            <p className="text-xs text-slate-400">
              Autonomous Citizen Welfare Navigation, Automated Filing & Statutory RTI Escalation
            </p>
          </div>
        </div>

        {/* Persona Selector & Stream Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Persona Selector */}
          <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1">
            <span className="text-[11px] text-slate-400 px-2 font-medium">Citizen:</span>
            <select
              value={persona}
              disabled={isStreaming}
              onChange={(e) => onPersonaChange(e.target.value as "rekha" | "rajesh")}
              className="bg-slate-950 text-slate-200 text-xs rounded border border-slate-700 px-2.5 py-1 focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:opacity-50 font-medium cursor-pointer"
            >
              <option value="rekha">Rekha Murugan (Student, 18)</option>
              <option value="rajesh">Rajesh Kumar (Farmer, 45)</option>
            </select>
          </div>

          {/* Stream Status Indicator */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs">
            <Radio
              className={`h-3.5 w-3.5 ${
                isStreaming
                  ? "text-emerald-400 animate-pulse"
                  : hasEvents
                  ? "text-teal-400"
                  : "text-slate-500"
              }`}
            />
            <span
              className={`font-mono text-[11px] ${
                isStreaming
                  ? "text-emerald-400 font-semibold"
                  : hasEvents
                  ? "text-slate-300"
                  : "text-slate-500"
              }`}
            >
              {isStreaming ? "STREAM ACTIVE" : hasEvents ? "CYCLE READY" : "IDLE"}
            </span>
          </div>

          {/* Delegate Link */}
          <Link href="/delegate">
            <Button
              variant="outline"
              size="sm"
              className="border-slate-700 text-xs hover:border-emerald-500/50 hover:bg-slate-900 gap-1.5"
            >
              <Mic className="h-3.5 w-3.5 text-emerald-400" />
              Delegate
            </Button>
          </Link>

          {/* Stream trigger dev buttons */}
          {!isStreaming ? (
            <div className="flex items-center gap-1.5">
              <Button
                variant="default"
                size="sm"
                onClick={() => onStartStream("normal")}
                className="bg-emerald-600 hover:bg-emerald-500 text-xs gap-1.5 font-medium shadow-md shadow-emerald-950"
              >
                <Play className="h-3.5 w-3.5 fill-current" />
                Start Stream
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onStartStream("fast")}
                title="Run stream in fast demo mode (10x timer)"
                className="bg-slate-800 hover:bg-slate-700 text-xs gap-1 px-2.5 text-slate-300"
              >
                <FastForward className="h-3.5 w-3.5 text-amber-400" />
                Fast
              </Button>
            </div>
          ) : (
            <Button
              variant="destructive"
              size="sm"
              onClick={onResetStream}
              className="text-xs gap-1.5"
            >
              Stop
            </Button>
          )}

          {hasEvents && !isStreaming && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onResetStream}
              className="text-xs gap-1 text-slate-400 hover:text-slate-200"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
