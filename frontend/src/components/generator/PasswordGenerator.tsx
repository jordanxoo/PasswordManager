import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Copy } from "lucide-react";
import {
  generatePassword,
  alphabetSize,
  entropyBits,
  strength,
  DEFAULT_GENERATOR_OPTIONS,
  MIN_LENGTH,
  MAX_LENGTH,
  type GeneratorOptions,
  type StrengthLevel,
} from "@pm/core";
import { Button } from "../ui/Button";
import { IconButton } from "../ui/IconButton";
import { CopyButton } from "../ui/CopyButton";
import { cn } from "../../lib/cn";

const STORAGE_KEY = "pm.generator.options";

const CLASS_TOGGLES: ReadonlyArray<{ key: keyof GeneratorOptions; label: string }> = [
  { key: "uppercase", label: "A–Z" },
  { key: "lowercase", label: "a–z" },
  { key: "numbers", label: "0–9" },
  { key: "symbols", label: "!@#" },
];

const STRENGTH_META: Record<StrengthLevel, { label: string; fill: string; text: string; bars: number }> = {
  weak: { label: "Weak", fill: "bg-red-500", text: "text-red-600", bars: 1 },
  fair: { label: "Fair", fill: "bg-amber-500", text: "text-amber-600", bars: 2 },
  strong: { label: "Strong", fill: "bg-emerald-500", text: "text-emerald-600", bars: 3 },
  excellent: { label: "Excellent", fill: "bg-emerald-500", text: "text-emerald-600", bars: 4 },
};

function loadOptions(): GeneratorOptions {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...DEFAULT_GENERATOR_OPTIONS, ...(JSON.parse(raw) as Partial<GeneratorOptions>) };
  } catch {
    /* fall through to defaults */
  }
  return DEFAULT_GENERATOR_OPTIONS;
}

interface Props {
  /** When set, renders a primary "Use password" action with the current value. */
  onUse?: (password: string) => void;
}

export function PasswordGenerator({ onUse }: Props) {
  const [options, setOptions] = useState<GeneratorOptions>(loadOptions);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const regenerate = useCallback(() => {
    try {
      setPassword(generatePassword(options));
      setError(null);
    } catch (e) {
      setPassword("");
      setError(e instanceof Error ? e.message : "Couldn't generate a password");
    }
  }, [options]);

  // Persist preferences and re-roll whenever the options change.
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(options));
    } catch {
      /* private mode / quota — preferences just won't persist */
    }
    regenerate();
  }, [options, regenerate]);

  const set = <K extends keyof GeneratorOptions>(key: K, value: GeneratorOptions[K]) =>
    setOptions((o) => ({ ...o, [key]: value }));

  const toggle = (key: keyof GeneratorOptions) =>
    setOptions((o) => ({ ...o, [key]: !o[key] }));

  const alphabet = alphabetSize(options);
  const bits = entropyBits(password.length, alphabet);
  const meta = STRENGTH_META[strength(bits)];

  return (
    <div className="space-y-5">
      {/* Output */}
      <div>
        <div className="flex items-stretch gap-2">
          <output
            aria-label="Generated password"
            className="flex min-h-[3rem] flex-1 items-center break-all rounded-md border border-zinc-200 bg-canvas px-3 py-2 font-mono text-sm text-zinc-900"
          >
            {password || <span className="text-zinc-400">Select at least one character set</span>}
          </output>
          <div className="flex items-center gap-1 self-center">
            <CopyButton value={password} label="Copy password">
              <Copy size={16} />
            </CopyButton>
            <IconButton label="Regenerate" onClick={regenerate} disabled={!password}>
              <RefreshCw size={16} />
            </IconButton>
          </div>
        </div>

        {/* Strength */}
        <div className="mt-2 flex items-center justify-between gap-3">
          <div className="flex flex-1 gap-1" aria-hidden>
            {[0, 1, 2, 3].map((i) => (
              <span
                key={i}
                className={cn(
                  "h-1 flex-1 rounded-full transition-colors",
                  password && i < meta.bars ? meta.fill : "bg-zinc-200",
                )}
              />
            ))}
          </div>
          <span className={cn("text-xs font-medium tabular-nums", password ? meta.text : "text-zinc-400")}>
            {password ? `${meta.label} · ${bits} bits` : "—"}
          </span>
        </div>
      </div>

      {error && <p className="text-[13px] text-red-600">{error}</p>}

      {/* Length */}
      <div>
        <div className="mb-1.5 flex items-center justify-between">
          <label htmlFor="gen-length" className="text-sm font-medium text-zinc-700">
            Length
          </label>
          <span className="font-mono text-sm tabular-nums text-zinc-900">{options.length}</span>
        </div>
        <input
          id="gen-length"
          type="range"
          min={MIN_LENGTH}
          max={MAX_LENGTH}
          value={options.length}
          onChange={(e) => set("length", Number(e.target.value))}
          className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-zinc-200 accent-zinc-900 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-zinc-900/10"
        />
      </div>

      {/* Character sets */}
      <div className="flex flex-wrap gap-2">
        {CLASS_TOGGLES.map(({ key, label }) => {
          const active = options[key] as boolean;
          return (
            <button
              key={key}
              type="button"
              aria-pressed={active}
              onClick={() => toggle(key)}
              className={cn(
                "h-9 rounded-md border px-3 font-mono text-[13px] transition-colors focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-zinc-900/10",
                active
                  ? "border-zinc-900 bg-zinc-900 text-surface"
                  : "border-zinc-200 bg-surface text-zinc-500 hover:bg-canvas",
              )}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Exclude ambiguous */}
      <label className="flex cursor-pointer items-center gap-2 text-sm text-zinc-700">
        <input
          type="checkbox"
          checked={options.excludeAmbiguous}
          onChange={() => toggle("excludeAmbiguous")}
          className="h-4 w-4 rounded border-zinc-300 accent-zinc-900"
        />
        Exclude look-alike characters (0 O 1 l I)
      </label>

      {onUse && (
        <div className="flex justify-end pt-1">
          <Button onClick={() => password && onUse(password)} disabled={!password}>
            Use password
          </Button>
        </div>
      )}
    </div>
  );
}
