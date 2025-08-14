'use client'

// Find HeroIcons here: https://react-icons.github.io/react-icons/icons/hi/
import StatusBadge from "./StatusBadge";
import TabList from "./TabList";
import SortableTH from "./SortableTH";
import { useMemo, useState, ChangeEvent } from "react";
import { useCrawler } from "@/hooks/useCrawler";
import { 
	HiDownload,
    HiOutlineCheckCircle,
    HiClipboard,
    HiFilter,
    HiStop,
    HiPlay,
    HiRefresh,
} from "react-icons/hi";
import { HiArrowPath, HiMagnifyingGlass } from "react-icons/hi2";

type Tab = "data" | "config" | "logs";

type PageRow = {
    id: string;
    path: string;
    title: string;
    type: "html" | "pdf" | "doc";
    size: number; // KB
};

const initialRows: PageRow[] = [
    { id: "1", path: "/", title: "Home", type: "html", size: 18_322 },
    { id: "2", path: "/pricing", title: "Pricing", type: "html", size: 25_101 },
    { id: "3", path: "/about", title: "About", type: "html", size: 19_552 },
]

function formatKB(bytes: number) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export default function ActiveRun() {
    const [activeTab, setActiveTab] = useState<Tab>("data");
    const [query, setQuery] = useState("");
	const [sortKey, setSortKey] = useState<keyof Pick<PageRow, "path" | "title" | "type" | "size">>("path");
    const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
    
    const { currentRun, stopCrawl } = useCrawler();

	const filtered = useMemo(() => {
    	const q = query.trim().toLowerCase();
    	const rows = q
    	  ? initialRows.filter(
    	      (r) =>
    	        r.path.toLowerCase().includes(q) ||
    	        r.title.toLowerCase().includes(q) ||
    	        r.type.toLowerCase().includes(q)
    	    )
    	  : initialRows;

    	const sorted = [...rows].sort((a, b) => {
    	  const av = a[sortKey];
    	  const bv = b[sortKey];
    	  if (typeof av === "number" && typeof bv === "number") {
    	    return sortDir === "asc" ? av - bv : bv - av;
    	  }
    	  const as = String(av).toLowerCase();
    	  const bs = String(bv).toLowerCase();
    	  return sortDir === "asc" ? as.localeCompare(bs) : bs.localeCompare(as);
    	});

    	return sorted;
  	}, [query, sortKey, sortDir]);

    const toggleSort = (key: keyof Pick<PageRow, "path" | "title" | "type" | "size">) => {
        if (key === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
        else {
            setSortKey(key);
            setSortDir("asc");
        }
    };

    const handleStopCrawl = async () => {
        if (currentRun) {
            await stopCrawl();
        }
    };

    // If no current running task, show empty state
    if (!currentRun) {
        return (
            <section className="bg-white border rounded-lg p-8 text-center">
                <HiPlay className="w-16 h-16 mx-auto mb-4 text-gray-300" />
                <h2 className="text-xl font-semibold text-gray-900 mb-2">No Active Task</h2>
                <p className="text-gray-500 mb-6">
                    Enter a website URL in the URL bar and click "Start crawl" to begin a new crawler task
                </p>
                <div className="inline-flex items-center gap-2 text-sm text-gray-400">
                    <HiRefresh className="w-4 h-4" />
                    <span>Waiting for new task to start...</span>
                </div>
            </section>
        );
    }

    return (
        <section className="bg-white border rounded-lg p-4">
            {/*Header*/}
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div>
                    <h2 className="text-lg font-semibold text-gray-900">Active Task</h2>
                    <p className="text-sm text-gray-500">
                        {currentRun.url} | {currentRun.id}
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    <StatusBadge status={currentRun.status} />
                    <span className="hidden sm:inline text-sm text-gray-500">
                        Started at {currentRun.startedAt}
                    </span>
                    <button
                        onClick={handleStopCrawl}
                        className="flex items-center gap-2 px-3 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors duration-200"
                    >
                        <HiStop className="w-4 h-4" />
                        Stop Task
                    </button>
                </div>
            </div>

            {/* Progress information */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-blue-800">Crawling Progress</span>
                    <span className="text-sm text-blue-600">{currentRun.pages} pages processed</span>
                </div>
                <div className="w-full bg-blue-200 rounded-full h-2">
                    <div 
                        className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                        style={{ width: `${Math.min((currentRun.pages / 100) * 100, 100)}%` }}
                    ></div>
                </div>
                <p className="text-xs text-blue-600 mt-2">
                    Currently crawling page content from {currentRun.url}...
                </p>
            </div>

            {/*Tabs*/}
            <TabList 
                activeTab={activeTab} 
                onTabChange={setActiveTab}
                tabs={[
                    { id: "data", label: "Data", count: filtered.length },
                    { id: "config", label: "Config", count: 0 },
                    { id: "logs", label: "Logs", count: 0 }
                ]}
            />

            {/* Tab Content */}
            {activeTab === "data" && (
                <div className="mt-4">
                    {/* Search and Filter */}
                    <div className="flex items-center gap-4 mb-4">
                        <div className="flex items-center flex-1 bg-gray-100 rounded-lg px-3 py-2">
                            <HiMagnifyingGlass className="w-4 h-4 text-gray-400 mr-2" />
                            <input
                                type="text"
                                placeholder="Search pages..."
                                value={query}
                                onChange={(e: ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
                                className="flex-1 bg-transparent outline-none text-sm"
                            />
                        </div>
                        <button className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:text-gray-800 transition-colors">
                            <HiFilter className="w-4 h-4" />
                            Filter
                        </button>
                    </div>

                    {/* Data Table */}
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b">
                                    <SortableTH
                                        label="Path"
                                        sortKey="path"
                                        currentSort={sortKey}
                                        sortDir={sortDir}
                                        onSort={toggleSort}
                                    />
                                    <SortableTH
                                        label="Title"
                                        sortKey="title"
                                        currentSort={sortKey}
                                        sortDir={sortDir}
                                        onSort={toggleSort}
                                    />
                                    <SortableTH
                                        label="Type"
                                        sortKey="type"
                                        currentSort={sortKey}
                                        sortDir={sortDir}
                                        onSort={toggleSort}
                                    />
                                    <SortableTH
                                        label="Size"
                                        sortKey="size"
                                        currentSort={sortKey}
                                        sortDir={sortDir}
                                        onSort={toggleSort}
                                    />
                                    <th className="text-left py-2 px-3 text-gray-500 font-medium">Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filtered.map((row) => (
                                    <tr key={row.id} className="border-b hover:bg-gray-50">
                                        <td className="py-2 px-3 font-mono text-xs">{row.path}</td>
                                        <td className="py-2 px-3">{row.title}</td>
                                        <td className="py-2 px-3">
                                            <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                                                {row.type.toUpperCase()}
                                            </span>
                                        </td>
                                        <td className="py-2 px-3 text-gray-600">{formatKB(row.size)}</td>
                                        <td className="py-2 px-3">
                                            <div className="flex items-center gap-2">
                                                <button className="p-1 hover:bg-gray-200 rounded transition-colors">
                                                    <HiDownload className="w-4 h-4 text-gray-600" />
                                                </button>
                                                <button className="p-1 hover:bg-gray-200 rounded transition-colors">
                                                    <HiClipboard className="w-4 h-4 text-gray-600" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {activeTab === "config" && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <p className="text-gray-500 text-center">Configuration information will be displayed here</p>
                </div>
            )}

            {activeTab === "logs" && (
                <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <p className="text-gray-500 text-center">Log information will be displayed here</p>
                </div>
            )}
        </section>
    );
}