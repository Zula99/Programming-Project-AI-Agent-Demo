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

    // Forward request to FastAPI backend
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://backend:5000";
    
    const response = await fetch(`${backendUrl}/crawl/stop/${runId}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
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
    return NextResponse.json(data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    console.error("Stop crawl API error:", msg);
    return NextResponse.json({ error: "Failed to stop crawl", details: msg }, { status: 500 });
  }
}