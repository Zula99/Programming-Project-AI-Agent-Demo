'use client';

import { useState } from 'react';
import StatusBadge from './StatusBadge';

interface CrawlJob {
  run_id: string;
  target_url: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  progress: number;
  started_at: number;
  num_pages_indexed: number;
  error_message?: string;
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

  const formatDuration = (startTime: number) => {
    const duration = Math.floor((Date.now() / 1000) - startTime);
    if (duration < 60) return `${duration}s`;
    if (duration < 3600) return `${Math.floor(duration / 60)}m ${duration % 60}s`;
    return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`;
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
            
            {activeJob.status === 'complete' && (
              <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded text-green-700 text-sm">
                <strong>Success!</strong> Crawl completed successfully. Data should be available in OpenSearch.
              </div>
            )}
          </div>
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