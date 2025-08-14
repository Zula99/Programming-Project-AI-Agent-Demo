'use client'

import { useState, useId, ChangeEvent } from "react";
import StatusBadge from "./StatusBadge";
import { 
    HiChevronDown,
	HiDownload,
    HiOutlineCheckCircle,
    HiClipboard,
    HiDocumentText,
    HiFilter,
} from "react-icons/hi";
import TabList from "./TabList";
import { HiMagnifyingGlass } from "react-icons/hi2";

type RunStatus = "running" | "complete";
type Tab = "data" | "config" | "logs";

type PageRow = {
    id: string;
    path: string;
    title: string;
    type: "html" | "pdf" | "doc";
    size: number; // KB
};

const mockRun = {
    runId: "RUN-003",
    url: "https://agilent.com",
    status: "running" as RunStatus,
    startedAt: "14 Aug, 2025 10:12am",
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

    return (
        <section className="bg-white border rounded-lg p-4">
            {/*Header*/}
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <h2 className="text-lg font-semibold text-gray-900">Active run</h2>
                    <p className="text-sm text-gray-500">
                        {mockRun.url} | {mockRun.runId}
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <StatusBadge status={mockRun.status} />
                    <span className="hidden sm:inline text-sm text-gray-500">Started {mockRun.startedAt}</span>
                    <CopyButton value={mockRun.runId} />
                </div>
            </div>

            {/*Tabs*/}
            <TabList value={activeTab} onChange={setActiveTab} />

            {/*Panels*/}
            {activeTab === "data" && (
                <div className="mt-4">
                    {/*Toolbar*/}
                    <div className="mb-3 flex flex-wrap items-center gap-2">
                        <div className="flex flex-1 items-center rounded-lg border border-gray-200 bg-white px-3 py-2 shadow-sm hover:border-gray-300">
                            <HiMagnifyingGlass className="mr-2 h-5 w-5 text-gray-400" />
                            <input
                                value={query}
                                onChange={(e: ChangeEvent<HTMLInputElement>) => setQuery(e.target.value)}
                                placeholder="Filter by path, title, or type"
                                className="w-full bg-transparent outline-none placeholder:text-gray-400"
                            />
                        </div>
						<button
							type="button"
							className="inline-flex items-center gap-2 rounded-lg border border-gray-300
										bg-white px-3 py-2 text-gray-700 shadow-sm transition-all 
										hover:bg-gray-50 hover:shadow-md focus-visible:outline-none
										focus-visible:ring-2 focus-visible:ring-blue-500/70 focus-visible:ring-offset-2"
							title="Filters"
						>
							<HiFilter className="h-5 w-5" />
							Filters
						</button>
						<button
							type="button"
							className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-3 py-2 
										font-medium text-white shadow-sm transition-all hover:bg-blue-500 
										hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 
										focus-visible:ring-blue-500/70 focus-visible:ring-offset-2"
							title="Download CSV"
						>
							<HiDownload className="h-5 w-5" />
							CSV
						</button>
                    </div>
                </div>
            )}
        </section>
    );
}

function CopyButton({ value, label = "Copy ID" }: { value: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(value);
          setCopied(true);
          setTimeout(() => setCopied(false), 1200);
        } catch {}
      }}
      className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 shadow-sm transition-all hover:bg-gray-50 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/70 focus-visible:ring-offset-2"
      title={label}
    >
      {copied ? (
        <HiOutlineCheckCircle className="h-5 w-5 text-green-600" />
      ) : (
        <HiClipboard className="h-5 w-5" />
      )}
      <span className="hidden sm:inline">{copied ? "Copied" : label}</span>
    </button>
  );
}