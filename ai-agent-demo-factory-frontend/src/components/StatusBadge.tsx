import { RunStatus } from "@/hooks/useCrawler";

type Props = { status: RunStatus };

export default function StatusBadge({ status }: Props) {
    const config = {
        idle: {
            label: "Idle",
            colors: "bg-gray-100 text-gray-800",
            icon: "⏸️"
        },
        running: {
            label: "Running",
            colors: "bg-blue-100 text-blue-800",
            icon: "🔄"
        },
        complete: {
            label: "Complete",
            colors: "bg-green-100 text-green-800",
            icon: "✅"
        },
        error: {
            label: "Error",
            colors: "bg-red-100 text-red-800",
            icon: "❌"
        }
    };

    const statusConfig = config[status] || config.idle;

    return (
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${statusConfig.colors} flex items-center gap-1`}>
            <span className="text-xs">{statusConfig.icon}</span>
            {statusConfig.label}
        </span>
    );
}