import { useId } from "react";

type Tab = "data" | "config" | "logs";

interface TabConfig {
  id: Tab;
  label: string;
  count: number;
}

export default function TabList({
  activeTab,
  onTabChange,
  tabs,
}: {
  activeTab: Tab;
  onTabChange: (t: Tab) => void;
  tabs: TabConfig[];
}) {
  const id = useId();

  return (
    <div role="tablist" aria-labelledby={`${id}-label`} className="mt-4 border-b">
      <div className="flex gap-2">
        {tabs.map((tab) => {
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              role="tab"
              aria-selected={active}
              aria-controls={`${id}-${tab.id}-panel`}
              onClick={() => onTabChange(tab.id)}
              className={[
                "relative -mb-px rounded-t-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "text-blue-600"
                  : "text-gray-500 hover:text-gray-700",
              ].join(" ")}
            >
              {tab.label}
              {tab.count > 0 && (
                <span className="ml-2 inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                  {tab.count}
                </span>
              )}
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