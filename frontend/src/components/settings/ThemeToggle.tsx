import { Moon, Sun } from "lucide-react";
import { useTheme, type Theme } from "../../lib/theme";
import { cn } from "../../lib/cn";

const OPTIONS: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
];

/** Segmented Light/Dark control. */
export function ThemeToggle() {
  const theme = useTheme((s) => s.theme);
  const setTheme = useTheme((s) => s.setTheme);

  return (
    <div className="inline-flex rounded-lg border border-zinc-200 bg-canvas p-0.5">
      {OPTIONS.map(({ value, label, icon: Icon }) => {
        const active = theme === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => setTheme(value)}
            aria-pressed={active}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-[13px] font-medium transition-colors",
              "focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-zinc-900/10",
              active
                ? "bg-surface text-zinc-900 shadow-sm"
                : "text-zinc-500 hover:text-zinc-900",
            )}
          >
            <Icon size={15} />
            {label}
          </button>
        );
      })}
    </div>
  );
}
