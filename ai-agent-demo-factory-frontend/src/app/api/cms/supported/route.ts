import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://norconex-backend:5000';

export async function GET(request: NextRequest) {
  try {
    const response = await fetch(`${BACKEND_URL}/cms/supported`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('Supported CMS API error:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to connect to backend service'
      },
      { status: 500 }
    );
  }
}