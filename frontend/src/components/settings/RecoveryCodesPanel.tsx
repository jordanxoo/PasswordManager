import { useState } from "react";
import { Check, Copy, Download, ShieldAlert } from "lucide-react";
import { Button } from "../ui/Button";

/**
 * Shows the one-time recovery codes once, right after enabling 2FA. The user
 * must confirm they've saved them — the codes are never retrievable again.
 */
export function RecoveryCodesPanel({
  codes,
  onDone,
}: {
  codes: string[];
  onDone: () => void;
}) {
  const [copied, setCopied] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const asText = codes.join("\n");

  const copyAll = async () => {
    await navigator.clipboard.writeText(asText);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  const download = () => {
    const blob = new Blob([`${asText}\n`], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "recovery-codes.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex gap-2 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-[13px] text-amber-800">
        <ShieldAlert size={16} className="mt-0.5 shrink-0" />
        <p>
          Save these recovery codes somewhere safe. Each works once if you lose your
          authenticator. <strong>They won't be shown again.</strong>
        </p>
      </div>

      <ul className="grid grid-cols-2 gap-2 rounded-md border border-zinc-200 bg-canvas p-3 font-mono text-sm text-zinc-800">
        {codes.map((code) => (
          <li key={code} className="text-center tracking-wide">
            {code}
          </li>
        ))}
      </ul>

      <div className="flex gap-2">
        <Button variant="secondary" size="sm" className="flex-1" onClick={copyAll}>
          {copied ? <Check size={16} className="text-emerald-600" /> : <Copy size={16} />}
          {copied ? "Copied" : "Copy all"}
        </Button>
        <Button variant="secondary" size="sm" className="flex-1" onClick={download}>
          <Download size={16} />
          Download .txt
        </Button>
      </div>

      <label className="flex items-center gap-2 text-sm text-zinc-600">
        <input
          type="checkbox"
          checked={acknowledged}
          onChange={(e) => setAcknowledged(e.target.checked)}
          className="h-4 w-4 rounded border-zinc-300 text-zinc-900 focus:ring-zinc-900/20"
        />
        I've saved my recovery codes
      </label>

      <Button className="w-full" disabled={!acknowledged} onClick={onDone}>
        Done
      </Button>
    </div>
  );
}
