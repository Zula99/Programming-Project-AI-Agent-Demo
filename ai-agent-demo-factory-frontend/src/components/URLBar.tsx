'use client'

import { useState } from "react";
import { useCrawler } from "@/hooks/useCrawler";
import { HiPlay, HiStop, HiCog, HiCheckCircle, HiExclamationCircle } from "react-icons/hi";

export default function URLBar() {
    const [url, setUrl] = useState("https://example.com");
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState<string | null>(null);
    
    const { startCrawl, stopCrawl, currentRun, isStarting } = useCrawler();

    const handleStartCrawl = async () => {
        setError(null);
        setSuccess(null);
        
        const result = await startCrawl(url);
        
        if (result.success) {
            setSuccess("Crawler task started successfully!");
            // Clear success message after 3 seconds
            setTimeout(() => setSuccess(null), 3000);
        } else {
            setError(result.error || "Start failed");
            // Clear error message after 5 seconds
            setTimeout(() => setError(null), 5000);
        }
    };

    const handleStopCrawl = async () => {
        setError(null);
        setSuccess(null);
        
        const result = await stopCrawl();
        
        if (result.success) {
            setSuccess("Crawler task stopped successfully!");
            setTimeout(() => setSuccess(null), 3000);
        } else {
            setError(result.error || "Stop failed");
            setTimeout(() => setError(null), 5000);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !isStarting && !currentRun) {
            handleStartCrawl();
        }
    };

    const isRunning = currentRun?.status === "running";
    const canStart = !isStarting && !isRunning && url.trim();

    return (
        <div className="space-y-3 mt-4">
            {/* URL input and buttons */}
            <div className="flex items-center gap-2">
                <div className="flex items-center flex-1 bg-white border rounded-lg px-3 py-2 focus-within:ring-2 focus-within:ring-blue-500 focus-within:border-blue-500">
                    <input
                        type="text"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Enter website URL to crawl..."
                        className="flex-1 outline-none text-gray-700 placeholder-gray-400"
                        disabled={isStarting || isRunning}
                    />
                </div>
                
                {/* Start/Stop button */}
                {!isRunning ? (
                    <button 
                        onClick={handleStartCrawl}
                        disabled={!canStart}
                        className={`px-4 py-2 rounded-lg flex items-center gap-2 font-medium transition-all duration-200 ${
                            canStart 
                                ? 'bg-blue-500 text-white hover:bg-blue-600 hover:shadow-lg' 
                                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                        }`}
                    >
                        <HiPlay className="w-4 h-4" />
                        {isStarting ? 'Starting...' : 'Start crawl'}
                    </button>
                ) : (
                    <button 
                        onClick={handleStopCrawl}
                        className="px-4 py-2 rounded-lg flex items-center gap-2 bg-red-500 text-white hover:bg-red-600 hover:shadow-lg font-medium transition-all duration-200"
                    >
                        <HiStop className="w-4 h-4" />
                        Stop crawl
                    </button>
                )}
                
                {/* Settings button */}
                <button className="border bg-gray-200 text-gray-500 px-3 py-2 rounded-lg hover:shadow-lg hover:bg-gray-300 hover:text-gray-700 transition-all duration-200 flex items-center gap-2">
                    <HiCog className="w-4 h-4" />
                    Crawler settings
                </button>
            </div>

            {/* Status and message display */}
            <div className="flex items-center gap-4">
                {/* Current status */}
                {currentRun && (
                    <div className="flex items-center gap-2 text-sm">
                        <span className="text-gray-600">Current task:</span>
                        <span className="font-medium text-blue-600">{currentRun.url}</span>
                        <span className="text-gray-500">|</span>
                        <span className="text-gray-600">ID: {currentRun.id}</span>
                        <span className="text-gray-500">|</span>
                        <span className="text-gray-600">Pages crawled: {currentRun.pages}</span>
                    </div>
                )}

                {/* Success message */}
                {success && (
                    <div className="flex items-center gap-2 text-green-600 bg-green-50 px-3 py-2 rounded-lg">
                        <HiCheckCircle className="w-4 h-4" />
                        <span className="text-sm font-medium">{success}</span>
                    </div>
                )}

                {/* Error message */}
                {error && (
                    <div className="flex items-center gap-2 text-red-600 bg-red-50 px-3 py-2 rounded-lg">
                        <HiExclamationCircle className="w-4 h-4" />
                        <span className="text-sm font-medium">{error}</span>
                    </div>
                )}
            </div>
        </div>
    );
}