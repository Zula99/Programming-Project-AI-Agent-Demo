'use client'

import { useState } from "react";
import LoadingSpinner from "./LoadingSpinner";

export default function URLBar() {
    const [url, setUrl] = useState("https://example.com");
    const [isLoading, setIsLoading] = useState(false);

    const handleStartCrawl = () => {
        if (!url.trim()) {
            // Example: Call Toast notification
            if (typeof window !== 'undefined' && (window as any).showToast) {
                (window as any).showToast({
                    type: 'error',
                    message: 'Please enter a valid URL',
                    duration: 3000
                });
            }
            return;
        }

        setIsLoading(true);
        
        // Simulate starting crawl
        setTimeout(() => {
            setIsLoading(false);
            // Example: Success notification
            if (typeof window !== 'undefined' && (window as any).showToast) {
                (window as any).showToast({
                    type: 'success',
                    message: `Started crawling: ${url}`,
                    duration: 4000
                });
            }
        }, 2000);
    };

    const handleCrawlerSettings = () => {
        // Example: Info notification
        if (typeof window !== 'undefined' && (window as any).showToast) {
            (window as any).showToast({
                type: 'info',
                message: 'Crawler settings panel will open here',
                duration: 3000
            });
        }
    };

    return (
        <div className="flex items-center gap-2 mt-4">
            <div className="flex items-center flex-1 bg-white text-gray-300 border rounded-lg px-3 py-2">
                <input
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="flex-1 outline-none"
                    placeholder="Enter URL to crawl..."
                    />
            </div>
            <button
                type="submit"
                onClick={handleStartCrawl}
                disabled={isLoading}
                className="bg-blue-500 text-white px-4 py-2 rounded-lg flex items-center gap-2
                            hover:shadow-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed">
                {isLoading ? (
                    <>
                        <LoadingSpinner size="sm" color="white" />
                        Starting...
                    </>
                ) : (
                    'Start crawl'
                )}
            </button>
            <button 
                onClick={handleCrawlerSettings}
                className="border bg-gray-200 text-gray-500 px-3 py-2 rounded-lg
                            hover:shadow-lg hover:bg-gray-300 hover:text-gray-700">
                Crawler settings
            </button>
        </div>
    );
}