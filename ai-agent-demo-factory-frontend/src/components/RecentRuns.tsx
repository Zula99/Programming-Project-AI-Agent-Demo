'use client'

import StatusBadge from "./StatusBadge";
import Tooltip from "./Tooltip";
import LoadingSpinner from "./LoadingSpinner";

type RunStatus = "complete" | "running";
type Run = {
    url: string;
    runId: string;
    pages: number;
    status: RunStatus;
}

const runs: Run[] = [
    { url: "https://example.com", runId: "RUN-001", pages: 42, status: "complete" },
    { url: "https://nab.com.au", runId: "RUN-002", pages: 1002, status: "complete" },
    { url: "https://agilent.com", runId: "RUN-003", pages: 5, status: "running" }
];

export default function RecentRuns() {
    return (
        <div className="bg-white text-gray-400 p-4 rounded-lg border">
            <div className="flex items-center justify-between mb-3">
                <h2 className="font-medium">Recent runs</h2>
                {/* Example: Using LoadingSpinner */}
                <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500">Live updates</span>
                    <LoadingSpinner size="sm" color="blue" />
                </div>
            </div>
            
            <ul className="space-y-3">
                {runs.map((run) => (
                    <li key={run.runId} className="flex justify-between items-center">
                        <div>
                            {/* Example: Using Tooltip */}
                            <Tooltip content={`Run ID: ${run.runId}`} position="top">
                                <p className="text-blue-500 cursor-help">{run.url}</p>
                            </Tooltip>
                            <p className="text-sm text-gray-500">
                                {run.runId} | {run.pages} pages
                            </p>
                        </div>
                        <StatusBadge status={run.status} />
                    </li>
                ))}
            </ul>
            
            {/* Example: Using Tooltip wrapper for button */}
            <div className="mt-4 pt-3 border-t border-gray-200">
                <Tooltip content="View all previous runs and their results" position="top">
                    <button className="w-full text-center text-sm text-blue-500 hover:text-blue-700 py-2 px-3 rounded border border-blue-200 hover:border-blue-300 transition-colors">
                        View All Runs
                    </button>
                </Tooltip>
            </div>
        </div>
    );
}