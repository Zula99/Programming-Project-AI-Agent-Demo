'use client'

import { useState, useEffect, useRef } from "react";
import { HiChevronDown, HiChevronUp, HiCodeBracket, HiCommandLine } from "react-icons/hi2";

interface BackendLogsDropdownProps {
  runId?: string | null;
  isConnected?: boolean;
  backendLogs?: BackendLogEntry[];
}

interface BackendLogEntry {
  timestamp: string;
  level: "INFO" | "WARNING" | "ERROR" | "DEBUG";
  message: string;
  source: string; // e.g., "uvicorn", "main", etc.
}

export default function BackendLogsDropdown({
  runId,
  isConnected = false,
  backendLogs = []
}: BackendLogsDropdownProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (isExpanded) {
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [backendLogs, isExpanded]);

  // Backend logs are now received via props from parent component (WebSocket)
  // No simulation needed anymore

  const getLevelColor = (level: string) => {
    switch (level) {
      case "ERROR": return "text-red-400";
      case "WARNING": return "text-yellow-400";
      case "DEBUG": return "text-gray-400";
      default: return "text-green-400";
    }
  };

  const getSourceColor = (source: string) => {
    switch (source) {
      case "uvicorn": return "text-blue-400";
      case "crawler": return "text-purple-400";
      case "parser": return "text-cyan-400";
      case "classifier": return "text-orange-400";
      case "network": return "text-pink-400";
      case "storage": return "text-indigo-400";
      default: return "text-gray-400";
    }
  };

  return (
    <div className="bg-white border rounded-lg">
      {/* Header - Collapsible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-gray-50 transition-colors rounded-t-lg"
        suppressHydrationWarning={true}
      >
        <div className="flex items-center gap-2">
          <HiCommandLine className="h-5 w-5 text-gray-600" />
          <h3 className="text-lg font-semibold text-gray-900">Backend Logs</h3>
          <div className="flex items-center gap-1 ml-2">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-400'
            }`} />
            <span className="text-xs text-gray-500">
              {isConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">
            {backendLogs.length} entries
          </span>
          {isExpanded ? (
            <HiChevronUp className="h-5 w-5 text-gray-500" />
          ) : (
            <HiChevronDown className="h-5 w-5 text-gray-500" />
          )}
        </div>
      </button>

      {/* Expandable Content */}
      {isExpanded && (
        <div className="border-t bg-gray-900 rounded-b-lg">
          <div className="p-3 bg-gray-800 border-b border-gray-700 flex items-center gap-2">
            <HiCodeBracket className="h-4 w-4 text-gray-400" />
            <span className="text-xs text-gray-400 font-mono">
              Real-time backend output • Auto-scroll enabled
            </span>
          </div>

          <div className="h-64 overflow-y-auto p-3 font-mono text-sm">
            {!runId ? (
              <div className="text-center py-8 text-gray-500">
                <HiCommandLine className="h-8 w-8 mx-auto mb-2 text-gray-600" />
                <p>Backend logs will appear when a crawl is started</p>
              </div>
            ) : (
              <div className="space-y-1">
                {backendLogs.map((log, index) => (
                  <div key={index} className="flex items-start gap-2">
                    <span className="text-gray-500 text-xs whitespace-nowrap">
                      {log.timestamp}
                    </span>
                    <span className={`text-xs font-bold whitespace-nowrap ${getLevelColor(log.level)}`}>
                      {log.level}
                    </span>
                    <span className={`text-xs whitespace-nowrap ${getSourceColor(log.source)}`}>
                      [{log.source}]
                    </span>
                    <span className="text-gray-300 text-xs flex-1">
                      {log.message}
                    </span>
                  </div>
                ))}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}