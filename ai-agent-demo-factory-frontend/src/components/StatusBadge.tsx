type Props = { status: "complete" | "running" | "failed" | "pending" | "unknown" };

export default function StatusBadge({ status }: Props) {
    const colours = {
        complete: "bg-green-100 text-green-800",
        running: "bg-blue-100 text-blue-800",
        failed: "bg-red-100 text-red-800",
        pending: "bg-yellow-100 text-yellow-800",
        unknown: "bg-gray-100 text-gray-800",
    };

    return (
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${colours[status]}`}>
            {status}
        </span>
    );
}