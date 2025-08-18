export default function SortableTH({
  label,
  active,
  dir,
  onClick,
  className = "",
}: {
  label: string;
  active?: boolean;
  dir?: "asc" | "desc";
  onClick: () => void;
  className?: string;
}) {
  return (
    <th
      scope="col"
      className={`cursor-pointer select-none ${className}`}
      onClick={onClick}
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
          <span className="text-xs text-gray-500">{dir === "asc" ? "▲" : "▼"}</span>
        )}
      </span>
    </th>
  );
}