import { NextRequest, NextResponse } from 'next/server';

// Server-side: Use internal Docker hostname (not NEXT_PUBLIC_)
const BACKEND_URL = process.env.NORCONEX_BACKEND_URL || 'http://norconex-backend:5000';

export async function GET(request: NextRequest) {
  try {
    console.log(`[Supported CMS] Fetching from: ${BACKEND_URL}/cms/supported`);

    // Add 30-second timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000);

    const response = await fetch(`${BACKEND_URL}/cms/supported`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[Supported CMS] Backend error: ${response.status} - ${errorText}`);
      return NextResponse.json(
        {
          success: false,
          error: `Backend error: ${response.status}`
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('[Supported CMS] Error:', error);

    if (error instanceof Error && error.name === 'AbortError') {
      return NextResponse.json(
        {
          success: false,
          error: 'Request timeout - backend took too long to respond'
        },
        { status: 504 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        error: 'Failed to connect to backend service',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}