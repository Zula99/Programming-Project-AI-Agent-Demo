import { NextRequest, NextResponse } from 'next/server';

// Server-side: Use internal Docker hostname (not NEXT_PUBLIC_)
const BACKEND_URL = process.env.NORCONEX_BACKEND_URL || 'http://norconex-backend:5000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    console.log(`[CMS Detect] Sending request to: ${BACKEND_URL}/cms/detect`);

    // Add 30-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    const response = await fetch(`${BACKEND_URL}/cms/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[CMS Detect] Backend error: ${response.status} - ${errorText}`);
      return NextResponse.json(
        {
          success: false,
          error: `Backend error: ${response.status}`,
          timestamp: Date.now()
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log(`[CMS Detect] Success`);

    return NextResponse.json(data);
  } catch (error) {
    console.error('[CMS Detect] Error:', error);

    // Check if it's a timeout error
    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        {
          success: false,
          error: 'Request timeout - backend took too long to respond',
          timeout: true,
          timestamp: Date.now()
        },
        { status: 504 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        error: 'Failed to connect to backend service',
        details: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      },
      { status: 500 }
    );
  }
}