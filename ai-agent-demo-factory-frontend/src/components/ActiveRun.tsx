'use client'

// Find HeroIcons here: https://react-icons.github.io/react-icons/icons/hi/
import StatusBadge from "./StatusBadge";
import TabList from "./TabList";
import SortableTH from "./SortableTH";
import { useMemo, useState, ChangeEvent } from "react";
import { 
	HiDownload,
    HiOutlineCheckCircle,
    HiClipboard,
    HiFilter,
} from "react-icons/hi";
import { HiArrowPath, HiMagnifyingGlass } from "react-icons/hi2";

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
	const [sortKey, setSortKey] = useState<keyof Pick<PageRow, "path" | "title" | "type" | "size">>("path");
    const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

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

					{/*Count*/}
					<div className="mb-2 flex items-center justify-between">
						<div className="text-sm text-gray-500">
							<span className="font-medium text-gray-900">Indexed Pages</span>
						</div>
						<div className="flex items-center gap-2 text-xs text-gray-500">
							<HiArrowPath className="h-4 w-4" />
							updating...
						</div>
					</div>

					{/*Table*/}
					<div className="overflow-hidden rounded-lg border">
						<div className="max-h-[420px] overflow-auto">
							<table className="min-w-full text-sm">
								<thead className="sticky top-0 bg-gray-50 text-left text-gray-600">
									<tr className="[&>th]:py-2 [&>th]:px-3">
										<SortableTH
											label="Path"
											active={sortKey === "path"}
											dir={sortKey === "path" ? sortDir : undefined}
											onClick={() => toggleSort("path")}
										/>
										<SortableTH
											label="Title"
											active={sortKey === "title"}
											dir={sortKey === "title" ? sortDir : undefined}
											onClick={() => toggleSort("title")}
										/>
										<SortableTH
											label="Type"
											active={sortKey === "type"}
											dir={sortKey === "type" ? sortDir : undefined}
											onClick={() => toggleSort("type")}
										/>
										<SortableTH
											label="Size"
											active={sortKey === "size"}
											dir={sortKey === "size" ? sortDir : undefined}
											onClick={() => toggleSort("size")}
										/>
									</tr>
								</thead>
								<tbody className="divide-y divide-gray-100">
									{filtered.map((row) => (
										<tr key={row.id} className="hover:bg-gray-50">
											<td className="py-2 px-3 font-mono text-gray-800">
												<span className="truncate block max-w-[420px]">{row.path}</span>
											</td>
											<td className="py-2 px-3 text-gray-800">{row.title}</td>
											<td className="py-2 px-3 text-gray-800">{row.type}</td>
											<td className="py-2 px-3 tabular-nums text-gray-800">{formatKB(row.size)}</td>
										</tr>
									))}
								</tbody>
							</table>
						</div>
					</div>
                </div>
            )}

			{activeTab === "config" && (
				<div className="mt-4 space-y-3">
					<div className="flex items-center justify-between">
						<h3 className="text-sm font-medium text-gray-900">Crawler config</h3>
						<CopyButton value={JSON.stringify(sampleConfig, null, 2)} label="Copy JSON" />
					</div>
					<pre className="overflow-auto rounded-lg border bg-gray-50 p-3 text-xs leading-relaxed text-gray-800">
						{JSON.stringify(sampleConfig, null, 2)}
					</pre>
				</div>
			)}

			{activeTab === "logs" && (
				<div className="mt-4">
					<div className="mb-2 flex items-center justify-between">
						<h3 className="text-sm font-medium text-gray-900">Run logs</h3>
						<span className="inline-flex items-center gap-1 text-xs text-green-700">
							<HiOutlineCheckCircle className="h-4 w-4" /> live
						</span>
					</div>
					<pre className="max-h-[420px] overflow-auto rounded-lg border bg-black p-3 text-xs leading-relaxed text-green-300">
						{`10:12:03  [INFO] seed=https://example.com depth=2 renderJS=true
							10:12:05  [FETCH] 200  GET  /  (18322 bytes)
							10:12:07  [PARSE] links found: 14
							10:12:12  [FETCH] 200  GET  /pricing  (25101 bytes)
							10:12:15  [FETCH] 200  GET  /about  (19552 bytes)
							10:12:18  [FETCH] 200  GET  /case-studies  (39881 bytes)
							10:12:23  [FETCH] 200  GET  /blog  (28430 bytes)
							10:12:27  [FETCH] 200  GET  /blog/ai-for-search  (44012 bytes)
							10:12:32  [FETCH] 200  GET  /whitepaper.pdf  (512330 bytes)
							10:12:38  [DONE]  indexed=10  queued=0  errors=0`}
					</pre>
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

// Sample config for Config tab
const sampleConfig = {
  seedUrl: "https://example.com",
  include: ["/", "/pricing", "/about", "/blog"],
  exclude: ["/admin", "/auth", "/cart"],
  depth: 2,
  maxPages: 250,
  renderJS: true,
  respectRobotsTxt: true,
  obeySitemaps: true,
  userAgent: "DemoCrawler/1.0",
  rateLimit: { requestsPerSecond: 4, burst: 8 },
};