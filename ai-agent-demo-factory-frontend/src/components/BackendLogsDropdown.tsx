'use client'

import { useState, useEffect, useRef } from "react";
import { HiChevronDown, HiChevronUp, HiCodeBracket, HiCommandLine, HiMagnifyingGlass } from "react-icons/hi2";

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
  const [searchQuery, setSearchQuery] = useState("");
  const [autoScroll, setAutoScroll] = useState(true);
  const logsEndRef = useRef<HTMLDivElement>(null);
  const logsContainerRef = useRef<HTMLDivElement>(null);
  const isAutoScrollingRef = useRef(false); // Track programmatic scrolling

  // Auto-scroll to bottom only if user is at the bottom
  useEffect(() => {
    if (isExpanded && autoScroll) {
      isAutoScrollingRef.current = true; // Mark as programmatic scroll
      logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });

      // Reset flag after scroll animation completes (smooth scrolling takes ~300-500ms)
      setTimeout(() => {
        isAutoScrollingRef.current = false;
      }, 600);
    }
  }, [backendLogs, isExpanded, autoScroll]);

  // Detect if user scrolled away from bottom (ignore programmatic scrolls)
  const handleScroll = () => {
    // Ignore scroll events triggered by our auto-scroll
    if (isAutoScrollingRef.current) return;

    if (!logsContainerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = logsContainerRef.current;
    const isAtBottom = Math.abs(scrollHeight - scrollTop - clientHeight) <= 5; // 5px tolerance for rounding

    setAutoScroll(isAtBottom);
  };

  // Filter logs based on search query
  const filteredLogs = backendLogs.filter(log =>
    searchQuery === "" ||
    log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
    log.level.toLowerCase().includes(searchQuery.toLowerCase()) ||
    log.source.toLowerCase().includes(searchQuery.toLowerCase()) ||
    log.timestamp.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getLevelColor = (level: string) => {
    switch (level) {
      case "ERROR": return "text-red-400";
      case "WARNING": return "text-yellow-400";
      case "DEBUG": return "text-gray-700";
      default: return "text-green-400";
    }
  };

  const getSourceColor = (source: string) => {
    switch (source) {
      case "uvicorn": return "text-blue-400";
      case "main": return "text-purple-400";
      case "crawler": return "text-cyan-400";
      case "indexer": return "text-orange-400";
      case "schema_processor": return "text-pink-400";
      default: return "text-gray-700";
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
            <span className="text-xs text-gray-700">
              {isConnected ? 'Live' : 'Disconnected'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-700">
            {backendLogs.length} entries
          </span>
          {isExpanded ? (
            <HiChevronUp className="h-5 w-5 text-gray-700" />
          ) : (
            <HiChevronDown className="h-5 w-5 text-gray-700" />
          )}
        </div>
      </button>

      {/* Expandable Content */}
      {isExpanded && (
        <div className="border-t bg-gray-900 rounded-b-lg">
          <div className="p-3 bg-gray-800 border-b border-gray-700 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <HiCodeBracket className="h-4 w-4 text-gray-400" />
              <span className="text-xs text-gray-300 font-mono">
                Real-time backend output • Auto-scroll {autoScroll ? 'enabled' : 'paused'}
              </span>
            </div>

            {/* Search Bar */}
            <div className="flex items-center gap-2 bg-gray-700 rounded px-3 py-1.5">
              <HiMagnifyingGlass className="h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search logs..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-transparent text-gray-200 text-xs font-mono outline-none w-64 placeholder-gray-400"
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery("")}
                  className="text-gray-300 hover:text-gray-100 text-xs"
                >
                  Clear
                </button>
              )}
            </div>
          </div>

          <div
            ref={logsContainerRef}
            onScroll={handleScroll}
            className="h-96 overflow-y-auto p-3 font-mono text-sm"
          >
            {!runId ? (
              <div className="text-center py-8 text-gray-400">
                <HiCommandLine className="h-8 w-8 mx-auto mb-2 text-gray-500" />
                <p>Backend logs will appear when a crawl is started</p>
              </div>
            ) : (
              <div className="space-y-1">
                {filteredLogs.map((log, index) => (
                  <div key={index} className="flex items-start gap-2">
                    <span className="text-gray-400 text-xs whitespace-nowrap">
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
                {filteredLogs.length === 0 && backendLogs.length > 0 && (
                  <div className="text-center py-8 text-gray-400">
                    <HiMagnifyingGlass className="h-8 w-8 mx-auto mb-2 text-gray-500" />
                    <p>No logs match your search query</p>
                  </div>
                )}
                <div ref={logsEndRef} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
