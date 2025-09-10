
import Link from 'next/link';

export default function Header() {
    return (
        <nav className="bg-gray-800 text-white p-2 mt-auto">
            <div className="w-full mx-auto max-w-screen-xl p-1 flex justify-between items-center">
                <div className="text-lg font-semibold">
                    AI Agent Demo
                </div>
                <div className="flex space-x-4">
                    <Link 
                        href="/" 
                        className="hover:text-gray-300 transition-colors"
                    >
                        Dashboard
                    </Link>
                    <Link 
                        href="/logs" 
                        className="hover:text-gray-300 transition-colors"
                    >
                        Crawl Logs
                    </Link>
                </div>
            </div>
        </nav>
    );
}