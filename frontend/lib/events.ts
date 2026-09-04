/**
 * Authoritative Event Types for SevaMithra SSE stream.
 * Exactly mirrors backend/state.py stream definitions.
 */

export type ReasoningPhase =
  | "trigger"
  | "discovery"
  | "verification"
  | "execution"
  | "monitor"
  | "escalate";

export type AgentRole =
  | "orchestrator"
  | "search"
  | "validator"
  | "filler"
  | "monitor"
  | "escalation";

export interface ReasoningStepEvent {
  type: "reasoning_step";
  timestamp: string; // ISO 8601
  phase: ReasoningPhase;
  agent: AgentRole;
  message: string;
  scheme_id?: string;
}

export type SchemePhase =
  | "matched"
  | "eligibility_checked"
  | "documents_requested"
  | "documents_verified"
  | "documents_missing"
  | "form_fetched"
  | "form_filled"
  | "submitted"
  | "monitoring"
  | "deadline_crossed"
  | "escalation_drafted"
  | "rti_drafted"
  | "completed";

export interface SchemeThreadUpdateEvent {
  type: "scheme_thread_update";
  timestamp: string;
  scheme_id: string;
  scheme_name: string;
  phase: SchemePhase;
  confidence?: number; // 0.0 - 1.0
  application_id?: string;
  rti_markdown?: string;
}

export interface RtiDraftReadyEvent {
  type: "rti_draft_ready";
  timestamp: string;
  scheme_id: string;
  markdown: string;
  cited_clauses: string[];
}

export interface MonitorCountdownEvent {
  type: "monitor_countdown";
  timestamp: string;
  seconds_remaining: number;
}

export type SevaEvent =
  | ReasoningStepEvent
  | SchemeThreadUpdateEvent
  | RtiDraftReadyEvent
  | MonitorCountdownEvent;

// Scheme phase order definition for the 13-step progress pipeline
export const SCHEME_PHASES: { phase: SchemePhase; label: string; shortLabel: string }[] = [
  { phase: "matched", label: "Matched", shortLabel: "Match" },
  { phase: "eligibility_checked", label: "Eligibility Checked", shortLabel: "Eligible" },
  { phase: "documents_requested", label: "Documents Requested", shortLabel: "Docs Req" },
  { phase: "documents_verified", label: "Documents Verified", shortLabel: "Docs OK" },
  { phase: "documents_missing", label: "Documents Missing", shortLabel: "Docs Gap" },
  { phase: "form_fetched", label: "Form Fetched", shortLabel: "Form" },
  { phase: "form_filled", label: "Form Filled", shortLabel: "Filled" },
  { phase: "submitted", label: "Submitted", shortLabel: "Filed" },
  { phase: "monitoring", label: "Monitoring SLA", shortLabel: "Monitor" },
  { phase: "deadline_crossed", label: "Deadline Crossed", shortLabel: "Overdue" },
  { phase: "escalation_drafted", label: "Escalation Drafted", shortLabel: "Escalate" },
  { phase: "rti_drafted", label: "RTI Drafted", shortLabel: "RTI" },
  { phase: "completed", label: "Completed", shortLabel: "Done" },
];

export interface SchemeThreadState {
  scheme_id: string;
  scheme_name: string;
  phase: SchemePhase;
  confidence?: number;
  application_id?: string;
  rti_markdown?: string;
  cited_clauses?: string[];
  updated_at: string;
}
