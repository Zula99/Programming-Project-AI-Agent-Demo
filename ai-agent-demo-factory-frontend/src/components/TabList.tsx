import { useId } from "react";
type Tab = "data" | "config" | "logs";

export default function TabList({
  value,
  onChange,
}: {
  value: Tab;
  onChange: (t: Tab) => void;
}) {
  const id = useId();
  const tabs: { key: Tab; label: string }[] = [
    { key: "data", label: "Data" },
    { key: "config", label: "Config" },
    { key: "logs", label: "Logs" },
  ];

  return (
    <div role="tablist" aria-labelledby={`${id}-label`} className="mt-4 border-b">
      <div className="flex gap-2">
        {tabs.map((t) => {
          const active = value === t.key;
          return (
            <button
              key={t.key}
              role="tab"
              aria-selected={active}
              aria-controls={`${id}-${t.key}-panel`}
              onClick={() => onChange(t.key)}
              className={[
                "relative -mb-px rounded-t-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "text-blue-600"
                  : "text-gray-500 hover:text-gray-700",
              ].join(" ")}
            >
              {t.label}
              <span
                className={[
                  "absolute left-0 right-0 bottom-[-1px] h-0.5",
                  active ? "bg-blue-600" : "bg-transparent",
                ].join(" ")}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}