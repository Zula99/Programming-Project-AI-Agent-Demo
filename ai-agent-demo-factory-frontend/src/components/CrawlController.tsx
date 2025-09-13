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
  status: 'pending' | 'running' | 'complete' | 'failed' | 'stopped';
  progress: number;
  started_at: number;
  completed_at?: number;
  num_pages_indexed: number;
  error_message?: string;
  stats?: CrawlStats;
  failure_details?: any;
}

interface CMSTemplate {
  id: string;
  name: string;
  description: string;
  platform: string;
  maxDepth: number;
  maxDocuments: number;
  numThreads: number;
  delay: number;
  stayOnDomain: boolean;
  includeSubdomains: boolean;
  fileExclusions: string[];
  urlPatterns: string[];
}

// Predefined CMS templates

const CMS_TEMPLATES: CMSTemplate[] = [
  {
    id: 'wordpress',
    name: 'WordPress',
    description: 'Optimized for WordPress sites with posts, pages, and WooCommerce',
    platform: 'WordPress',
    maxDepth: 3,           
    maxDocuments: 500,     
    numThreads: 2,         
    delay: 1500,           
    stayOnDomain: true,
    includeSubdomains: false,
    fileExclusions: ['wp-admin', 'wp-includes', 'wp-content/uploads', 'admin-ajax.php'],
    urlPatterns: ['/wp-content/', '/wp-json/', '/category/', '/tag/', '/author/']
  },
  {
    id: 'drupal',
    name: 'Drupal',
    description: 'Optimized for Drupal sites with nodes, taxonomy, and content types',
    platform: 'Drupal',
    maxDepth: 3,           
    maxDocuments: 400,     
    numThreads: 2,         
    delay: 2000,           
    stayOnDomain: true,
    includeSubdomains: false,
    fileExclusions: ['admin', 'modules', 'themes', 'sites/default/files'],
    urlPatterns: ['/node/', '/taxonomy/', '/user/', '/content/']
  },
  {
    id: 'joomla',
    name: 'Joomla',
    description: 'Optimized for Joomla sites with articles, categories, and components',
    platform: 'Joomla',
    maxDepth: 3,           
    maxDocuments: 350,     
    numThreads: 2,         
    delay: 1500,           
    stayOnDomain: true,
    includeSubdomains: false,
    fileExclusions: ['administrator', 'cache', 'tmp', 'logs'],
    urlPatterns: ['/component/', '/index.php', '/article/', '/category/']
  },
  {
    id: 'wix',
    name: 'Wix',
    description: 'Optimized for Wix sites with dynamic content and JavaScript',
    platform: 'Wix',
    maxDepth: 2,           
    maxDocuments: 300,     
    numThreads: 1,        
    delay: 2500,           
    stayOnDomain: true,
    includeSubdomains: true,
    fileExclusions: ['_api', 'wixstatic', 'static.wixstatic.com'],
    urlPatterns: ['/s/', '/blog/', '/_api/']
  },
  {
    id: 'squarespace',
    name: 'Squarespace',
    description: 'Optimized for Squarespace sites with galleries, blogs, and events',
    platform: 'Squarespace',
    maxDepth: 3,           
    maxDocuments: 400,     
    numThreads: 2,         
    delay: 1500,           
    stayOnDomain: true,
    includeSubdomains: false,
    fileExclusions: ['admin', 'config', 'squarespace'],
    urlPatterns: ['/s/', '/blog/', '/gallery/', '/events/']
  },
  {
    id: 'generic',
    name: 'Generic',
    description: 'General purpose template for unknown or custom platforms',
    platform: 'Generic',
    maxDepth: 2,           
    maxDocuments: 250,     
    numThreads: 2,         
    delay: 1500,           
    stayOnDomain: true,
    includeSubdomains: false,
    fileExclusions: ['admin', 'api', 'assets', 'static'],
    urlPatterns: ['/blog/', '/news/', '/about/', '/contact/']
  }
];

export default function CrawlController() {
  const [url, setUrl] = useState('');
  const [selectedTemplate, setSelectedTemplate] = useState<CMSTemplate | null>(null);
  const [activeJob, setActiveJob] = useState<CrawlJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTemplatePreview, setShowTemplatePreview] = useState(false);

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
          target_url: url,
          template: selectedTemplate ? {
            id: selectedTemplate.id,
            name: selectedTemplate.name,
            platform: selectedTemplate.platform,
            maxDepth: selectedTemplate.maxDepth,
            maxDocuments: selectedTemplate.maxDocuments,
            numThreads: selectedTemplate.numThreads,
            delay: selectedTemplate.delay,
            stayOnDomain: selectedTemplate.stayOnDomain,
            includeSubdomains: selectedTemplate.includeSubdomains,
            fileExclusions: selectedTemplate.fileExclusions,
            urlPatterns: selectedTemplate.urlPatterns
          } : null
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
          
          // Stop polling if job is complete, failed, or stopped
          if (job.status === 'complete' || job.status === 'failed' || job.status === 'stopped') {
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

  const handleTemplateSelect = (template: CMSTemplate) => {
    setSelectedTemplate(template);
    setShowTemplatePreview(false);
  };

  const handleTemplatePreview = (template: CMSTemplate) => {
    setSelectedTemplate(template);
    setShowTemplatePreview(true);
  };

  const clearTemplate = () => {
    setSelectedTemplate(null);
    setShowTemplatePreview(false);
  };

  const stopCrawl = async (runId: string) => {
    try {
      const response = await fetch(`/api/crawl/stop/${runId}`, {
        method: 'POST',
      });

      if (!response.ok) {
        let errorMessage = `HTTP error! status: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMessage = errorData.details || errorData.error || errorData.detail || errorMessage;
        } catch {
          // If response is not JSON, use the status text
          errorMessage = `${response.status}: ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data = await response.json();
      console.log('Crawl stopped successfully:', data);
      
      // Update the local job state immediately
      if (activeJob && activeJob.run_id === runId) {
        setActiveJob({
          ...activeJob,
          status: 'stopped',
          completed_at: Date.now() / 1000
        });
      }
    } catch (err) {
      console.error('Error stopping crawl:', err);
      setError(err instanceof Error ? err.message : 'Failed to stop crawl');
    }
  };

  const formatDuration = (startTime: number, endTime?: number) => {
    const duration = Math.floor((endTime ? endTime : Date.now() / 1000) - startTime);
    if (duration < 60) return `${duration}s`;
    if (duration < 3600) return `${Math.floor(duration / 60)}m ${duration % 60}s`;
    return `${Math.floor(duration / 3600)}h ${Math.floor((duration % 3600) / 60)}m`;
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

  const renderStoppedStats = (job: CrawlJob) => {
    if (job.status !== 'stopped') return null;

    const stats = job.stats;
    const duration = job.completed_at ? formatDuration(job.started_at, job.completed_at) : 'Unknown';
    
    return (
      <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <div className="flex items-center justify-between mb-3">
          <h4 className="font-semibold text-yellow-800">Crawl Stopped - Partial Results Available</h4>
          <div className="text-sm text-yellow-600">
            Duration: <span className="font-medium">{duration}</span>
          </div>
        </div>
        
        <div className="mb-4 p-3 bg-orange-50 border border-orange-200 rounded">
          <div className="text-sm text-orange-800 mb-2">
            <strong>Status:</strong> The crawl was manually stopped and partial results have been saved
          </div>
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-2 bg-white rounded border">
                <div className="text-xl font-bold text-blue-600">{stats.pages_indexed || 0}</div>
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
          )}
        </div>

        <div className="space-y-2">
          <div className="text-sm text-gray-700">
            The crawl was stopped before completion, but any pages that were successfully crawled are available for search.
          </div>
          
          {stats && stats.pages_indexed && stats.pages_indexed > 0 && (
            <div className="mt-3 p-2 bg-blue-50 border border-blue-200 rounded text-blue-700 text-sm">
              <strong>Data Available:</strong> {stats.pages_indexed} pages were successfully indexed and are available for search in OpenSearch.
            </div>
          )}
          
          {(!stats || !stats.pages_indexed || stats.pages_indexed === 0) && (
            <div className="mt-3 p-2 bg-gray-50 border border-gray-200 rounded text-gray-700 text-sm">
              No pages were successfully indexed before the crawl was stopped.
            </div>
          )}
        </div>
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
            disabled={loading || (activeJob?.status === 'running')}
          />
          <button
            onClick={startCrawl}
            disabled={loading || (activeJob?.status === 'running')}
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

      {/* CMS Template Selection */}
      <div className="mb-6">
        <h3 className="text-lg font-medium mb-3">Select CMS Template (Optional)</h3>
        <p className="text-sm text-gray-600 mb-4">
          Choose a template optimized for your target website's platform to improve crawl efficiency.
        </p>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-4">
          {CMS_TEMPLATES.map((template) => (
            <div
              key={template.id}
              className={`p-4 border rounded-lg cursor-pointer transition-all ${
                selectedTemplate?.id === template.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
              }`}
              onClick={() => handleTemplateSelect(template)}
            >
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900">{template.name}</h4>
                <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                  {template.platform}
                </span>
              </div>
              <p className="text-sm text-gray-600 mb-3">{template.description}</p>
              <div className="flex gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleTemplatePreview(template);
                  }}
                  className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                >
                  Preview
                </button>
                {selectedTemplate?.id === template.id && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      clearTemplate();
                    }}
                    className="text-xs px-2 py-1 bg-red-100 text-red-700 rounded hover:bg-red-200"
                  >
                    Clear
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {selectedTemplate && (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-blue-900">Selected Template: {selectedTemplate.name}</h4>
              <button
                onClick={clearTemplate}
                className="text-sm text-blue-600 hover:text-blue-800"
              >
                Change Template
              </button>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Max Depth:</span>
                <span className="font-medium ml-1">{selectedTemplate.maxDepth}</span>
              </div>
              <div>
                <span className="text-gray-600">Max Documents:</span>
                <span className="font-medium ml-1">{selectedTemplate.maxDocuments}</span>
              </div>
              <div>
                <span className="text-gray-600">Threads:</span>
                <span className="font-medium ml-1">{selectedTemplate.numThreads}</span>
              </div>
              <div>
                <span className="text-gray-600">Delay:</span>
                <span className="font-medium ml-1">{selectedTemplate.delay}ms</span>
              </div>
            </div>
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
              <div className="flex items-center gap-2">
                {activeJob.status === 'running' && (
                  <button
                    onClick={() => stopCrawl(activeJob.run_id)}
                    className="px-3 py-1 bg-red-600 text-white text-sm rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    Stop Crawl
                  </button>
                )}
                <StatusBadge status={activeJob.status === 'pending' ? 'running' : activeJob.status as any} />
              </div>
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
          
          {/* Render stopped stats with partial results */}
          {renderStoppedStats(activeJob)}
          
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

      {/* Template Preview Modal */}
      {showTemplatePreview && selectedTemplate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-semibold">Template Preview: {selectedTemplate.name}</h3>
              <button
                onClick={() => setShowTemplatePreview(false)}
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Description</h4>
                <p className="text-gray-600">{selectedTemplate.description}</p>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Configuration Parameters</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Max Depth:</span>
                      <span className="font-medium">{selectedTemplate.maxDepth}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Max Documents:</span>
                      <span className="font-medium">{selectedTemplate.maxDocuments}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Threads:</span>
                      <span className="font-medium">{selectedTemplate.numThreads}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Delay:</span>
                      <span className="font-medium">{selectedTemplate.delay}ms</span>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Stay on Domain:</span>
                      <span className="font-medium">{selectedTemplate.stayOnDomain ? 'Yes' : 'No'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Include Subdomains:</span>
                      <span className="font-medium">{selectedTemplate.includeSubdomains ? 'Yes' : 'No'}</span>
                    </div>
                  </div>
                </div>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 mb-2">File Exclusions</h4>
                <div className="flex flex-wrap gap-2">
                  {selectedTemplate.fileExclusions.map((exclusion, index) => (
                    <span key={index} className="px-2 py-1 bg-red-100 text-red-800 text-xs rounded">
                      {exclusion}
                    </span>
                  ))}
                </div>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 mb-2">URL Patterns</h4>
                <div className="flex flex-wrap gap-2">
                  {selectedTemplate.urlPatterns.map((pattern, index) => (
                    <span key={index} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                      {pattern}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            
            <div className="flex gap-3 mt-6 pt-4 border-t">
              <button
                onClick={() => {
                  setShowTemplatePreview(false);
                  setSelectedTemplate(selectedTemplate);
                }}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                Use This Template
              </button>
              <button
                onClick={() => setShowTemplatePreview(false)}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}