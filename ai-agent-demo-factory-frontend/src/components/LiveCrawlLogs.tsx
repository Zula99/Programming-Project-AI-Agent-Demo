'use client';

import React, { useRef, useEffect, useState } from 'react';
import { useNorconexWebSocket, LogMessage, ProgressMessage } from '@/hooks/useNorconexWebSocket';

interface LiveCrawlLogsProps {
  runId: string;
  onComplete?: () => void;
  onFailed?: () => void;
}

export default function LiveCrawlLogs({ runId, onComplete, onFailed }: LiveCrawlLogsProps) {
  const logsEndRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);
  const [filter, setFilter] = useState<'ALL' | 'INFO' | 'WARN' | 'ERROR'>('ALL');

  const {
    isConnected,
    logs,
    progress,
    lastEvent,
    connectionError,
    clearLogs,
  } = useNorconexWebSocket(runId, {
    onCrawlCompleted: (event) => {
      console.log('Crawl completed:', event);
      if (onComplete) onComplete();
    },
    onCrawlFailed: (event) => {
      console.log('Crawl failed:', event);
      if (onFailed) onFailed();
    },
    autoConnect: true,
  });

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, autoScroll]);

  const filteredLogs = filter === 'ALL'
    ? logs
    : logs.filter(log => log.log_level === filter);

  const getLogLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'text-red-600 bg-red-50';
      case 'WARN':
        return 'text-yellow-600 bg-yellow-50';
      case 'INFO':
        return 'text-blue-600 bg-blue-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getLogLevelIcon = (level: string) => {
    switch (level) {
      case 'ERROR':
        return '❌';
      case 'WARN':
        return '⚠️';
      case 'INFO':
        return 'ℹ️';
      default:
        return '📝';
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-md border border-gray-200">
      {/* Header */}
      <div className="bg-gray-800 text-white px-4 py-3 rounded-t-lg flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold">Live Crawl Logs</h3>
          <span className={`flex items-center gap-2 text-sm px-2 py-1 rounded ${
            isConnected ? 'bg-green-600' : 'bg-red-600'
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-300 animate-pulse' : 'bg-red-300'
            }`}></span>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
          {progress && (
            <span className="text-sm px-2 py-1 bg-blue-600 rounded">
              Progress: {progress.progress}%
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded"
            />
            Auto-scroll
          </label>
          <button
            onClick={clearLogs}
            className="px-3 py-1 bg-gray-600 hover:bg-gray-700 rounded text-sm"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-gray-100 px-4 py-2 border-b border-gray-200 flex items-center gap-2">
        <span className="text-sm font-medium text-gray-700">Filter:</span>
        {(['ALL', 'INFO', 'WARN', 'ERROR'] as const).map((level) => (
          <button
            key={level}
            onClick={() => setFilter(level)}
            className={`px-3 py-1 text-xs rounded ${
              filter === level
                ? 'bg-blue-600 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-200'
            }`}
          >
            {level} ({logs.filter(l => level === 'ALL' || l.log_level === level).length})
          </button>
        ))}
      </div>

      {/* Connection Error */}
      {connectionError && (
        <div className="bg-red-50 border-l-4 border-red-500 p-3 mx-4 mt-2">
          <div className="flex items-center">
            <span className="text-red-700 text-sm">❌ Connection Error: {connectionError}</span>
          </div>
        </div>
      )}

      {/* Progress Bar */}
      {progress && (
        <div className="px-4 pt-3">
          <div className="bg-gray-200 rounded-full h-2 overflow-hidden">
            <div
              className="bg-blue-600 h-2 transition-all duration-300"
              style={{ width: `${progress.progress}%` }}
            />
          </div>
          <div className="flex justify-between items-center mt-1 text-xs text-gray-600">
            <span>Status: {progress.status}</span>
            <span>{progress.progress}%</span>
          </div>
        </div>
      )}

      {/* Logs Container */}
      <div className="flex-1 overflow-y-auto p-4 font-mono text-sm bg-gray-50">
        {filteredLogs.length === 0 ? (
          <div className="text-center text-gray-500 py-8">
            {isConnected ? 'Waiting for logs...' : 'Not connected. Logs will appear when crawl starts.'}
          </div>
        ) : (
          <div className="space-y-1">
            {filteredLogs.map((log, index) => (
              <div
                key={index}
                className={`flex items-start gap-2 p-2 rounded ${getLogLevelColor(log.log_level)} border border-gray-200`}
              >
                <span className="text-lg leading-none">{getLogLevelIcon(log.log_level)}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs text-gray-500 whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                      log.log_level === 'ERROR' ? 'bg-red-200 text-red-800' :
                      log.log_level === 'WARN' ? 'bg-yellow-200 text-yellow-800' :
                      'bg-blue-200 text-blue-800'
                    }`}>
                      {log.log_level}
                    </span>
                  </div>
                  <p className="text-sm mt-1 break-words">{log.message}</p>
                  {log.metadata && Object.keys(log.metadata).length > 0 && (
                    <details className="mt-1">
                      <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-800">
                        Metadata
                      </summary>
                      <pre className="text-xs mt-1 p-2 bg-white rounded overflow-x-auto">
                        {JSON.stringify(log.metadata, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        )}
      </div>

      {/* Stats Footer */}
      {progress?.stats && (
        <div className="bg-gray-100 px-4 py-2 border-t border-gray-200 text-xs text-gray-700">
          <div className="flex gap-4">
            {Object.entries(progress.stats).map(([key, value]) => (
              <span key={key}>
                <strong>{key}:</strong> {String(value)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
