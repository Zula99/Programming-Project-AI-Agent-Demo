
# Phased Implementation Plan - Proxy & Index Control System

## Architecture Decisions
- **Index naming**: `demo-{domain}-{run_id}` (preserves all crawls)
- **Metadata**: Dual storage (sessions + persistent files)
- **Ports**: Single port (8000) - proxy mounted as FastAPI sub-application
- **Index selection**: Always matches target_url (simplified)
- **Organization**: Enterprise structure with `API/` directory
- **Storage**: Docker bind mount to persist locally + in container
- **Proxy Architecture**: FastAPI sub-app mounted at `/proxy-api` (no separate server needed)

---

## ✅ Pre-Completed Fixes

**1. Run ID Isolation (COMPLETED)**
- **Files**: `smart_mirror_agent.py` (lines 297, 338, 391, 381, 371, 376)
- **Changes**:
  - Line 297: Hybrid crawler `output_dir` includes run_id
  - Line 338: `crawl_data["output_path"]` includes run_id
  - Line 391: Fallback crawler `output_path` includes run_id
  - Line 381: Fallback method signature accepts `run_id` parameter
  - Lines 371, 376: All fallback calls pass `run_id` parameter
- **Result**: Multiple crawls of same domain preserved in separate directories (both hybrid and fallback paths)
- **Structure**:
  ```
  output/agent_crawls/{domain}/{run_id}/run_metadata.json
  output/agent_crawls/{domain}/{run_id}/{domain}/index.html
  ```

**2. Proxy Port Configuration (COMPLETED)**
- **File**: `start_proxy.py:20`
- **Change**: Proxy port changed from 8000 → 8001
- **Note**: Will be superseded by sub-app architecture in Phase 1

**3. Debug Logging Cleanup (COMPLETED)**
- **File**: `websocket_log_handler.py:162-167`
- **Change**: Root logger set to INFO, silenced OpenSearch/urllib3 DEBUG logs
- **Result**: Clean logs without HTTP request spam

---

## PHASE 0: Docker Volume Fix ✅ COMPLETED

### 0.1 Modify `docker-compose.yml` ✅
**Issue**: Files save to `backend/output/` but Docker mounts `backend/crawl4ai-agent/output/`

**Fix Applied** (line 17):
```yaml
volumes:
  # OLD: - ./ai-agent-demo-factory-backend/crawl4ai-agent/output:/app/backend/crawl4ai-agent/output
  # NEW: Mount correct output directory
  - ./ai-agent-demo-factory-backend/output:/app/backend/output
  - ./logs:/app/backend/logs
  - ./ai-agent-demo-factory-backend:/app/backend
  - ./crawl4ai:/app/crawl4ai
```

**Result** ✅:
- Crawl data saved to `./output/agent_crawls/{domain}/{run_id}/` persists on host
- Accessible in container at `/app/backend/output/agent_crawls/`
- Works with existing code paths
- Multiple crawls preserved in separate run_id directories

**Status**: COMPLETED - Container rebuilt with correct volume mounts

---

## PHASE 1: Metadata Storage Foundation

### 1.1 Create `API/` Directory Structure
**New**: `ai-agent-demo-factory-backend/API/__init__.py` (empty file)

### 1.2 Modify `main.py` (415 → 460 lines, +45)

**Part A - Mount Proxy Sub-App** (around line 24):
```python
# Import proxy app
from Proxy.proxy_server import app as proxy_app

# Mount proxy as sub-application (after app initialization, before other routes)
app.mount("/proxy-api", proxy_app)

# Note: Proxy routes now accessible at:
# - http://localhost:8000/proxy-api/config
# - http://localhost:8000/proxy-api/auto-configure
# - http://localhost:8000/proxy/* (proxied content)
```

**Part B - Metadata Storage** (Lines 190-210 - crawl completion handler):
```python
# Import at top (around line 15)
import json
from pathlib import Path
from datetime import datetime

# After line 202 (when output_path is logged)
if output_path:
    # Store in session
    crawl4ai_sessions[run_id]["output_path"] = output_path
    crawl4ai_sessions[run_id]["domain"] = urlparse(target_url).netloc
    crawl4ai_sessions[run_id]["completed_at"] = datetime.now().isoformat()
    crawl4ai_sessions[run_id]["quality_score"] = overall_score
    crawl4ai_sessions[run_id]["pages_crawled"] = pages_crawled

    # Save run metadata to file (persists to Docker volume)
    # Note: output_path now includes run_id: ./output/agent_crawls/{domain}/{run_id}/
    metadata_file = Path(output_path) / "run_metadata.json"
    metadata = {
        "run_id": run_id,
        "target_url": target_url,
        "domain": urlparse(target_url).netloc,
        "status": "completed",
        "started_at": crawl4ai_sessions[run_id]["started_at"],
        "completed_at": datetime.now().isoformat(),
        "pages_crawled": pages_crawled,
        "quality_score": overall_score,
        "output_path": output_path
    }
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Run metadata saved to: {metadata_file}")
```

**Deliverable**:
- Every crawl creates `run_metadata.json` in output directory (persisted to host via Docker volume)
- Proxy server mounted as sub-app (always available at `/proxy-api` and `/proxy/*`, configured on-demand via UI)

**New Directory Structure** (with run_id isolation):
```
output/agent_crawls/
└── nab.com.au/
    ├── abc123/                    # run_id folder
    │   ├── run_metadata.json      # Crawl metadata
    │   └── nab.com.au/            # Crawled content
    │       ├── index.html
    │       ├── index.md
    │       └── meta.json
    └── def456/                    # Another crawl (preserved)
        ├── run_metadata.json
        └── nab.com.au/
            └── ...
```

---

## PHASE 2: Crawl Discovery System

### 2.1 Create `Utility/crawl_storage.py` (~150 lines, NEW)
**Purpose**: Scan filesystem for completed crawls

**Functions**:
```python
from pathlib import Path
from typing import List, Dict, Optional
import json
import logging

logger = logging.getLogger(__name__)

def scan_crawl_output_directory(base_path: str = "./output/agent_crawls") -> List[Dict]:
    """Scan filesystem for all crawl directories with run_metadata.json"""
    crawls = []
    base = Path(base_path)

    if not base.exists():
        logger.warning(f"Output directory not found: {base_path}")
        return crawls

    # Scan for run_metadata.json files
    for metadata_file in base.rglob("run_metadata.json"):
        metadata = get_crawl_metadata(metadata_file.parent)
        if metadata:
            crawls.append(metadata)

    return crawls

def get_crawl_metadata(output_path: Path) -> Optional[Dict]:
    """Read run_metadata.json from crawl directory"""
    metadata_file = Path(output_path) / "run_metadata.json"

    if not metadata_file.exists():
        return None

    try:
        with open(metadata_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read metadata from {metadata_file}: {e}")
        return None

def list_all_crawls(active_sessions: Dict = None) -> List[Dict]:
    """Combines filesystem scan + in-memory sessions

    Args:
        active_sessions: Optional dict of active crawl sessions (avoids circular import)
    """
    # Get all crawls from filesystem
    all_crawls = scan_crawl_output_directory()

    # Add active sessions if provided
    if active_sessions:
        for run_id, session in active_sessions.items():
            if session.get("status") in ["running", "pending"]:
                all_crawls.append({
                    "run_id": run_id,
                    "target_url": session["target_url"],
                    "domain": session.get("domain", ""),
                    "status": session["status"],
                    "started_at": session["started_at"],
                    "pages_crawled": session.get("pages_crawled", 0),
                    "output_path": session.get("output_path", "")
                })

    # Deduplicate by run_id (prefer filesystem version)
    crawls_by_id = {}
    for crawl in all_crawls:
        run_id = crawl.get("run_id")
        if run_id and (run_id not in crawls_by_id or crawl.get("status") == "completed"):
            crawls_by_id[run_id] = crawl

    # Sort by completed_at descending (most recent first)
    sorted_crawls = sorted(
        crawls_by_id.values(),
        key=lambda x: x.get("completed_at", x.get("started_at", "")),
        reverse=True
    )

    return sorted_crawls
```

### 2.2 Create `API/indexing_routes.py` (~100 lines, NEW)
**Purpose**: Endpoints for crawl listing

**Code**:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import sys
from pathlib import Path

# Add Utility to path
sys.path.insert(0, str(Path(__file__).parent.parent / "Utility"))
from crawl_storage import list_all_crawls

router = APIRouter(prefix="/api", tags=["indexing"])

@router.get("/crawls/completed")
async def get_completed_crawls():
    """List all completed crawls from filesystem + sessions"""
    try:
        # Import sessions inside function to avoid circular dependency
        from main import crawl4ai_sessions

        # Pass sessions as parameter (avoids circular import at module level)
        crawls = list_all_crawls(active_sessions=crawl4ai_sessions)
        return {"crawls": crawls, "count": len(crawls)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list crawls: {str(e)}")
```

### 2.3 Modify `main.py` (460 → 465 lines, +5)
**Location**: After proxy sub-app mount (around line 52)

**Changes**:
```python
# Import router
from API.indexing_routes import router as indexing_router

# Include router (after proxy mount)
app.include_router(indexing_router)
```

**Deliverable**: `GET /api/crawls/completed` returns all crawls with run_id and domain

**Test**:
```bash
curl http://localhost:8000/api/crawls/completed
```

---

## PHASE 3: Manual Indexing with Progress

### 3.1 Modify `opensearch_integration.py` (787 → 850 lines, +60)
**Location**: Add after `get_index_stats()` method (around line 475)

**New methods**:
```python
def list_all_indexes(self, pattern: str = "demo-*") -> List[Dict]:
    """List all indexes matching pattern with metadata"""
    try:
        # Get all indexes matching pattern
        indices = self.client.cat.indices(index=pattern, format="json")

        results = []
        for idx in indices:
            results.append({
                "name": idx["index"],
                "doc_count": int(idx.get("docs.count", 0)),
                "size_bytes": idx.get("store.size", "0b"),
                "status": idx.get("health", "unknown")
            })

        return results
    except Exception as e:
        logger.error(f"Failed to list indexes: {e}")
        return []

def get_all_demo_indexes(self) -> List[Dict]:
    """Get all demo-* indexes with parsed metadata"""
    indexes = self.list_all_indexes("demo-*")

    # Parse index names to extract domain and run_id
    for idx in indexes:
        name = idx["name"]
        # Format: demo-domain_com-run_id
        if name.startswith("demo-"):
            parts = name[5:].split("-")
            if len(parts) >= 2:
                idx["domain"] = parts[0].replace("_", ".")
                idx["run_id"] = "-".join(parts[1:])

    return indexes

def index_exists(self, index_name: str) -> bool:
    """Check if index exists"""
    try:
        return self.client.indices.exists(index=index_name)
    except Exception as e:
        logger.error(f"Failed to check index existence: {e}")
        return False
```

### 3.2 Modify `API/indexing_routes.py` (~100 → 250 lines, +150)
**Purpose**: Add indexing endpoint with WebSocket logging

**New code**:
```python
from websocket_log_handler import current_run_id
from opensearch_integration import Crawl4AIOpenSearchIntegration, OpenSearchConfig
import logging

class IndexRequest(BaseModel):
    run_id: str
    output_path: str
    domain: str

@router.post("/opensearch/index")
async def index_crawl_data(request: IndexRequest):
    """Index crawl data to OpenSearch with progress logging"""
    try:
        # Set logging context for WebSocket (shows in backend logs)
        current_run_id.set(request.run_id)
        logger = logging.getLogger("opensearch_indexing")

        # Create index name: demo-{domain}-{run_id}
        domain_clean = request.domain.replace(".", "_")
        index_name = f"demo-{domain_clean}-{request.run_id}"

        logger.info(f"Starting OpenSearch indexing: {index_name}")
        logger.info(f"Source: {request.output_path}")

        # Initialize OpenSearch
        config = OpenSearchConfig(host="opensearch-demo", port=9200, scheme="http")
        opensearch = Crawl4AIOpenSearchIntegration(config)

        # Check if index already exists
        if opensearch.index_exists(index_name):
            logger.warning(f"Index {index_name} already exists - will append data")

        # Index data (index_crawl4ai_data logs progress automatically)
        stats = opensearch.index_crawl4ai_data(
            crawl_output_dir=request.output_path,
            index_name=index_name,
            batch_size=100
        )

        logger.info(f"Indexing complete!")
        logger.info(f"  Documents indexed: {stats.get('documents_indexed', 0)}")
        logger.info(f"  Duration: {stats.get('duration', 0):.2f}s")
        logger.info(f"  Errors: {stats.get('errors', 0)}")

        return {
            "index_name": index_name,
            "stats": stats,
            "message": f"Successfully indexed {stats.get('documents_indexed', 0)} documents"
        }

    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Indexing failed: {str(e)}")

@router.get("/opensearch/indexes")
async def get_opensearch_indexes():
    """List all OpenSearch demo indexes"""
    try:
        config = OpenSearchConfig(host="opensearch-demo", port=9200, scheme="http")
        opensearch = Crawl4AIOpenSearchIntegration(config)
        indexes = opensearch.get_all_demo_indexes()

        return {"indexes": indexes, "count": len(indexes)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list indexes: {str(e)}")
```

**Deliverable**:
- `POST /api/opensearch/index` indexes crawl with backend log progress
- `GET /api/opensearch/indexes` lists all indexed crawls

**Test**:
```bash
# Index a crawl
curl -X POST http://localhost:8000/api/opensearch/index \
  -H "Content-Type: application/json" \
  -d '{"run_id":"abc123","output_path":"./output/agent_crawls/nab.com.au","domain":"nab.com.au"}'

# List indexes
curl http://localhost:8000/api/opensearch/indexes
```

---

## PHASE 4: Proxy Control Endpoints

### 4.1 Modify `API/indexing_routes.py` (~250 → 350 lines, +100)
**Purpose**: Proxy control via HTTP to proxy sub-app (mounted at /proxy-api)

**Add to top**:
```python
import httpx
from urllib.parse import urlparse

# Proxy is mounted as sub-app at /proxy-api (same port as main app)
PROXY_SERVER_URL = "http://localhost:8000/proxy-api"
```

**New models**:
```python
class ProxyLaunchRequest(BaseModel):
    target_url: str
    run_id: str
```

**New endpoints**:
```python
@router.post("/proxy/launch")
async def launch_proxy(request: ProxyLaunchRequest):
    """Launch proxy server with target URL and index"""
    try:
        # Generate index name from run_id (matches indexing naming)
        domain = urlparse(request.target_url).netloc
        domain_clean = domain.replace(".", "_")
        index_name = f"demo-{domain_clean}-{request.run_id}"

        # Call proxy_server's /auto-configure endpoint (port 8001)
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{PROXY_SERVER_URL}/auto-configure",
                json={
                    "target_url": request.target_url,
                    "run_id": request.run_id,
                    "enabled": True
                }
            )
            response.raise_for_status()

        logger = logging.getLogger("proxy")
        logger.info(f"Proxy launched: {request.target_url} → {index_name}")

        return {
            "message": "Proxy launched successfully",
            "proxy_url": "http://localhost:8000/proxy/",
            "target_url": request.target_url,
            "index_name": index_name
        }

    except httpx.HTTPError as e:
        raise HTTPException(status_code=503, detail=f"Proxy server unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch proxy: {str(e)}")

@router.post("/proxy/stop")
async def stop_proxy():
    """Stop proxy server"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{PROXY_SERVER_URL}/auto-configure",
                json={"target_url": "", "enabled": False}
            )
            response.raise_for_status()

        return {"message": "Proxy stopped"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop proxy: {str(e)}")

@router.get("/proxy/status")
async def get_proxy_status():
    """Get proxy server status"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{PROXY_SERVER_URL}/config")
            response.raise_for_status()
            return response.json()

    except httpx.HTTPError:
        return {
            "enabled": False,
            "target_url": None,
            "message": "Proxy server not running"
        }
```

**Deliverable**:
- `POST /api/proxy/launch` configures proxy (already running as sub-app on port 8000)
- `GET /api/proxy/status` checks proxy state
- Proxy serves content at `http://localhost:8000/proxy/`

**Test**:
```bash
# Check status
curl http://localhost:8000/api/proxy/status

# Launch proxy
curl -X POST http://localhost:8000/api/proxy/launch \
  -H "Content-Type: application/json" \
  -d '{"target_url":"https://nab.com.au","run_id":"abc123"}'
```

---

## PHASE 5: Frontend Implementation

### 5.1 Create `lib/indexing-api.ts` (~100 lines, NEW)
**Purpose**: API client functions

**Code**:
```typescript
const API_BASE = 'http://localhost:8000/api';

export interface CompletedCrawl {
  run_id: string;
  target_url: string;
  domain: string;
  status: string;
  started_at: string;
  completed_at?: string;
  pages_crawled: number;
  quality_score?: number;
  output_path: string;
}

export interface OpenSearchIndex {
  name: string;
  domain: string;
  run_id: string;
  doc_count: number;
  size_bytes: string;
  status: string;
}

export async function getCompletedCrawls(): Promise<CompletedCrawl[]> {
  const response = await fetch(`${API_BASE}/crawls/completed`);
  if (!response.ok) throw new Error('Failed to fetch completed crawls');
  const data = await response.json();
  return data.crawls;
}

export async function indexCrawl(runId: string, outputPath: string, domain: string) {
  const response = await fetch(`${API_BASE}/opensearch/index`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ run_id: runId, output_path: outputPath, domain })
  });
  if (!response.ok) throw new Error('Failed to index crawl');
  return await response.json();
}

export async function getOpenSearchIndexes(): Promise<OpenSearchIndex[]> {
  const response = await fetch(`${API_BASE}/opensearch/indexes`);
  if (!response.ok) throw new Error('Failed to fetch indexes');
  const data = await response.json();
  return data.indexes;
}

export async function launchProxy(targetUrl: string, runId: string) {
  const response = await fetch(`${API_BASE}/proxy/launch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ target_url: targetUrl, run_id: runId })
  });
  if (!response.ok) throw new Error('Failed to launch proxy');
  return await response.json();
}

export async function stopProxy() {
  const response = await fetch(`${API_BASE}/proxy/stop`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to stop proxy');
  return await response.json();
}

export async function getProxyStatus() {
  const response = await fetch(`${API_BASE}/proxy/status`);
  if (!response.ok) throw new Error('Failed to get proxy status');
  return await response.json();
}
```

### 5.2 Create `components/IndexControlPanel.tsx` (~220 lines, NEW)
**Purpose**: Manual indexing UI

**Code**:
```tsx
'use client'

import { useState, useEffect } from 'react';
import { getCompletedCrawls, indexCrawl, type CompletedCrawl } from '@/lib/indexing-api';

export default function IndexControlPanel() {
  const [crawls, setCrawls] = useState<CompletedCrawl[]>([]);
  const [selectedCrawl, setSelectedCrawl] = useState<string>('');
  const [indexing, setIndexing] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  useEffect(() => {
    loadCrawls();
  }, []);

  const loadCrawls = async () => {
    try {
      const data = await getCompletedCrawls();
      setCrawls(data);
    } catch (error) {
      console.error('Failed to load crawls:', error);
    }
  };

  const handleIndex = async () => {
    if (!selectedCrawl) {
      setMessage({type: 'error', text: 'Please select a crawl'});
      return;
    }

    const crawl = crawls.find(c => c.run_id === selectedCrawl);
    if (!crawl) return;

    setIndexing(true);
    setMessage(null);

    try {
      const result = await indexCrawl(crawl.run_id, crawl.output_path, crawl.domain);
      setMessage({
        type: 'success',
        text: `Indexed as ${result.index_name} (${result.stats.documents_indexed} docs)`
      });
    } catch (error) {
      setMessage({type: 'error', text: `Indexing failed: ${error}`});
    } finally {
      setIndexing(false);
    }
  };

  const selectedCrawlData = crawls.find(c => c.run_id === selectedCrawl);

  return (
    <div className="bg-white rounded-lg shadow p-6 mt-6">
      <h2 className="text-xl font-semibold mb-4">Index Control</h2>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Select crawl to index:
        </label>
        <select
          value={selectedCrawl}
          onChange={(e) => setSelectedCrawl(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2"
          disabled={indexing}
        >
          <option value="">-- Select a crawl --</option>
          {crawls.map((crawl) => (
            <option key={crawl.run_id} value={crawl.run_id}>
              {crawl.domain} - {crawl.run_id.substring(0, 8)} ({crawl.pages_crawled} pages, {crawl.status})
            </option>
          ))}
        </select>
      </div>

      {selectedCrawlData && (
        <div className="bg-gray-50 rounded-lg p-4 mb-4 text-sm">
          <div><strong>Domain:</strong> {selectedCrawlData.domain}</div>
          <div><strong>Pages:</strong> {selectedCrawlData.pages_crawled}</div>
          <div><strong>Quality:</strong> {selectedCrawlData.quality_score?.toFixed(1)}%</div>
          <div><strong>Status:</strong> {selectedCrawlData.status}</div>
        </div>
      )}

      <button
        onClick={handleIndex}
        disabled={!selectedCrawl || indexing}
        className="w-full bg-indigo-600 text-white rounded-lg px-4 py-2 hover:bg-indigo-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
      >
        {indexing ? 'Indexing... (check backend logs)' : 'Index to OpenSearch'}
      </button>

      {message && (
        <div className={`mt-4 p-3 rounded-lg ${
          message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
        }`}>
          {message.text}
        </div>
      )}
    </div>
  );
}
```

### 5.3 Create `components/ProxyControlPanel.tsx` (~200 lines, NEW)
**Purpose**: Proxy launch UI

**Code**:
```tsx
'use client'

import { useState, useEffect } from 'react';
import { getOpenSearchIndexes, launchProxy, stopProxy, getProxyStatus, type OpenSearchIndex } from '@/lib/indexing-api';

export default function ProxyControlPanel() {
  const [indexes, setIndexes] = useState<OpenSearchIndex[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<string>('');
  const [targetUrl, setTargetUrl] = useState<string>('');
  const [proxyActive, setProxyActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{type: 'success' | 'error', text: string} | null>(null);

  useEffect(() => {
    loadIndexes();
    checkProxyStatus();
  }, []);

  const loadIndexes = async () => {
    try {
      const data = await getOpenSearchIndexes();
      setIndexes(data);
    } catch (error) {
      console.error('Failed to load indexes:', error);
    }
  };

  const checkProxyStatus = async () => {
    try {
      const status = await getProxyStatus();
      setProxyActive(status.enabled || false);
      if (status.target_url) setTargetUrl(status.target_url);
    } catch (error) {
      setProxyActive(false);
    }
  };

  const handleLaunch = async () => {
    if (!selectedIndex || !targetUrl) {
      setMessage({type: 'error', text: 'Please select index and enter target URL'});
      return;
    }

    const index = indexes.find(i => i.name === selectedIndex);
    if (!index) return;

    setLoading(true);
    setMessage(null);

    try {
      const result = await launchProxy(targetUrl, index.run_id);
      setProxyActive(true);
      setMessage({
        type: 'success',
        text: `Proxy launched: ${result.proxy_url}`
      });
    } catch (error) {
      setMessage({type: 'error', text: `Failed to launch proxy: ${error}`});
    } finally {
      setLoading(false);
    }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      await stopProxy();
      setProxyActive(false);
      setMessage({type: 'success', text: 'Proxy stopped'});
    } catch (error) {
      setMessage({type: 'error', text: `Failed to stop proxy: ${error}`});
    } finally {
      setLoading(false);
    }
  };

  const selectedIndexData = indexes.find(i => i.name === selectedIndex);

  // Auto-fill target URL when index is selected
  useEffect(() => {
    if (selectedIndexData && !targetUrl) {
      setTargetUrl(`https://${selectedIndexData.domain}`);
    }
  }, [selectedIndexData]);

  return (
    <div className="bg-white rounded-lg shadow p-6 mt-6">
      <h2 className="text-xl font-semibold mb-4">Proxy Control</h2>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Target Site:
        </label>
        <input
          type="text"
          value={targetUrl}
          onChange={(e) => setTargetUrl(e.target.value)}
          placeholder="https://example.com"
          className="w-full border border-gray-300 rounded-lg px-3 py-2"
          disabled={loading || proxyActive}
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Search Index:
        </label>
        <select
          value={selectedIndex}
          onChange={(e) => setSelectedIndex(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2"
          disabled={loading || proxyActive}
        >
          <option value="">-- Select indexed crawl --</option>
          {indexes.map((index) => (
            <option key={index.name} value={index.name}>
              {index.domain} - {index.run_id.substring(0, 8)} ({index.doc_count} docs)
            </option>
          ))}
        </select>
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleLaunch}
          disabled={loading || proxyActive || !selectedIndex || !targetUrl}
          className="flex-1 bg-green-600 text-white rounded-lg px-4 py-2 hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {loading ? 'Launching...' : 'Start Proxy'}
        </button>

        <button
          onClick={handleStop}
          disabled={loading || !proxyActive}
          className="flex-1 bg-red-600 text-white rounded-lg px-4 py-2 hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          Stop Proxy
        </button>
      </div>

      {proxyActive && (
        <div className="mt-4 bg-green-50 border border-green-200 rounded-lg p-3">
          <div className="text-sm font-medium text-green-800 mb-1">Proxy Active</div>
          <a
            href="http://localhost:8000/proxy/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline text-sm"
          >
            http://localhost:8000/proxy/
          </a>
        </div>
      )}

      {message && (
        <div className={`mt-4 p-3 rounded-lg ${
          message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
        }`}>
          {message.text}
        </div>
      )}
    </div>
  );
}
```

### 5.4 Modify `app/crawl4ai/page.tsx` (~200 → 260 lines, +60)
**Purpose**: Add new panels

**Changes**:
```tsx
// Add imports
import IndexControlPanel from "@/components/IndexControlPanel";
import ProxyControlPanel from "@/components/ProxyControlPanel";

// In the return JSX, add after CrawlProgressPanel and before BackendLogsDropdown:
export default function Crawl4AIPage() {
  // ... existing code ...

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <Header />
      <Crawl4AIUrlBar onStartCrawl={handleStartCrawl} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-6">
        <div className="lg:col-span-2">
          <AgentOutputCard
            status={status}
            logs={logs}
            onStopCrawl={handleStopCrawl}
          />
          <CrawlProgressPanel progress={progress} isConnected={isConnected} />

          {/* NEW PANELS */}
          <IndexControlPanel />
          <ProxyControlPanel />
        </div>

        <div className="lg:col-span-1">
          <BackendLogsDropdown logs={backendLogs} />
        </div>
      </div>
    </main>
  );
}
```

---

## File Summary

### New Files (6):
1. `API/__init__.py` - 0 lines
2. `API/indexing_routes.py` - 350 lines
3. `Utility/crawl_storage.py` - 150 lines
4. `frontend/lib/indexing-api.ts` - 100 lines
5. `frontend/components/IndexControlPanel.tsx` - 220 lines
6. `frontend/components/ProxyControlPanel.tsx` - 200 lines

### Modified Files (4):
1. `docker-compose.yml` - Fix volume mount (line 17)
2. `main.py` - +50 lines (415 → 465) - includes proxy sub-app mounting + metadata storage + router
3. `opensearch_integration.py` - +60 lines (787 → 850)
4. `app/crawl4ai/page.tsx` - +60 lines (200 → 260)

**Total**: ~1190 new lines, all files stay under 500 lines ✅

---

## Implementation Order

**Phase 0** ✅ COMPLETED: Docker volume fix + Run ID isolation
**Phase 1** (30 min): Metadata storage + Proxy sub-app mounting
**Phase 2** (45 min): Crawl listing → Verify API returns data
**Phase 3** (1 hour): Manual indexing → Test indexing + logs
**Phase 4** (45 min): Proxy control → Test proxy launch
**Phase 5** (1.5 hours): Frontend → Full UI integration

**Total Remaining**: ~4 hours of incremental development

---

## Testing Checklist

- [x] Phase 0: Docker volume persists crawl data to host with run_id isolation
- [ ] Phase 1: run_metadata.json created in `output/agent_crawls/{domain}/{run_id}/`
- [ ] Phase 1: Proxy sub-app accessible at `/proxy-api` and `/proxy/`
- [ ] Phase 2: GET /api/crawls/completed returns crawls with run_id
- [ ] Phase 3: POST /api/opensearch/index creates index
- [ ] Phase 3: Backend logs show indexing progress
- [ ] Phase 4: POST /api/proxy/launch configures proxy (sub-app on port 8000)
- [ ] Phase 4: Proxy serves content at `http://localhost:8000/proxy/`
- [ ] Phase 5: Frontend dropdowns populate correctly
- [ ] Phase 5: Proxy URL opens proxied site with search