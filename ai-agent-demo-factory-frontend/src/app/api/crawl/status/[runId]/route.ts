import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest, { params }: { params: Promise<{ runId: string }> }) {
  try {
    const { runId } = await params;

    if (!runId) {
      return NextResponse.json({ error: "runId is required" }, { status: 400 });
    }

    // Server-side: Use internal Docker hostname (not NEXT_PUBLIC_)
    const backendUrl = process.env.NORCONEX_BACKEND_URL || "http://norconex-backend:5000";

    console.log(`[Status] Fetching status for runId: ${runId} from ${backendUrl}`);

    // Add 30-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    const response = await fetch(`${backendUrl}/status/${runId}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ error: "Job not found" }, { status: 404 });
      }
      const errorText = await response.text();
      console.error(`[Status] Backend error: ${response.status} - ${errorText}`);
      throw new Error(`Backend error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    console.error("[Status] Error:", msg);

    // Check if it's a timeout error
    if (err instanceof Error && err.name === 'AbortError') {
      return NextResponse.json(
        {
          error: "Request timeout - backend took too long to respond",
          timeout: true
        },
        { status: 504 }
      );
    }

    return NextResponse.json({ error: "Failed to get crawl status", details: msg }, { status: 500 });
  }
}