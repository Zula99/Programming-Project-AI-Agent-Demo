import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(req: NextRequest, { params }: { params: Promise<{ runId: string }> }) {
  try {
    const { runId } = await params;

    if (!runId) {
      return NextResponse.json({ error: "runId is required" }, { status: 400 });
    }

    // Forward request to FastAPI backend
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://backend:5000";
    
    const response = await fetch(`${backendUrl}/status/${runId}`, {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ error: "Job not found" }, { status: 404 });
      }
      throw new Error(`Backend error: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    console.error("Status API error:", msg);
    return NextResponse.json({ error: "Failed to get crawl status", details: msg }, { status: 500 });
  }
}