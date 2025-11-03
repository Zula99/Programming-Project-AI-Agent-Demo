const API_BASE = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api`;

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
