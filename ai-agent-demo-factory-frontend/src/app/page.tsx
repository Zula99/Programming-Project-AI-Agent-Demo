"use client";

import { useState } from "react";

interface SearchResult {
  _id: string;
  _score: number;
  _source: {
    title: string;
    description: string;
    url: string;
    content?: string;
    metadata?: {
      depth?: string;
      contentType?: string;
    };
  };
}

interface SearchResponse {
  took: number;
  hits: {
    total: { value: number };
    hits: SearchResult[];
  };
}

export default function NABSearchDemo() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalHits, setTotalHits] = useState(0);
  const [searchTime, setSearchTime] = useState(0);
  const [error, setError] = useState("");

  const searchOpenSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setTotalHits(0);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ query: searchQuery }),
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.status}`);
      }

      const data: SearchResponse = await response.json();
      setResults(data.hits.hits);
      setTotalHits(data.hits.total.value);
      setSearchTime(data.took);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setResults([]);
      setTotalHits(0);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    searchOpenSearch(query);
  };

  const demoQueries = ["banking", "loans", "credit cards", "mortgage", "business"];

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Demo Factory Search</h1>
              <p className="text-gray-600 mt-1">Search crawled NAB banking content</p>
            </div>
            <div className="flex items-center gap-4 text-sm">
              <div className="text-gray-500">
                Index: <span className="font-mono bg-gray-100 px-2 py-1 rounded">nab_search</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span className="text-green-600">OpenSearch Connected</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <form onSubmit={handleSearch} className="mb-8">
          <div className="flex gap-4">
            <div className="flex-1">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search NAB content... (try 'banking', 'loans', 'credit cards')"
                className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {loading ? "Searching..." : "Search"}
            </button>
          </div>
        </form>

        <div className="mb-6">
          <p className="text-sm text-gray-600 mb-2">Try these demo searches:</p>
          <div className="flex flex-wrap gap-2">
            {demoQueries.map((demoQuery) => (
              <button
                key={demoQuery}
                onClick={() => {
                  setQuery(demoQuery);
                  searchOpenSearch(demoQuery);
                }}
                className="px-3 py-1 bg-gray-200 text-gray-700 rounded-full text-sm hover:bg-gray-300 transition-colors"
              >
                {demoQuery}
              </button>
            ))}
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
            <p><strong>Error:</strong> {error}</p>
            <p className="text-sm mt-1">Make sure OpenSearch is running: docker-compose up -d</p>
          </div>
        )}

        {(totalHits > 0 || query) && !error && (
          <div className="text-sm text-gray-600 mb-4">
            {totalHits > 0 ? (
              <>Found {totalHits} results in {searchTime}ms</>
            ) : query && !loading ? (
              <>No results found for "{query}"</>
            ) : null}
          </div>
        )}

        <div className="space-y-4">
          {results.map((result, index) => (
            <div key={result._id} className="bg-white border border-gray-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-2">
                <h3 className="text-lg font-semibold text-blue-600 hover:text-blue-800">
                  <a href={result._source.url} target="_blank" rel="noopener noreferrer">
                    {result._source.title || "Untitled"}
                  </a>
                </h3>
                <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                  Score: {result._score.toFixed(2)}
                </span>
              </div>

              <p className="text-gray-600 mb-2 text-sm">
                {result._source.url}
              </p>

              {result._source.description && (
                <p className="text-gray-700 mb-3">
                  {result._source.description}
                </p>
              )}

              {result._source.metadata?.contentType && (
                <div className="flex gap-2 text-xs text-gray-500">
                  <span className="bg-gray-100 px-2 py-1 rounded">
                    {result._source.metadata.contentType}
                  </span>
                  {result._source.metadata.depth && (
                    <span className="bg-gray-100 px-2 py-1 rounded">
                      Depth: {result._source.metadata.depth}
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>

        {results.length === 0 && !loading && !error && !query && (
          <div className="text-center py-12">
            <div className="text-gray-400 mb-4">
              <svg className="mx-auto h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">Ready to Search NAB Content</h3>
            <p className="text-gray-600">
              Your OpenSearch index contains crawled pages from NAB.com.au
            </p>
          </div>
        )}
      </main>
    </div>
  );
}