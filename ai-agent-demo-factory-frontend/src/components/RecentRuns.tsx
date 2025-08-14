'use client'

import StatusBadge from "./StatusBadge";
import { useCrawler } from "@/hooks/useCrawler";
import { HiClock, HiDocumentText, HiCalendar } from "react-icons/hi";

export default function RecentRuns() {
    const { recentRuns, currentRun } = useCrawler();

    const formatTime = (timeString: string) => {
        try {
            const date = new Date(timeString);
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch {
            return timeString;
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'running':
                return 'text-blue-600';
            case 'complete':
                return 'text-green-600';
            case 'error':
                return 'text-red-600';
            default:
                return 'text-gray-600';
        }
    };

    return (
        <div className="bg-white rounded-lg border shadow-sm">
            <div className="p-4 border-b">
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                    <HiClock className="w-5 h-5 text-blue-500" />
                    Recent Runs
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                    Shows recent crawler task execution status
                </p>
            </div>
            
            <div className="p-4">
                {recentRuns.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                        <HiDocumentText className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                        <p>No run records yet</p>
                        <p className="text-sm">Start your first crawler task!</p>
                    </div>
                ) : (
                    <ul className="space-y-3">
                        {recentRuns.map((run) => (
                            <li 
                                key={run.id} 
                                className={`p-3 rounded-lg border transition-all duration-200 hover:shadow-md cursor-pointer ${
                                    currentRun?.id === run.id 
                                        ? 'border-blue-300 bg-blue-50' 
                                        : 'border-gray-200 hover:border-gray-300'
                                }`}
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <div className="flex-1 min-w-0">
                                        <p className={`font-medium truncate ${getStatusColor(run.status)}`}>
                                            {run.url}
                                        </p>
                                        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                                            <span className="flex items-center gap-1">
                                                <HiCalendar className="w-3 h-3" />
                                                {formatTime(run.startedAt)}
                                            </span>
                                            <span className="flex items-center gap-1">
                                                <HiDocumentText className="w-3 h-3" />
                                                {run.pages} pages
                                            </span>
                                        </div>
                                    </div>
                                    <StatusBadge status={run.status} />
                                </div>
                                
                                <div className="flex items-center justify-between text-xs">
                                    <span className="text-gray-500 font-mono">
                                        {run.id}
                                    </span>
                                    {run.completedAt && run.status === 'complete' && (
                                        <span className="text-green-600">
                                            Completed at {formatTime(run.completedAt)}
                                        </span>
                                    )}
                                </div>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    );
}