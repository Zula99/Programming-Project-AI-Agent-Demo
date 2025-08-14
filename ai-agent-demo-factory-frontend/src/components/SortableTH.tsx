export default function SortableTH({
  label,
  sortKey,
  currentSort,
  sortDir,
  onSort,
  className = "",
}: {
  label: string;
  sortKey: string;
  currentSort: string;
  sortDir: "asc" | "desc";
  onSort: (key: string) => void;
  className?: string;
}) {
  const active = currentSort === sortKey;
  
  return (
    <th
      scope="col"
      className={`cursor-pointer select-none ${className}`}
      onClick={() => onSort(sortKey)}
      title={`Sort by ${label}`}
    >
      <span
        className={[
          "inline-flex items-center gap-1.5 rounded px-1 py-1 transition-colors",
          active ? "text-gray-900" : "hover:bg-gray-100",
        ].join(" ")}
      >
        {label}
        {active && (
          <span className="text-xs text-gray-500">{sortDir === "asc" ? "▲" : "▼"}</span>
        )}
      </span>
    </th>
  );
}