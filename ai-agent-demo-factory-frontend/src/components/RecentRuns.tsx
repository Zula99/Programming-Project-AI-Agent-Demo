import StatusBadge from "./StatusBadge";

type RunStatus = "complete" | "running";
type Run = {
    url: string;
    runId: string;
    pages: number;
    status: RunStatus;
}

const runs: Run[] = [
    { url: "https://example.com", runId: "RUN-001", pages: 42, status: "complete" },
    { url: "https://nab.com.au", runId: "RUN-002", pages: 1002, status: "complete" },
    { url: "https://agilent.com", runId: "RUN-003", pages: 5, status: "running" }
];

export default function RecentRuns() {
    return (
        <div className="bg-white text-gray-400 p-4 rounded-lg border">
            <h2 className="font-medium mb-3">Recent runs</h2>
            <ul className="space-y-3">
                {runs.map((run) => (
                    <li key={run.runId} className="flex justify-between items-center">
                        <div>
                            <p className="text-blue-500">{run.url}</p>
                            <p className="text-sm text-gray-500">
                                {run.runId} | {run.pages} pages
                            </p>
                        </div>
                        <StatusBadge status={run.status} />
                    </li>
                ))}
            </ul>
        </div>
    );
}