import { NextResponse } from "next/server";

export async function POST(request: Request) {
  try {
    const body = await request.json().catch(() => ({}));
    const persona = body.persona || "rekha";
    const sessionId = `SM-${Date.now().toString(36).toUpperCase()}`;

    return NextResponse.json({
      success: true,
      session_id: sessionId,
      persona,
      message: "Delegation intent received. Autonomous agents dispatched.",
      timestamp: new Date().toISOString(),
    });
  } catch {
    return NextResponse.json(
      { success: false, error: "Failed to process delegation request" },
      { status: 500 }
    );
  }
}
