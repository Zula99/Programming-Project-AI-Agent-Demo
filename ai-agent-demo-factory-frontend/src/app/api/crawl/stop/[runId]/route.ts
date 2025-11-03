import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(
  req: NextRequest,
  { params }: { params: { runId: string } }
) {
  try {
    const { runId } = params;

    if (!runId || typeof runId !== "string") {
      return NextResponse.json({ error: "runId is required" }, { status: 400 });
    }

    // Server-side: Use internal Docker hostname (not NEXT_PUBLIC_)
    const backendUrl = process.env.NORCONEX_BACKEND_URL || "http://norconex-backend:5000";

    console.log(`[Stop Crawl] Stopping crawl ${runId} via ${backendUrl}`);

    // Add 30-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    const response = await fetch(`${backendUrl}/crawl/stop/${runId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[Stop Crawl] Backend error: ${response.status} - ${errorText}`);
      let errorData;
      try {
        errorData = JSON.parse(errorText);
      } catch {
        errorData = { detail: errorText };
      }

      return NextResponse.json(
        { error: "Failed to stop crawl", details: errorData.detail || errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log(`[Stop Crawl] Success`);
    return NextResponse.json(data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    console.error("[Stop Crawl] Error:", msg);

    if (err instanceof Error && err.name === 'AbortError') {
      return NextResponse.json(
        {
          error: "Request timeout - backend took too long to respond",
          timeout: true
        },
        { status: 504 }
      );
    }

    return NextResponse.json({ error: "Failed to stop crawl", details: msg }, { status: 500 });
  }
}