import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  try {
    const { target_url } = await req.json();

    if (!target_url || typeof target_url !== "string") {
      return NextResponse.json({ error: "target_url is required" }, { status: 400 });
    }

    // Forward request to FastAPI backend
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://backend:5000";
    
    const response = await fetch(`${backendUrl}/crawl`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ target_url }),
    });

    if (!response.ok) {
      throw new Error(`Backend error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    console.error("Crawl API error:", msg);
    return NextResponse.json({ error: "Failed to start crawl", details: msg }, { status: 500 });
  }
}