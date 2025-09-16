import { NextResponse } from "next/server";

// For server-side API routes, use internal Docker service name
const BACKEND_URL = "http://backend:5000";

export async function GET() {
    try {
        console.log(`Fetching crawl list from: ${BACKEND_URL}/crawl/list`);

        const response = await fetch(`${BACKEND_URL}/crawl/list`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json"
            },
            // Add cache control to prevent caching issues
            cache: 'no-store'
        });

        console.log(`Backend response status: ${response.status}`);

        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Backend error response: ${errorText}`);
            return NextResponse.json(
                { error: `Backend error: ${response.status} - ${errorText}` },
                { status: response.status }
            );
        }

        const data = await response.json();
        console.log(`Successfully fetched ${data.runs?.length || 0} runs`);
        return NextResponse.json(data);

    } catch (error) {
        console.error("Error fetching crawl list:", error);
        return NextResponse.json(
            { error: `Failed to fetch crawl runs: ${error instanceof Error ? error.message : 'Unknown error'}` },
            { status: 500 }
        );
    }
}