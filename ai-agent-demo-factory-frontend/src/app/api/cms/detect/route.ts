import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://backend:5000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${BACKEND_URL}/cms/detect`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('CMS detection API error:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to connect to backend service',
        timestamp: Date.now()
      },
      { status: 500 }
    );
  }
}