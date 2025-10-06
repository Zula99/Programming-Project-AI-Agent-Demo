'use client'

import { useState } from "react";

interface Crawl4AIUrlBarProps {
  onStartCrawl?: (url: string, maxPages?: number) => void;
  onStopCrawl?: () => void;
  isRunning?: boolean;
}

export default function Crawl4AIUrlBar({ onStartCrawl, onStopCrawl, isRunning = false }: Crawl4AIUrlBarProps) {
    const [url, setUrl] = useState("https://example.com");
    const [maxPages, setMaxPages] = useState<string>("");

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (onStartCrawl && url.trim() && !isRunning) {
            const pages = maxPages.trim() ? parseInt(maxPages) : undefined;
            onStartCrawl(url.trim(), pages);
        }
    };

    const handleStop = () => {
        if (onStopCrawl && isRunning) {
            onStopCrawl();
        }
    };

    return (
        <div className="space-y-2 mt-4">
            <form onSubmit={handleSubmit} className="flex items-center gap-2">
                <div className="flex items-center flex-1 bg-white text-gray-700 border rounded-lg px-3 py-2">
                    <input
                        type="url"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="Enter website URL to crawl..."
                        className="flex-1 outline-none"
                        disabled={isRunning}
                        required
                        suppressHydrationWarning={true}
                    />
                </div>
                <button
                type="submit"
                disabled={isRunning || !url.trim()}
                suppressHydrationWarning={true}
                className={`px-4 py-2 rounded-lg flex items-center gap-1 font-medium transition-all
                    ${isRunning || !url.trim()
                        ? 'bg-gray-400 text-gray-200 cursor-not-allowed'
                        : 'bg-blue-500 text-white hover:shadow-lg hover:bg-blue-700'
                    }`}
            >
                {isRunning ? 'Running...' : 'Start Crawl4AI Agent'}
            </button>

                {isRunning && (
                    <button
                        type="button"
                        onClick={handleStop}
                        suppressHydrationWarning={true}
                        className="px-4 py-2 rounded-lg flex items-center gap-1 font-medium transition-all bg-red-500 text-white hover:shadow-lg hover:bg-red-700"
                    >
                        End Crawl
                    </button>
                )}
            </form>

            {/* Max Pages Control */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-4 shadow-sm">
                <div className="flex items-center gap-4">
                    <div className="flex-shrink-0">
                        <label className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                            <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                            Max Pages
                        </label>
                    </div>
                    <div className="flex-1 flex items-center gap-3">
                        <input
                            type="number"
                            value={maxPages}
                            onChange={(e) => setMaxPages(e.target.value)}
                            placeholder="Auto"
                            className="w-32 px-4 py-2 bg-white text-gray-700 border-2 border-gray-300 rounded-lg outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-all disabled:bg-gray-100 disabled:cursor-not-allowed font-medium text-center"
                            disabled={isRunning}
                            min="1"
                            max="10000"
                        />
                        <div className="flex-1">
                            <p className="text-xs text-gray-600 leading-relaxed">
                                <span className="font-medium text-gray-700">Optional:</span> Leave empty for intelligent auto-stopping
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}