'use client'

import { useState, useEffect, useRef } from "react";
import { HiOutlineCheckCircle, HiOutlineXCircle, HiClock } from "react-icons/hi";

interface AgentOutputCardProps {
  runId?: string | null;
  isConnected?: boolean;
  status?: "idle" | "running" | "waiting_for_input" | "completed" | "error";
  logs?: LogEntry[];
}

interface LogEntry {
  timestamp: string;
  message: string;
  type: "info" | "success" | "warning" | "error" | "question";
}

export default function AgentOutputCard({
  runId,
  isConnected = false,
  status = "idle",
  logs = []
}: AgentOutputCardProps) {
    const logsEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new logs arrive
    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [logs]);

    const getStatusIcon = () => {
        switch (status) {
            case "running":
                return <HiClock className="h-5 w-5 text-blue-500 animate-spin" />;
            case "completed":
                return <HiOutlineCheckCircle className="h-5 w-5 text-green-500" />;
            case "error":
                return <HiOutlineXCircle className="h-5 w-5 text-red-500" />;
            case "waiting_for_input":
                return <HiClock className="h-5 w-5 text-yellow-500" />;
            default:
                return <HiClock className="h-5 w-5 text-gray-400" />;
        }
    };

    const getStatusText = () => {
        switch (status) {
            case "running":
                return "Agent Running";
            case "completed":
                return "Completed";
            case "error":
                return "Error";
            case "waiting_for_input":
                return "Waiting for Input";
            default:
                return "Ready";
        }
    };

    const getLogTypeColor = (type: LogEntry["type"]) => {
        switch (type) {
            case "success":
                return "text-green-400";
            case "warning":
                return "text-yellow-400";
            case "error":
                return "text-red-400";
            case "question":
                return "text-blue-400";
            default:
                return "text-gray-300";
        }
    };

    return (
        <section className="bg-white border rounded-lg p-4">
            {/* Header */}
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div>
                    <h2 className="text-lg font-semibold text-gray-900">Crawl4AI Agent Output</h2>
                    <p className="text-sm text-gray-500">
                        {runId ? `Run ID: ${runId}` : "No active session"}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    {getStatusIcon()}
                    <span className="text-sm font-medium text-gray-700">
                        {getStatusText()}
                    </span>
                    {isConnected && (
                        <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-100 px-2 py-1 rounded-full">
                            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                            Live
                        </span>
                    )}
                </div>
            </div>

            {/* Agent Output Terminal */}
            <div className="bg-black rounded-lg p-4 h-96 overflow-auto font-mono text-sm">
                {logs.length === 0 ? (
                    <div className="text-gray-500 text-center py-8">
                        Agent output will appear here when a crawl is started...
                    </div>
                ) : (
                    <div className="space-y-1">
                        {logs.map((log, index) => (
                            <div key={index} className="flex gap-2">
                                <span className="text-gray-500 text-xs min-w-[60px]">
                                    {log.timestamp}
                                </span>
                                <span className={getLogTypeColor(log.type)}>
                                    {log.message}
                                </span>
                            </div>
                        ))}
                        <div ref={logsEndRef} />
                    </div>
                )}
            </div>

            {/* Connection Status */}
            <div className="mt-3 text-xs text-gray-500 flex items-center justify-between">
                <span>
                    WebSocket: {isConnected ? "Connected" : "Disconnected"}
                </span>
                <span>
                    {logs.length} log {logs.length === 1 ? "entry" : "entries"}
                </span>
            </div>
        </section>
    );
}