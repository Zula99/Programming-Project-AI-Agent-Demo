import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
    try {
        const { query } = await request.json();

        if (!query || typeof query !== "string") {
            return NextResponse.json({ error: "Query is required" }, { status: 400 });
        }

        const searchResponse = await fetch("http://localhost:9200/nab_search/_search", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                query: {
                    multi_match: {
                        query: query,
                        fields: ["title^3", "description^2", "content"],
                        type: "best_fields",
                        fuzziness: "AUTO"
                    }
                },
                highlight: {
                    fields: {
                        title: {},
                        description: {},
                        content: { fragment_size: 150, number_of_fragments: 2 }
                    }
                },
                size: 10
            })
        });

        if (!searchResponse.ok) {
            throw new Error(`OpenSearch error: ${searchResponse.status}`);
        }

        const data = await searchResponse.json();
        return NextResponse.json(data);

    } catch (error) {
        console.error("Search API error:", error);
        return NextResponse.json(
            { error: "Search failed", details: error instanceof Error ? error.message : "Unknown error" },
            { status: 500 }
        );
    }
}