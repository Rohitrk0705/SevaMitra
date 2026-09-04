"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Copy, Check, Download, Scale, FileText } from "lucide-react";

interface RtiModalProps {
  isOpen: boolean;
  onClose: () => void;
  rtiData: {
    scheme_id: string;
    scheme_name?: string;
    markdown: string;
    cited_clauses: string[];
  } | null;
}

export function RtiModal({ isOpen, onClose, rtiData }: RtiModalProps) {
  const [copied, setCopied] = useState(false);

  if (!rtiData) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(rtiData.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([rtiData.markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `RTI_Application_${rtiData.scheme_id}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] flex flex-col bg-slate-950 border border-slate-700 text-slate-100 shadow-2xl p-0 overflow-hidden sm:rounded-2xl">
        {/* Header */}
        <div className="p-6 pb-4 bg-slate-900/90 border-b border-slate-800">
          <DialogHeader>
            <div className="flex items-center gap-2 mb-1">
              <div className="p-1.5 rounded-lg bg-rose-500/20 border border-rose-500/30 text-rose-400">
                <Scale className="h-5 w-5" />
              </div>
              <DialogTitle className="text-lg sm:text-xl font-bold text-white">
                Statutory Right to Information (RTI) Escalation Petition
              </DialogTitle>
            </div>
            <DialogDescription className="text-xs sm:text-sm text-slate-400">
              Autonomously drafted petition under Section 6(1) of the RTI Act 2005 for overdue application{" "}
              <span className="text-rose-300 font-mono font-semibold">{rtiData.scheme_id}</span>
            </DialogDescription>
          </DialogHeader>

          {/* Cited clauses badges */}
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
            <span className="text-xs font-mono text-slate-400 flex items-center gap-1 font-semibold">
              <FileText className="h-3.5 w-3.5 text-rose-400" />
              Statutory Citations:
            </span>
            {rtiData.cited_clauses && rtiData.cited_clauses.length > 0 ? (
              rtiData.cited_clauses.map((clause) => (
                <Badge
                  key={clause}
                  variant="outline"
                  className="bg-rose-950/40 border-rose-700/60 text-rose-300 font-mono text-xs py-0.5 px-2 hover:bg-rose-900/60 transition-colors"
                >
                  {clause}
                </Badge>
              ))
            ) : (
              <Badge variant="outline" className="text-slate-400 font-mono text-xs">
                RTI-2005-S6-1
              </Badge>
            )}
          </div>
        </div>

        {/* Rendered Markdown Body */}
        <div className="flex-1 p-6 overflow-y-auto terminal-scroll bg-slate-950/70 text-slate-200 text-sm leading-relaxed space-y-4 font-sans">
          <div className="prose prose-invert max-w-none prose-headings:text-slate-100 prose-h1:text-lg prose-h1:font-bold prose-h1:border-b prose-h1:border-slate-800 prose-h1:pb-2 prose-h2:text-base prose-h3:text-sm prose-p:text-slate-300 prose-strong:text-emerald-300 prose-li:text-slate-300 prose-hr:border-slate-800 prose-code:text-emerald-300 prose-code:bg-slate-900 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded">
            <ReactMarkdown>{rtiData.markdown}</ReactMarkdown>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 bg-slate-900/90 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div className="text-[11px] text-slate-400 font-mono flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block"></span>
            Statutory Legal Draft Ready for Direct Dispatch
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="border-slate-700 text-xs text-slate-200 hover:bg-slate-800 gap-1.5"
            >
              <Download className="h-3.5 w-3.5" />
              Download .md
            </Button>

            <Button
              variant="secondary"
              size="sm"
              onClick={handleCopy}
              className="bg-slate-800 hover:bg-slate-700 text-xs text-slate-100 gap-1.5 font-medium"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-400" />
                  Copied to Clipboard
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  Copy Text
                </>
              )}
            </Button>

            <Button
              variant="default"
              size="sm"
              onClick={onClose}
              className="bg-rose-600 hover:bg-rose-500 text-white text-xs px-4"
            >
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
