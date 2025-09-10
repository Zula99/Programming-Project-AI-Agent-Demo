'use client';

import { useState, useEffect } from 'react';
import StatusBadge from './StatusBadge';

interface LogEntry {
  run_id: string;
  timestamp: string;
  log_level: string;
  logger: string;
  message: string;
  log_type: 'trigger' | 'runner' | 'execution_summary';
  thread?: string;
  execution_stats?: {
    total_processed?: number;
    crawl_duration?: string;
    avg_throughput?: number;
    event_counts?: Record<string, number>;
  };
  raw_log_line: string;
}

interface CrawlRun {
  run_id: string;
  target_url?: string;
  status?: string;
  log_count: number;
  last_activity: string;
}

export default function CrawlLogs() {
  const [runs, setRuns] = useState<CrawlRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [logFilter, setLogFilter] = useState<{
    log_level?: string;
    log_type?: string;
  }>({});

  // Fetch available runs (you might need to create this endpoint in the backend)
  const fetchRuns = async () => {
    try {
      // For now, we'll get runs by searching all logs and grouping by run_id
      const response = await fetch('http://localhost:5000/crawl-logs/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          size: 1000  // Get many logs to extract unique run_ids
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch runs');
      }

      const data = await response.json();
      
      // Group logs by run_id to create run summaries
      const runMap = new Map<string, CrawlRun>();
      
      data.logs?.forEach((log: LogEntry) => {
        const runId = log.run_id;
        if (!runMap.has(runId)) {
          runMap.set(runId, {
            run_id: runId,
            target_url: extractTargetUrl(log.message),
            status: extractStatus(log.message, log.log_level),
            log_count: 0,
            last_activity: log.timestamp
          });
        }
        
        const run = runMap.get(runId)!;
        run.log_count++;
        
        // Update last activity if this log is newer
        if (new Date(log.timestamp) > new Date(run.last_activity)) {
          run.last_activity = log.timestamp;
        }
        
        // Update status and URL from more specific log entries
        if (log.message.includes('Executing crawl for') && log.message.includes('with config')) {
          run.target_url = extractTargetUrl(log.message);
        }
        
        if (log.message.includes('Crawl completed successfully') || log.message.includes('Crawl failed')) {
          run.status = log.message.includes('failed') ? 'failed' : 'complete';
        }
      });
      
      const runsArray = Array.from(runMap.values()).sort((a, b) => 
        new Date(b.last_activity).getTime() - new Date(a.last_activity).getTime()
      );
      
      setRuns(runsArray);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch runs');
    }
  };

  // Extract target URL from log messages
  const extractTargetUrl = (message: string): string => {
    // Try to extract URL from various log message patterns
    const patterns = [
      /with config .*crawler-([^.]+)\.xml/,
      /trigger file: .*trigger-([^.]+)\.json/,
      /Executing crawl for ([^\s]+)/
    ];
    
    for (const pattern of patterns) {
      const match = message.match(pattern);
      if (match) {
        return match[1] || 'Unknown URL';
      }
    }
    
    return 'Unknown URL';
  };

  // Extract status from log messages
  const extractStatus = (message: string, logLevel: string): string => {
    if (message.includes('Crawl completed successfully')) return 'complete';
    if (message.includes('Crawl failed') || logLevel === 'ERROR') return 'failed';
    if (message.includes('Starting crawler') || message.includes('Executing crawl')) return 'running';
    return 'unknown';
  };

  // Fetch logs for a specific run
  const fetchLogsForRun = async (runId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('http://localhost:5000/crawl-logs/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          run_id: runId,
          log_level: logFilter.log_level,
          log_type: logFilter.log_type,
          size: 100
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to fetch logs');
      }

      const data = await response.json();
      setLogs(data.logs || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch logs');
    } finally {
      setLoading(false);
    }
  };

  // Load runs on component mount
  useEffect(() => {
    fetchRuns();
  }, []);

  // Load logs when run is selected or filter changes
  useEffect(() => {
    if (selectedRunId) {
      fetchLogsForRun(selectedRunId);
    }
  }, [selectedRunId, logFilter]);

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const getLogLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR': return 'text-red-600 bg-red-50';
      case 'WARN': return 'text-yellow-600 bg-yellow-50';
      case 'INFO': return 'text-blue-600 bg-blue-50';
      case 'DEBUG': return 'text-gray-600 bg-gray-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const getLogTypeColor = (type: string) => {
    switch (type) {
      case 'trigger': return 'text-purple-600 bg-purple-50';
      case 'runner': return 'text-green-600 bg-green-50';
      case 'execution_summary': return 'text-orange-600 bg-orange-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  return (
    <div className="bg-white rounded-lg border p-6">
      <h2 className="text-xl font-semibold mb-4">Crawl Logs</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Run List */}
        <div className="lg:col-span-1">
          <h3 className="font-medium mb-3">Crawl Runs</h3>
          
          {error && (
            <div className="text-red-600 text-sm mb-3 p-2 bg-red-50 rounded">
              {error}
            </div>
          )}

          <div className="space-y-2 max-h-[60vh] overflow-y-auto">
            {runs.map((run) => (
              <div
                key={run.run_id}
                className={`p-3 rounded border cursor-pointer transition-colors ${
                  selectedRunId === run.run_id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                onClick={() => setSelectedRunId(run.run_id)}
              >
                <div className="flex justify-between items-start mb-1">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {run.run_id.substring(0, 8)}...
                  </p>
                  {run.status && <StatusBadge status={run.status as any} />}
                </div>
                <p className="text-xs text-gray-500 truncate">{run.target_url}</p>
                <div className="flex justify-between items-center mt-1">
                  <span className="text-xs text-gray-400">{run.log_count} logs</span>
                  <span className="text-xs text-gray-400">
                    {formatTimestamp(run.last_activity)}
                  </span>
                </div>
              </div>
            ))}
          </div>
          
          <button
            onClick={fetchRuns}
            className="mt-3 text-sm text-blue-500 hover:text-blue-700"
          >
            Refresh Runs
          </button>
        </div>

        {/* Log Details */}
        <div className="lg:col-span-2">
          {selectedRunId ? (
            <>
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-medium">
                  Logs for {selectedRunId.substring(0, 12)}...
                </h3>
                
                {/* Log Filters */}
                <div className="flex gap-2">
                  <select
                    value={logFilter.log_level || ''}
                    onChange={(e) => setLogFilter({...logFilter, log_level: e.target.value || undefined})}
                    className="text-sm border rounded px-2 py-1"
                  >
                    <option value="">All Levels</option>
                    <option value="ERROR">ERROR</option>
                    <option value="WARN">WARN</option>
                    <option value="INFO">INFO</option>
                    <option value="DEBUG">DEBUG</option>
                  </select>
                  
                  <select
                    value={logFilter.log_type || ''}
                    onChange={(e) => setLogFilter({...logFilter, log_type: e.target.value || undefined})}
                    className="text-sm border rounded px-2 py-1"
                  >
                    <option value="">All Types</option>
                    <option value="trigger">Trigger</option>
                    <option value="runner">Runner</option>
                    <option value="execution_summary">Summary</option>
                  </select>
                </div>
              </div>

              {loading && (
                <div className="text-center py-4">
                  <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                </div>
              )}

              <div className="space-y-2 max-h-[60vh] overflow-y-auto">
                {logs.map((log, index) => (
                  <div key={index} className="border border-gray-200 rounded p-3">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex gap-2 flex-wrap">
                        <span className={`text-xs px-2 py-1 rounded font-medium ${getLogLevelColor(log.log_level)}`}>
                          {log.log_level}
                        </span>
                        <span className={`text-xs px-2 py-1 rounded ${getLogTypeColor(log.log_type)}`}>
                          {log.log_type}
                        </span>
                        {log.thread && (
                          <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-600">
                            {log.thread}
                          </span>
                        )}
                      </div>
                      <span className="text-xs text-gray-500">
                        {formatTimestamp(log.timestamp)}
                      </span>
                    </div>
                    
                    <p className="text-sm text-gray-700 mb-1">{log.message}</p>
                    
                    {log.execution_stats && (
                      <div className="mt-2 p-2 bg-gray-50 rounded text-xs">
                        <strong>Execution Stats:</strong>
                        {log.execution_stats.total_processed && (
                          <span className="ml-2">Processed: {log.execution_stats.total_processed}</span>
                        )}
                        {log.execution_stats.crawl_duration && (
                          <span className="ml-2">Duration: {log.execution_stats.crawl_duration}</span>
                        )}
                        {log.execution_stats.avg_throughput && (
                          <span className="ml-2">Throughput: {log.execution_stats.avg_throughput}/sec</span>
                        )}
                      </div>
                    )}
                    
                    <details className="mt-2">
                      <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                        Raw log line
                      </summary>
                      <pre className="text-xs text-gray-600 mt-1 whitespace-pre-wrap bg-gray-50 p-2 rounded">
                        {log.raw_log_line}
                      </pre>
                    </details>
                  </div>
                ))}
                
                {logs.length === 0 && !loading && (
                  <div className="text-center py-8 text-gray-500">
                    No logs found for this run
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="text-center py-12 text-gray-500">
              Select a crawl run to view its logs
            </div>
          )}
        </div>
      </div>
    </div>
  );
}