import { Boxes, Box, Layers, Play, Palette } from "lucide-react";
import { useState } from "react";

const sections = [
  { key: "assets", label: "Assets", icon: Boxes },
  { key: "models", label: "Models", icon: Box },
  { key: "scenes", label: "Scenes", icon: Layers },
  { key: "animations", label: "Animations", icon: Play },
  { key: "materials", label: "Materials", icon: Palette },
];

export function Sidebar() {
  const [active, setActive] = useState("assets");

  return (
    <aside className="flex w-56 shrink-0 flex-col border-r border-border bg-panel/60 p-3">
      <p className="px-2 pb-3 text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
        Library
      </p>
      <nav className="flex flex-col gap-1">
        {sections.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActive(key)}
            className={`flex items-center gap-3 rounded-md border px-3 py-2 text-sm transition-colors ${
              active === key
                ? "border-gold/30 bg-gold/10 text-gold"
                : "border-transparent text-muted-foreground hover:border-border hover:bg-secondary hover:text-foreground"
            }`}
          >
            <Icon className="size-4" />
            {label}
          </button>
        ))}
      </nav>

      <div className="mt-auto rounded-md border border-border p-3 text-xs text-muted-foreground">
        <p className="text-foreground">No assets yet</p>
        <p className="mt-1 leading-relaxed">
          Generated models and materials will appear here.
        </p>
      </div>
    </aside>
  );
}
