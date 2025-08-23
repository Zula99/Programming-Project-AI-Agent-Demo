import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function POST(req: NextRequest) {
  try {
    const { query, size = 50, matchAll = false } = await req.json();

    if (!matchAll && (!query || typeof query !== "string")) {
      return NextResponse.json({ error: "Query is required" }, { status: 400 });
    }

    const base = process.env.OPENSEARCH_BASE_URL || "http://localhost:9200";
    const index = process.env.OPENSEARCH_INDEX || "nab_search";

    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (process.env.OPENSEARCH_USERNAME && process.env.OPENSEARCH_PASSWORD) {
      const token = Buffer
        .from(`${process.env.OPENSEARCH_USERNAME}:${process.env.OPENSEARCH_PASSWORD}`)
        .toString("base64");
      headers.Authorization = `Basic ${token}`;
    }

    const body = matchAll
      ? {
          query: { match_all: {} },
          sort: [{ _score: "desc" }],
          size,
        }
      : {
          query: {
            multi_match: {
              query,
              fields: ["title^3", "description^2", "content"],
              type: "best_fields",
              fuzziness: "AUTO",
            },
          },
          highlight: {
            fields: {
              title: {},
              description: {},
              content: { fragment_size: 150, number_of_fragments: 2 },
            },
          },
          size,
        };

    const resp = await fetch(`${base}/${index}/_search`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    if (!resp.ok) throw new Error(`OpenSearch error: ${resp.status} ${resp.statusText}`);
    const data = await resp.json();
    return NextResponse.json(data);
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Unknown error";
    console.error("Search API error:", msg);
    return NextResponse.json({ error: "Search failed", details: msg }, { status: 500 });
  }
}