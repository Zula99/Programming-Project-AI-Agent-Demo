'use client'

import { useState } from "react";

export default function URLBar() {
    const [url, setUrl] = useState("https://example.com");

    return (
        <div className="flex items-center gap-2 mt-4">
            <div className="flex items-center flex-1 bg-white text-gray-300 border rounded-lg px-3 py-2">
                <input
                    type="text"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className="flex-1 outline-none"
                    />
            </div>
            <button 
                type="submit"
                className="bg-blue-500 text-white px-4 py-2 rounded-lg flex items-center gap-1 
                            hover:shadow-lg hover:bg-blue-700">
                Start crawl
            </button>
            <button className="border bg-gray-200 text-gray-500 px-3 py-2 rounded-lg
                                hover:shadow-lg hover:bg-gray-300 hover:text-gray-700">
                Crawler settings
            </button>
        </div>
    );
}