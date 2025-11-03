import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  try {
    const { target_url } = await req.json();

    if (!target_url || typeof target_url !== "string") {
      return NextResponse.json({ error: "target_url is required" }, { status: 400 });
    }

    // Server-side: Use internal Docker hostname (not NEXT_PUBLIC_)
    const backendUrl = process.env.NORCONEX_BACKEND_URL || "http://norconex-backend:5000";

    console.log(`[Start Crawl] Starting crawl for ${target_url} via ${backendUrl}`);

    // Add 30-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    const response = await fetch(`${backendUrl}/crawl`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ target_url }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[Start Crawl] Backend error: ${response.status} - ${errorText}`);
      throw new Error(`Backend error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    console.log(`[Start Crawl] Success - runId: ${data.run_id || 'unknown'}`);
    return NextResponse.json(data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    console.error("[Start Crawl] Error:", msg);

    if (err instanceof Error && err.name === 'AbortError') {
      return NextResponse.json(
        {
          error: "Request timeout - backend took too long to respond",
          timeout: true
        },
        { status: 504 }
      );
    }

    return NextResponse.json({ error: "Failed to start crawl", details: msg }, { status: 500 });
  }
}