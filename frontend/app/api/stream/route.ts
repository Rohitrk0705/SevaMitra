import { NextRequest } from "next/server";
import fs from "fs";
import path from "path";
import { SevaEvent, MonitorCountdownEvent } from "@/lib/events";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const persona = searchParams.get("persona") === "rajesh" ? "rajesh" : "rekha";
  const speed = searchParams.get("speed"); // e.g. "fast" for testing/quick demo

  const mockFile = path.join(
    process.cwd(),
    "mocks",
    `${persona}-happy-path.json`
  );

  let events: SevaEvent[] = [];
  try {
    const raw = fs.readFileSync(mockFile, "utf-8");
    events = JSON.parse(raw);
  } catch {
    return new Response(
      JSON.stringify({ error: `Failed to read mock file: ${mockFile}` }),
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }

  const countdownInterval = speed === "fast" ? 100 : 1000;
  const normalDelay = speed === "fast" ? 50 : 350;

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      let isAborted = false;
      request.signal.addEventListener("abort", () => {
        isAborted = true;
      });

      const sendEvent = (event: SevaEvent) => {
        if (isAborted) return false;
        try {
          const payload = `data: ${JSON.stringify(event)}\n\n`;
          controller.enqueue(encoder.encode(payload));
          return true;
        } catch {
          return false;
        }
      };

      try {
        for (let i = 0; i < events.length; i++) {
          if (isAborted) break;
          const currentEvent = { ...events[i] };
          currentEvent.timestamp = new Date().toISOString();

          sendEvent(currentEvent);

          // Check if this event initiates the monitor countdown
          const isMonitorPauseTrigger =
            currentEvent.type === "reasoning_step" &&
            currentEvent.phase === "monitor" &&
            currentEvent.message.includes("time-dilation watch");

          if (isMonitorPauseTrigger) {
            // Stream 60 seconds down to 0
            for (let sec = 60; sec >= 0; sec--) {
              if (isAborted) break;
              const countdownEvent: MonitorCountdownEvent = {
                type: "monitor_countdown",
                timestamp: new Date().toISOString(),
                seconds_remaining: sec,
              };
              sendEvent(countdownEvent);
              await sleep(countdownInterval);
            }
          } else {
            // Realistic interval between reasoning & scheme updates (200-500ms)
            const randomJitter = Math.floor(Math.random() * 200);
            await sleep(normalDelay + randomJitter);
          }
        }
      } catch {
        // Stream aborted or finished
      } finally {
        if (!isAborted) {
          try {
            controller.close();
          } catch {
            // already closed
          }
        }
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
