# SevaMithra Frontend

Autonomous Civic Welfare & RTI Escalation Agent Dashboard for Indian Citizens. Built with Next.js 14 App Router, TypeScript, Tailwind CSS, and shadcn/ui.

---

## Features

- **Agent Thought Stream (60% Split):** Real-time terminal log rendering autonomous agent reasoning (`orchestrator`, `search`, `validator`, `filler`, `monitor`, `escalation`) with phase divider banners, scheme indents, monospace typography, and live blinking cursor.
- **Scheme Threads Panel (40% Split):** Live lifecycle cards tracking each welfare scheme across a 13-stage pipeline with match confidence scoring, DigiLocker verification badges, and application IDs.
- **Time-Dilation Monitoring Timer:** Automatically surfaces when the 30-day SLA monitoring countdown starts: *"In production this waits 8 months. Right now, 60 seconds."*
- **RTI Escalation Preview Modal:** Automatically launches when the terminal RTI event fires, displaying formatted Markdown applications under Section 6(1) of the RTI Act 2005 alongside cited legal clauses as interactive badges.
- **Citizen Delegation Screen (`/delegate`):** Voice input intake with pulsing waveform simulation and textarea fallback.
- **Dual Persona Mock Feeds:** Support for both **Rekha Murugan** (Student) and **Rajesh Kumar** (Farmer) scenarios.

---

## Quick Start

### 1. Prerequisites
- Node.js 20+
- npm

### 2. Install & Run Locally

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

- Visiting `/` displays the standby agent dashboard. Click **"Start Stream"** (or **"Fast"** for a 10x accelerated demo) to begin streaming.
- Visiting `/delegate` allows you to speak or type a citizen request, and clicking **"Delegate to SevaMithra"** routes back to `/` and auto-starts the stream.
- Switch between **Rekha** and **Rajesh** via the top-right persona selector.

---

## Project Structure

```
frontend/
├── app/
│   ├── api/
│   │   ├── delegate/route.ts      # POST mock delegation intake endpoint
│   │   └── stream/route.ts        # Mock SSE streaming engine (?persona=rekha|rajesh)
│   ├── delegate/
│   │   └── page.tsx               # Voice / Text delegation intake screen
│   ├── globals.css                # Slate dark theme styling, terminal animations
│   ├── layout.tsx                 # Root layout with font & metadata
│   └── page.tsx                   # Main dashboard (60/40 layout + timer + modal)
├── components/
│   ├── ui/                        # shadcn/ui primitives (Card, Badge, Progress, Dialog, Button)
│   ├── Header.tsx                 # Branding, persona dropdown, stream controls
│   ├── ThoughtStream.tsx          # Terminal thought stream with auto-scroll & phase banners
│   ├── SchemeThreadsPanel.tsx     # Active scheme cards panel
│   ├── SchemeCard.tsx             # 13-stage lifecycle card with confidence & SLA badges
│   ├── MonitorTimerWidget.tsx     # 60s countdown card with production disclaimer narrative
│   └── RtiModal.tsx               # Rendered RTI application dialog with cited clauses
├── lib/
│   ├── events.ts                  # Authoritative discriminated union types matching backend
│   └── utils.ts                   # Tailwind cn helper & time formatters
└── mocks/
    ├── rekha-happy-path.json      # 3 schemes -> 1 blocked, 2 filed, 1 pending -> RTI draft
    └── rajesh-happy-path.json     # Farmer persona dataset (PM-KISAN, Kuruvai RTI)
```

---

## Event Architecture (`lib/events.ts`)

The frontend strictly types against 4 discriminated SSE events:

1. `reasoning_step`: Autonomous agent log entries across `trigger`, `discovery`, `verification`, `execution`, `monitor`, `escalate`.
2. `scheme_thread_update`: 13-stage lifecycle state transitions for each `scheme_id`.
3. `monitor_countdown`: 1s ticker during statutory monitoring (`seconds_remaining: 60..0`).
4. `rti_draft_ready`: Terminal event containing full rendered Markdown and cited clauses.

---

## How to Connect to the Real Backend

When the Python LangGraph backend is ready:

1. Create a `.env.local` file inside `frontend/`:
   ```bash
   NEXT_PUBLIC_SSE_URL=http://127.0.0.1:8000/api/stream
   ```
2. Restart the Next.js dev server (`npm run dev`).

The frontend will immediately stream live LangGraph agent events without requiring any code changes.
