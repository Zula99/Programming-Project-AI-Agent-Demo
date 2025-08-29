'use client';

import { useState } from 'react';
import StatusBadge from './StatusBadge';

interface CrawlStats {
  total_pages_crawled: number;
  pages_indexed: number;
  pages_fetched: number;
  pages_processed: number;
  pages_queued: number;
  pages_rejected: number;
  pages_skipped: number;
  total_size_bytes: number;
  avg_page_size_bytes: number;
  crawl_duration_seconds: number;
  norconex_duration_seconds: number;
  domains_found: string[];
  file_types: Record<string, number>;
  max_depth_reached: number;
  errors_encountered: number;
  urls_extracted: number;
  avg_throughput: number;
}

interface CrawlJob {
  run_id: string;
  target_url: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  progress: number;
  started_at: number;
  completed_at?: number;
  num_pages_indexed: number;
  error_message?: string;
  stats?: CrawlStats;
  failure_details?: any;
}

export default function CrawlController() {
  const [url, setUrl] = useState('');
  const [activeJob, setActiveJob] = useState<CrawlJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startCrawl = async () => {
    if (!url.trim()) {
      setError('Please enter a URL to crawl');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/crawl', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target_url: url
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      
      // Start polling for status
      if (data.run_id) {
        pollJobStatus(data.run_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start crawl');
    } finally {
      setLoading(false);
    }
  };

  const pollJobStatus = async (runId: string) => {
    let polling = true;
    
    const poll = async () => {
      try {
        const response = await fetch(`/api/crawl/status/${runId}`);
        
        if (response.ok) {
          const job: CrawlJob = await response.json();
          setActiveJob(job);
          
          // Stop polling if job is complete or failed
          if (job.status === 'complete' || job.status === 'failed') {
            polling = false;
          }
        }
      } catch (err) {
        console.error('Error polling job status:', err);
      }
      
      if (polling) {
        setTimeout(poll, 2000); // Poll every 2 seconds
      }
    };
    
    poll();
  };

  const formatDuration = (startTime: number, endTime?: number) => {
    const duration = Math.floor((endTime ? endTime : Date.now() / 1000) - startTime);
    if (duration < 60) return `${duration}s`;
    if (duration < 3600) return `${Math.floor(duration / 60)}m ${duration % 60}s`;
    return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`;
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const renderCompletionStats = (job: CrawlJob) => {
    if (job.status !== 'complete' || !job.stats) return null;

    const stats = job.stats;
    const duration = job.completed_at ? formatDuration(job.started_at, job.completed_at) : 'Unknown';
    
    return (
      <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded-lg">
        <div className="flex items-center justify-between mb-3">
          <h4 className="font-semibold text-green-800">Crawl Completed Successfully!</h4>
          <div className="text-sm text-green-600">
            Duration: <span className="font-medium">{duration}</span>
          </div>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
          <div className="text-center p-3 bg-white rounded border">
            <div className="text-2xl font-bold text-blue-600">{stats.pages_indexed || 0}</div>
            <div className="text-sm text-gray-600">Pages Indexed</div>
          </div>
          <div className="text-center p-3 bg-white rounded border">
            <div className="text-2xl font-bold text-green-600">{stats.pages_processed || stats.total_pages_crawled || 0}</div>
            <div className="text-sm text-gray-600">Pages Processed</div>
          </div>
          <div className="text-center p-3 bg-white rounded border">
            <div className="text-2xl font-bold text-purple-600">{stats.pages_fetched || 0}</div>
            <div className="text-sm text-gray-600">Pages Fetched</div>
          </div>
          <div className="text-center p-3 bg-white rounded border">
            <div className="text-2xl font-bold text-orange-600">{stats.pages_queued || 0}</div>
            <div className="text-sm text-gray-600">Pages Queued</div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <h5 className="font-medium text-gray-800 mb-2">Performance</h5>
            <ul className="space-y-1 text-gray-600">
              <li>Throughput: <span className="font-medium">{stats.avg_throughput ? `${stats.avg_throughput} pages/sec` : 'N/A'}</span></li>
              <li>URLs Extracted: <span className="font-medium">{stats.urls_extracted || 0}</span></li>
              <li>Pages Rejected: <span className="font-medium text-yellow-600">{stats.pages_rejected || 0}</span></li>
              <li>Norconex Duration: <span className="font-medium">{stats.norconex_duration_seconds ? `${stats.norconex_duration_seconds}s` : 'N/A'}</span></li>
            </ul>
          </div>
          <div>
            <h5 className="font-medium text-gray-800 mb-2">Crawl Details</h5>
            <ul className="space-y-1 text-gray-600">
              <li>Run ID: <span className="font-mono text-xs">{job.run_id.slice(0, 8)}...</span></li>
              <li>Started: <span className="font-medium">{new Date(job.started_at * 1000).toLocaleTimeString()}</span></li>
              {job.completed_at && (
                <li>Completed: <span className="font-medium">{new Date(job.completed_at * 1000).toLocaleTimeString()}</span></li>
              )}
              <li>Status: <span className="font-medium capitalize">{job.status}</span></li>
            </ul>
          </div>
        </div>

        {stats.domains_found && stats.domains_found.length > 0 && (
          <div className="mt-3 pt-3 border-t border-green-200">
            <h5 className="font-medium text-gray-800 mb-2">Domains Discovered</h5>
            <div className="flex flex-wrap gap-2">
              {stats.domains_found.slice(0, 5).map((domain, idx) => (
                <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-mono">
                  {domain}
                </span>
              ))}
              {stats.domains_found.length > 5 && (
                <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded text-xs">
                  +{stats.domains_found.length - 5} more
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderFailureStats = (job: CrawlJob) => {
    if (job.status !== 'failed') return null;

    const stats = job.stats;
    const duration = job.completed_at ? formatDuration(job.started_at, job.completed_at) : 'Unknown';
    
    return (
      <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center justify-between mb-3">
          <h4 className="font-semibold text-red-800">Crawl Failed - Partial Results</h4>
          <div className="text-sm text-red-600">
            Duration: <span className="font-medium">{duration}</span>
          </div>
        </div>
        
        {/* Show partial progress if any pages were indexed */}
        {stats && stats.pages_indexed && stats.pages_indexed > 0 && (
          <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
            <div className="text-sm text-yellow-800 mb-2">
              <strong>Partial Progress:</strong> Some pages were successfully crawled before the failure
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-2 bg-white rounded border">
                <div className="text-xl font-bold text-blue-600">{stats.pages_indexed}</div>
                <div className="text-xs text-gray-600">Pages Indexed</div>
              </div>
              <div className="text-center p-2 bg-white rounded border">
                <div className="text-xl font-bold text-green-600">{stats.pages_processed || stats.total_pages_crawled || 0}</div>
                <div className="text-xs text-gray-600">Pages Processed</div>
              </div>
              <div className="text-center p-2 bg-white rounded border">
                <div className="text-xl font-bold text-purple-600">{stats.pages_fetched || 0}</div>
                <div className="text-xs text-gray-600">Pages Fetched</div>
              </div>
              <div className="text-center p-2 bg-white rounded border">
                <div className="text-xl font-bold text-orange-600">{stats.pages_queued || 0}</div>
                <div className="text-xs text-gray-600">Pages Queued</div>
              </div>
            </div>
          </div>
        )}

        {/* Error details */}
        <div className="space-y-2">
          <div className="text-sm">
            <span className="font-medium text-red-800">Error:</span>
            <span className="ml-2 text-red-700">{job.error_message}</span>
          </div>
          
          {stats && stats.pages_indexed === 0 && (
            <div className="text-sm text-red-600">
              No pages were successfully indexed before the crawl failed.
            </div>
          )}
          
          <div className="mt-3 text-xs text-gray-600">
            <p><strong>Possible causes:</strong></p>
            <ul className="list-disc list-inside mt-1 space-y-1">
              <li>Website blocked the crawler (robots.txt, rate limiting)</li>
              <li>Network connectivity issues</li>
              <li>OpenSearch connection problems</li>
              <li>Large website exceeded resource limits</li>
              <li>Invalid URLs or broken links encountered</li>
            </ul>
          </div>

          {/* Show data availability notice if partial data exists */}
          {stats && stats.pages_indexed && stats.pages_indexed > 0 && (
            <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded text-blue-700 text-sm">
              <strong>Good news:</strong> The {stats.pages_indexed} pages that were crawled successfully are available for search in OpenSearch.
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="bg-white p-6 rounded-lg border">
      <h2 className="text-xl font-medium mb-4">Start New Norconex Crawl</h2>
      
      <div className="mb-6">
        <div className="flex gap-2 mb-4">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="Enter URL to crawl (e.g., https://example.com)"
            className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading || (activeJob && activeJob.status === 'running')}
          />
          <button
            onClick={startCrawl}
            disabled={loading || (activeJob && activeJob.status === 'running')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Starting...' : 'Start Crawl'}
          </button>
        </div>
        
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            <strong>Error:</strong> {error}
            <br />
            <small>Make sure the backend API is running and accessible</small>
          </div>
        )}
      </div>

      {activeJob && (
        <div className="border-t pt-6">
          <h3 className="font-medium mb-4">Active Crawl</h3>
          
          <div className="bg-gray-50 p-4 rounded-lg">
            <div className="flex justify-between items-start mb-3">
              <div>
                <p className="font-medium text-blue-600">{activeJob.target_url}</p>
                <p className="text-sm text-gray-500">Run ID: {activeJob.run_id}</p>
              </div>
              <StatusBadge status={activeJob.status === 'pending' ? 'running' : activeJob.status as any} />
            </div>
            
            <div className="mb-3">
              <div className="flex justify-between text-sm mb-1">
                <span>Progress</span>
                <span>{activeJob.progress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${activeJob.progress}%` }}
                ></div>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Pages indexed:</span>
                <span className="font-medium ml-2">{activeJob.num_pages_indexed}</span>
              </div>
              <div>
                <span className="text-gray-600">Duration:</span>
                <span className="font-medium ml-2">{formatDuration(activeJob.started_at)}</span>
              </div>
            </div>
            
            {activeJob.error_message && (
              <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                <strong>Error:</strong> {activeJob.error_message}
              </div>
            )}
            
            {activeJob.status === 'complete' && !activeJob.stats && (
              <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded text-green-700 text-sm">
                <strong>Success!</strong> Crawl completed successfully. Data should be available in OpenSearch.
              </div>
            )}
          </div>
          
          {/* Render detailed completion stats */}
          {renderCompletionStats(activeJob)}
          
          {/* Render failure stats with partial results */}
          {renderFailureStats(activeJob)}
        </div>
      )}
      
      <div className="mt-6 text-sm text-gray-600">
        <p><strong>Note:</strong> The crawler will:</p>
        <ul className="list-disc list-inside mt-2 space-y-1">
          <li>Crawl up to 500 documents with max depth of 3</li>
          <li>Index content into OpenSearch with index name "demo_factory"</li>
          <li>Keep downloaded files for analysis</li>
          <li>Run using the Norconex HTTP Collector v3</li>
        </ul>
      </div>
    </div>
  );
}