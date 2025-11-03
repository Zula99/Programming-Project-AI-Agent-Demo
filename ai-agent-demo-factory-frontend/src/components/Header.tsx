
import Link from "next/link";

export default function Header() {

    return (
        <nav className="bg-gray-800 text-white p-2 mt-auto">
            <div className="w-full mx-auto max-w-screen-xl p-1 flex items-center justify-between">
                <div className="text-lg font-semibold">AI Agent Demo</div>
                <div className="flex items-center gap-4">
                    <Link
                        href="/"
                        className="text-gray-300 hover:text-white transition-colors px-3 py-1 rounded"
                    >
                        Norconex Crawler
                    </Link>
                    <Link
                        href="/crawl4ai"
                        className="text-gray-300 hover:text-white transition-colors px-3 py-1 rounded"
                    >
                        Crawl4AI Agent
                    </Link>
                    <Link
                        href="/logs"
                        className="text-gray-300 hover:text-white transition-colors px-3 py-1 rounded"
                    >
                        Norconex Logs
                    </Link>
                </div>
            </div>
        </nav>
    );
}