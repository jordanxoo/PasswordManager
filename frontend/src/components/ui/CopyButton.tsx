import { useState } from "react";
import type { ReactNode } from "react";
import { Check } from "lucide-react";
import { IconButton } from "./IconButton";

interface CopyButtonProps {
  value: string;
  label: string;
  children: ReactNode;
}

/** Copies `value` to the clipboard and flashes a check for ~1.2s. */
export function CopyButton({ value, label, children }: CopyButtonProps) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    if (!value) return;
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  return (
    <IconButton label={copied ? "Copied" : label} onClick={copy} disabled={!value}>
      {copied ? <Check size={16} className="text-emerald-600" /> : children}
    </IconButton>
  );
}
