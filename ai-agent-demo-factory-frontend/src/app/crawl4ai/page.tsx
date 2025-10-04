'use client'

import { useState, useEffect, useRef } from "react";
import Header from "@/components/Header";
import Crawl4AIUrlBar from "@/components/Crawl4AIUrlBar";
import AgentOutputCard from "@/components/AgentOutputCard";
import CrawlProgressPanel from "@/components/CrawlProgressPanel";
import BackendLogsDropdown from "@/components/BackendLogsDropdown";
import { startCrawl4AI, stopCrawl4AI, createWebSocketConnection, type AgentLog, type StopSummary } from "@/lib/crawl4ai-api";

type AgentStatus = "idle" | "pending" | "running" | "waiting_for_input" | "completed" | "error" | "stopped";

interface CrawlProgress {
  percentage: number;
  pages_crawled: number;
  pages_remaining: number;
  total_pages: number;
  estimated_time_remaining: number;
  crawl_speed: number;
  ai_classifications: number;
  cache_hits: number;
  loaded_caches: number;
}

interface BackendLogEntry {
  timestamp: string;
  level: "INFO" | "WARNING" | "ERROR" | "DEBUG";
  message: string;
  source: string;
}

export default function Crawl4AIPage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<AgentStatus>("idle");
  const [isConnected, setIsConnected] = useState(false);
  const [logs, setLogs] = useState<AgentLog[]>([]);
  const [backendLogs, setBackendLogs] = useState<BackendLogEntry[]>([]);
  const [stopSummary, setStopSummary] = useState<StopSummary | null>(null);
  const [showStopModal, setShowStopModal] = useState(false);
  const [progress, setProgress] = useState<CrawlProgress>({
    percentage: 0,
    pages_crawled: 0,
    pages_remaining: 0,
    total_pages: 0,
    estimated_time_remaining: 0,
    crawl_speed: 0,
    ai_classifications: 0,
    cache_hits: 0,
    loaded_caches: 0
  });
  const wsRef = useRef<WebSocket | null>(null);

  // Handle starting a new crawl
  const handleStartCrawl = async (url: string) => {
    try {
      const response = await startCrawl4AI(url);
      setRunId(response.run_id);
      setStatus("running");
      setLogs([]);
      setBackendLogs([]);

      // Reset progress
      setProgress({
        percentage: 0,
        pages_crawled: 0,
        pages_remaining: 0,
        total_pages: 0,
        estimated_time_remaining: 0,
        crawl_speed: 0,
        ai_classifications: 0,
        cache_hits: 0,
        loaded_caches: 0
      });

      // Establish WebSocket connection with a slight delay
      setTimeout(() => {
        connectWebSocket(response.run_id);
      }, 500);
    } catch (error) {
      console.error("Failed to start Crawl4AI:", error);
      alert("Failed to start Crawl4AI agent. Please try again.");
    }
  };

  // Handle stopping a crawl
  const handleStopCrawl = async () => {
    if (!runId) return;

    try {
      // Send stop request and get summary
      const response = await stopCrawl4AI(runId);

      // Store summary
      setStopSummary(response.summary);

      // Add summary logs to the output
      const summary = response.summary;
      const summaryLogs: AgentLog[] = [
        { timestamp: new Date().toLocaleTimeString(), message: "═══════════════════════════════════════", type: "info" },
        { timestamp: new Date().toLocaleTimeString(), message: "CRAWL STOPPED - SESSION SUMMARY", type: "warning" },
        { timestamp: new Date().toLocaleTimeString(), message: "═══════════════════════════════════════", type: "info" },
        { timestamp: new Date().toLocaleTimeString(), message: "", type: "info" },
        { timestamp: new Date().toLocaleTimeString(), message: `📊 Progress: ${summary.pages_crawled} of ${summary.total_pages} pages (${summary.percentage.toFixed(1)}%)`, type: "info" },
        { timestamp: new Date().toLocaleTimeString(), message: `⏱️  Duration: ${summary.elapsed_time}`, type: "info" },
        { timestamp: new Date().toLocaleTimeString(), message: `📦 Cache Hits: ${summary.cache_hits}`, type: "info" },
        { timestamp: new Date().toLocaleTimeString(), message: `🤖 AI Classifications: ${summary.ai_classifications}`, type: "info" },
        { timestamp: new Date().toLocaleTimeString(), message: "", type: "info" },
        { timestamp: new Date().toLocaleTimeString(), message: `🎯 Target URL: ${summary.target_url}`, type: "info" },
        { timestamp: new Date().toLocaleTimeString(), message: `📍 Last URL: ${summary.current_url}`, type: "info" },
        { timestamp: new Date().toLocaleTimeString(), message: "", type: "info" },
        { timestamp: new Date().toLocaleTimeString(), message: "═══════════════════════════════════════", type: "info" },
      ];

      setLogs(prev => [...prev, ...summaryLogs]);

      // Update UI
      setStatus("stopped");

      console.log("Crawl force stopped with summary:", response.summary);
    } catch (error) {
      console.error("Failed to stop crawl:", error);
      // Fallback: still update UI even if stop request fails
      setStatus("stopped");
    }
  };


  // Connect to WebSocket for live updates
  const connectWebSocket = (sessionRunId: string) => {
    try {
      // Close existing connection
      if (wsRef.current) {
        wsRef.current.close();
      }

      const ws = createWebSocketConnection(
        sessionRunId,
        // On new log message
        (log) => {
          setLogs(prev => [...prev, log]);
        },
        // On status change
        (newStatus) => {
          setStatus(newStatus);
        },
        // On error
        (error) => {
          console.warn("WebSocket error (non-critical):", error);
          setIsConnected(false);
        }
      );

      ws.onopen = () => {
        setIsConnected(true);
        console.log("WebSocket connected successfully");
      };

      ws.onclose = () => {
        setIsConnected(false);
        console.log("WebSocket disconnected");
      };

      // Handle status updates and questions from WebSocket
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'log') {
            setLogs(prev => [...prev, data.log]);
          } else if (data.type === 'status') {
            setStatus(data.status);
          } else if (data.type === 'progress') {
            setProgress(data.progress);
          } else if (data.type === 'backend_log') {
            setBackendLogs(prev => [...prev, data.log]); // Keep all logs
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.warn("Failed to establish WebSocket connection:", error);
      setIsConnected(false);
    }
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <Header />
      <Crawl4AIUrlBar
        onStartCrawl={handleStartCrawl}
        onStopCrawl={handleStopCrawl}
        isRunning={status === "running"}
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        {/* Left: Progress Panel */}
        <div className="md:col-span-1 space-y-4">
          {/* Progress panel shows crawl statistics */}
          <CrawlProgressPanel
            runId={runId}
            progress={progress}
            status={status}
          />

        </div>

        {/* Right: Agent Output */}
        <div className="md:col-span-2 space-y-4">
          <AgentOutputCard
            runId={runId}
            isConnected={isConnected}
            status={status}
            logs={logs}
            backendLogs={backendLogs}
          />
        </div>
      </div>

      {/* Backend Logs Dropdown - Full Width */}
      <div className="mt-6">
        <BackendLogsDropdown
          runId={runId}
          isConnected={isConnected}
          backendLogs={backendLogs}
        />
      </div>
    </main>
  );
}