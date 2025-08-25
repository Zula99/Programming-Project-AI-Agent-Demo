'use client';

import { useState, useEffect } from 'react';
import StatusBadge from './StatusBadge';

interface SearchHit {
  _index: string;
  _id: string;
  _score: number;
  _source: {
    title?: string;
    description?: string;
    content?: string;
    url?: string;
    lastModified?: string;
    contentType?: string;
    size?: number;
  };
  highlight?: {
    title?: string[];
    description?: string[];
    content?: string[];
  };
}

interface SearchResponse {
  hits: {
    total: { value: number; relation: string };
    hits: SearchHit[];
  };
}

export default function SearchResults() {
  const [searchResults, setSearchResults] = useState<SearchHit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchNABData = async (query: string = '') => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: query || undefined,
          matchAll: !query,
          size: 5000
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data: SearchResponse = await response.json();
      setSearchResults(data.hits.hits);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNABData();
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    fetchNABData(searchQuery);
  };

  const formatSize = (bytes?: number) => {
    if (!bytes) return 'Unknown';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  const getHighlightedContent = (hit: SearchHit, field: string) => {
    const highlight = hit.highlight?.[field as keyof typeof hit.highlight];
    if (highlight && highlight.length > 0) {
      return { __html: highlight[0] };
    }
    return null;
  };

  return (
    <div className="bg-white p-6 rounded-lg border">
      <div className="mb-4">
        <h2 className="text-xl font-medium mb-4">Crawled Data from OpenSearch</h2>
        
        <form onSubmit={handleSearch} className="mb-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search crawled data..."
              className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              type="submit"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Search
            </button>
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                fetchNABData();
              }}
              className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-500"
            >
              Show All
            </button>
          </div>
        </form>
      </div>

      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="text-gray-500">Loading crawled data...</div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
          <strong>Error:</strong> {error}
          <br />
          <small>Make sure OpenSearch is running and the search index exists.</small>
        </div>
      )}

      {!loading && !error && (
        <div>
          <div className="mb-4 text-sm text-gray-600">
            Found {searchResults.length} documents
          </div>
          
          {searchResults.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No data found. Try starting a new crawl or make sure crawl data is loaded into OpenSearch.
            </div>
          ) : (
            <div className="space-y-4">
              {searchResults.map((hit) => (
                <div key={hit._id} className="border rounded-lg p-4 hover:bg-gray-50">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <h3 className="font-medium text-blue-600 hover:underline cursor-pointer">
                        {getHighlightedContent(hit, 'title') ? (
                          <span dangerouslySetInnerHTML={getHighlightedContent(hit, 'title')!} />
                        ) : (
                          hit._source.title || 'Untitled'
                        )}
                      </h3>
                      {hit._source.url && (
                        <p className="text-sm text-green-600 mt-1">{hit._source.url}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 ml-4">
                      <span className="text-xs text-gray-500">Score: {hit._score.toFixed(2)}</span>
                      <StatusBadge status="complete" />
                    </div>
                  </div>
                  
                  {(hit._source.description || getHighlightedContent(hit, 'description')) && (
                    <div className="mb-2">
                      {getHighlightedContent(hit, 'description') ? (
                        <p 
                          className="text-sm text-gray-700"
                          dangerouslySetInnerHTML={getHighlightedContent(hit, 'description')!}
                        />
                      ) : (
                        <p className="text-sm text-gray-700">{hit._source.description}</p>
                      )}
                    </div>
                  )}
                  
                  {getHighlightedContent(hit, 'content') && (
                    <div className="mb-2">
                      <p 
                        className="text-sm text-gray-600 italic"
                        dangerouslySetInnerHTML={getHighlightedContent(hit, 'content')!}
                      />
                    </div>
                  )}
                  
                  <div className="flex justify-between items-center text-xs text-gray-500 mt-3">
                    <div className="flex gap-4">
                      {hit._source.contentType && (
                        <span>Type: {hit._source.contentType}</span>
                      )}
                      {hit._source.size && (
                        <span>Size: {formatSize(hit._source.size)}</span>
                      )}
                      {hit._source.lastModified && (
                        <span>Modified: {new Date(hit._source.lastModified).toLocaleDateString()}</span>
                      )}
                    </div>
                    <span>ID: {hit._id}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}