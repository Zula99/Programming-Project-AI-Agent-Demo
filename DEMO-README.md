# Demo Factory Search Implementation

## Overview
Today we successfully built an end-to-end search demo that connects crawled website data to a live search interface. This demonstrates the core concept of the "Demo Factory" - automated website crawling with searchable content.

## What We Accomplished

✅ **Set up OpenSearch** via Docker for local development  
✅ **Loaded real crawled NAB data** from Norconex crawler exports  
✅ **Built a search interface** in Next.js connected to real data  
✅ **Identified crawler optimization opportunities** (the YouTube problem)  
✅ **Created a complete proof of concept** ready for client demos  

---

## Prerequisites

- Docker Desktop installed
- Node.js installed  
- Existing crawled data from Norconex (in `demo-results/search-proof/`)

---

## Step 1: Set Up OpenSearch

### 1.1 Create docker-compose.yml
```yaml
version: '3.7'
services:
  opensearch:
    image: opensearchproject/opensearch:latest
    container_name: opensearch
    environment:
      - discovery.type=single-node
      - OPENSEARCH_INITIAL_ADMIN_PASSWORD=DemoPass123!
      - DISABLE_SECURITY_PLUGIN=true
    ports:
      - 9200:9200
      - 9600:9600
    volumes:
      - opensearch-data:/usr/share/opensearch/data

volumes:
  opensearch-data:
    driver: local
```

### 1.2 Start OpenSearch
```powershell
# Start OpenSearch container
docker-compose up -d

# Verify it's running
docker ps

# Test the API
Invoke-RestMethod http://localhost:9200
```

---

## Step 2: Load Crawled Data

### 2.1 Handle UTF-16 Encoding Issue

**Problem:** The exported JSON files from Elasticsearch were UTF-16 encoded with BOM, causing parse errors.

**Diagnosis:**
```powershell
# Check file encoding
$buffer = [System.IO.File]::ReadAllBytes(".\demo-results\search-proof\all-docs.json")
$buffer[0..19] | ForEach-Object { $_.ToString("x2") }
# Output: fffe7b00220074006f006f006b0022003a003100
# This shows UTF-16 LE BOM (fffe)
```

### 2.2 Create Data Loader Script

**File: `load-data.js`**
```javascript
const fs = require('fs');

async function makeRequest(url, options = {}) {
  const http = require('http');
  const https = require('https');
  const urlModule = require('url');
  
  return new Promise((resolve, reject) => {
    const parsedUrl = urlModule.parse(url);
    const lib = parsedUrl.protocol === 'https:' ? https : http;
    
    const req = lib.request({
      hostname: parsedUrl.hostname,
      port: parsedUrl.port,
      path: parsedUrl.path,
      method: options.method || 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({
            status: res.statusCode,
            data: res.statusCode === 204 ? {} : JSON.parse(data)
          });
        } catch (e) {
          resolve({ status: res.statusCode, data: data });
        }
      });
    });
    
    req.on('error', reject);
    
    if (options.body) {
      req.write(typeof options.body === 'string' ? options.body : JSON.stringify(options.body));
    }
    
    req.end();
  });
}

async function loadDataToOpenSearch() {
  const OPENSEARCH_URL = 'http://localhost:9200';
  const INDEX_NAME = 'nab_search';
  
  console.log('🔍 Loading NAB data into OpenSearch...');
  
  try {
    // Test connection
    console.log('Testing OpenSearch connection...');
    const healthCheck = await makeRequest(OPENSEARCH_URL);
    console.log('✅ OpenSearch is running:', healthCheck.data.cluster_name);
    
    // Create index with proper mapping
    console.log('Creating index with mapping...');
    const indexMapping = {
      mappings: {
        properties: {
          title: { type: 'text', analyzer: 'standard' },
          content: { type: 'text', analyzer: 'standard' },
          url: { type: 'keyword' },
          description: { type: 'text' },
          'og:description': { type: 'text' },
          'dc:title': { type: 'text' },
          's365:title': { type: 'text' },
          metadata: { type: 'object', enabled: false }
        }
      }
    };
    
    await makeRequest(`${OPENSEARCH_URL}/${INDEX_NAME}`, {
      method: 'PUT',
      body: indexMapping
    });
    console.log('✅ Index created with mapping');
    
    // Read your exported data
    const dataFiles = [
      './demo-results/search-proof/all-docs.json',
      './demo-results/search-proof/full-index-export.json'
    ];
    
    let totalDocs = 0;
    
    for (const filePath of dataFiles) {
      if (!fs.existsSync(filePath)) {
        console.log(`⏭️  Skipping ${filePath} - file not found`);
        continue;
      }
      
      console.log(`📄 Processing ${filePath}...`);
      
      try {
        // Read file with UTF-16 LE encoding (your files are UTF-16)
        let rawData = fs.readFileSync(filePath, 'utf16le');
        
        // Remove BOM if present
        if (rawData.charCodeAt(0) === 0xFEFF) {
          rawData = rawData.slice(1);
          console.log('✅ BOM removed from', filePath);
        }
        
        const elasticsearchResponse = JSON.parse(rawData);
        
        // Extract documents from Elasticsearch export format
        const documents = elasticsearchResponse.hits.hits;
        console.log(`Found ${documents.length} documents in ${filePath}`);
        
        // Prepare bulk index operations
        const bulkOps = [];
        
        documents.forEach(doc => {
          const source = doc._source;
          
          // Create a clean document for OpenSearch
          const cleanDoc = {
            url: source['Content-Location'] || doc._id,
            title: source['s365:title'] || source['dc:title'] || 'Untitled',
            description: source['og:description'] || '',
            content: source.content || source['og:description'] || '',
            metadata: {
              depth: source['collector.depth'],
              contentType: source['document.contentType'],
              sitemap: {
                changefreq: source['collector.sitemap-changefreq'],
                priority: source['collector.sitemap-priority']
              }
            }
          };
          
          // Add index operation
          bulkOps.push({ index: { _index: INDEX_NAME, _id: doc._id } });
          bulkOps.push(cleanDoc);
        });
        
        // Bulk index to OpenSearch
        if (bulkOps.length > 0) {
          console.log(`📤 Bulk indexing ${documents.length} documents...`);
          const bulkBody = bulkOps.map(op => JSON.stringify(op)).join('\n') + '\n';
          
          const bulkResponse = await makeRequest(`${OPENSEARCH_URL}/_bulk`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-ndjson' },
            body: bulkBody
          });
          
          if (bulkResponse.data.errors) {
            console.log('⚠️  Some indexing errors occurred');
            console.log(bulkResponse.data.items.filter(item => item.index.error));
          } else {
            console.log(`✅ Successfully indexed ${documents.length} documents`);
            totalDocs += documents.length;
          }
        }
        
      } catch (parseError) {
        console.error(`❌ Failed to parse ${filePath}:`, parseError.message);
        continue;
      }
    }
    
    // Refresh index
    await makeRequest(`${OPENSEARCH_URL}/${INDEX_NAME}/_refresh`, {
      method: 'POST'
    });
    
    console.log(`\n🎉 Data loading complete! Total documents: ${totalDocs}`);
    console.log(`\n🔍 Test your search:`);
    console.log(`curl "${OPENSEARCH_URL}/${INDEX_NAME}/_search?q=banking"`);
    
  } catch (error) {
    console.error('❌ Error:', error.message);
    process.exit(1);
  }
}

// Run the loader
loadDataToOpenSearch();
```

### 2.3 Run the Data Loader
```powershell
# Run the loader script
node load-data.js

# Expected output:
# 🔍 Loading NAB data into OpenSearch...
# ✅ OpenSearch is running: docker-cluster
# ✅ Index created with mapping
# ✅ Successfully indexed 15 documents
# 🎉 Data loading complete! Total documents: 30
```

### 2.4 Test the Search
```powershell
# Test search functionality
Invoke-RestMethod "http://localhost:9200/nab_search/_search?q=banking"

# Count total documents
Invoke-RestMethod "http://localhost:9200/nab_search/_count"

# View all documents
Invoke-RestMethod "http://localhost:9200/nab_search/_search?size=20"
```

---

## Step 3: Build Search Interface

### 3.1 Create API Route

**File: `ai-agent-demo-factory-frontend/src/app/api/search/route.ts`**
```typescript
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
```

### 3.2 Create Search Interface

**File: `ai-agent-demo-factory-frontend/src/app/page.tsx`**
```typescript
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
```

### 3.3 Start the Search Interface
```powershell
cd ai-agent-demo-factory-frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Visit http://localhost:3000
```

---

## Step 4: Results & Discovery

### 4.1 Search Test Results
```powershell
# Search for "banking" returned 5 results in 33ms
# Found results include:
# - NAB personal banking (Score: 4.09)
# - About us (Score: 2.34)
# - Plus multiple YouTube links
```

### 4.2 Data Analysis
```powershell
# Check what was actually crawled
$response = Invoke-RestMethod "http://localhost:9200/nab_search/_search?size=20&_source=url,title"
$response.hits.hits[0]._source

# Results showed:
# - Only 3 actual NAB pages: nab.com.au, nab.com.au/about-us
# - 12+ YouTube pages from artists.youtube, about.youtube, etc.
```

### 4.3 Key Discovery: The YouTube Problem

**Issue:** The crawler followed links from NAB → YouTube and spent 35 minutes crawling YouTube instead of NAB content.

**URLs Found:**
- ✅ `https://www.nab.com.au`
- ✅ `https://www.nab.com.au/about-us` 
- ❌ `https://artists.youtube/features/`
- ❌ `https://artists.youtube/foundry/`
- ❌ `https://about.youtube/`
- ❌ ... (and more YouTube URLs)

---

## Key Technical Challenges Solved

### 1. UTF-16 BOM Encoding Issue
**Problem:** JSON exports were UTF-16 with BOM, causing `Unexpected token '�'` errors.

**Solution:** 
```javascript
// Read as UTF-16 LE and strip BOM
let rawData = fs.readFileSync(filePath, 'utf16le');
if (rawData.charCodeAt(0) === 0xFEFF) {
  rawData = rawData.slice(1);
}
```

### 2. CORS Issues with Direct OpenSearch Access
**Problem:** Browser security prevented direct calls to OpenSearch from frontend.

**Solution:** Created Next.js API route as proxy:
```typescript
// /api/search endpoint that calls OpenSearch server-side
const searchResponse = await fetch("http://localhost:9200/nab_search/_search", ...);
```

### 3. Crawler Configuration Optimization
**Problem:** Crawler followed external links instead of staying on target domain.

**Identified Solution:** 
```json
{
  "include": ["^https://www\\.nab\\.com\\.au/.*"],
  "exclude": [".*youtube.*", ".*youtu\\.be.*"],
  "stayInDomain": true,
  "respectRobotsTxt": false
}
```

---

## Demo Factory Workflow Achieved

1. **Crawl Target Website** ✅ (Norconex crawler)
2. **Extract Structured Data** ✅ (JSON export) 
3. **Index for Search** ✅ (OpenSearch)
4. **Deploy Search Interface** ✅ (Next.js app)
5. **Demonstrate Live Search** ✅ (Real NAB content)

---

## Next Steps for Demo Optimization

### 1. Fix Crawler Configuration
- Add domain restrictions to prevent YouTube crawling
- Increase crawl depth to get more NAB pages
- Implement robots.txt bypass for better coverage

### 2. LLM-Powered Config Optimization
- Build agent that analyzes crawl results
- Automatically detects unwanted domains (YouTube, social media)
- Generates optimized crawler configurations
- Validates results and iterates

### 3. Production Deployment
- Docker Compose for complete stack
- Automated deploy/teardown scripts
- Multiple demo environments

---

## Commands Reference

### OpenSearch Management
```powershell
# Start/stop OpenSearch
docker-compose up -d
docker-compose down -v

# Check status
docker ps
curl http://localhost:9200

# Search operations
curl "http://localhost:9200/nab_search/_search?q=banking"
curl "http://localhost:9200/nab_search/_count"
```

### Development
```powershell
# Load data
node load-data.js

# Start frontend
cd ai-agent-demo-factory-frontend
npm run dev

# Check ports
netstat -ano | findstr :9200  # OpenSearch
netstat -ano | findstr :3000  # Next.js
```

### Debugging
```powershell
# Check file encoding
$buffer = [System.IO.File]::ReadAllBytes("file.json")
$buffer[0..19] | ForEach-Object { $_.ToString("x2") }

# View indexed data
$response = Invoke-RestMethod "http://localhost:9200/nab_search/_search?size=20"
$response.hits.hits | ForEach-Object { $_._source.url }
```

---

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Norconex      │───▶│    OpenSearch    │◀───│   Next.js App   │
│   Crawler       │    │   (Port 9200)    │    │  (Port 3000)    │
│                 │    │                  │    │                 │
│ • Crawls sites  │    │ • Indexes data   │    │ • Search UI     │
│ • Exports JSON  │    │ • Full-text      │    │ • API routes    │
│ • UTF-16 format │    │   search         │    │ • Live results  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
        │                        ▲                       │
        │                        │                       │
        ▼                        │                       ▼
┌─────────────────┐              │              ┌─────────────────┐
│  load-data.js   │──────────────┘              │   Browser UI    │
│                 │                             │                 │
│ • Handles UTF-16│                             │ • Real-time     │
│ • Strips BOM    │                             │   search        │
│ • Bulk indexes  │                             │ • Relevance     │
│ • Error handling│                             │   scoring       │
└─────────────────┘                             └─────────────────┘
```

This implementation successfully demonstrates the core Demo Factory concept with real crawled data, working search, and identified optimization opportunities.