import { KeyRound, Star, User } from "lucide-react";
import { IconButton } from "../ui/IconButton";
import { CopyButton } from "../ui/CopyButton";
import { cn } from "../../lib/cn";
import type { VaultItem } from "../../lib/vault";

interface Props {
  item: VaultItem;
  onView: () => void;
  onTogglePin: () => void;
  /** Hide write actions (pin) for read-only org members. */
  readOnly?: boolean;
}

export function VaultRow({ item, onView, onTogglePin, readOnly }: Props) {
  return (
    <div className="flex items-center gap-1 px-2 transition-colors hover:bg-canvas">
      <button
        type="button"
        onClick={onView}
        className="flex min-w-0 flex-1 items-center gap-3 rounded-lg px-2 py-2.5 text-left focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-zinc-900/10"
      >
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-zinc-100 text-sm font-semibold text-zinc-600">
          {item.name.charAt(0).toUpperCase() || "?"}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-zinc-900">{item.name}</p>
          <p className="truncate text-[13px] text-zinc-500">{item.username || item.url}</p>
        </div>
      </button>
      <div className="flex items-center gap-0.5">
        {!readOnly && (
          <IconButton
            label={item.pinned ? "Unpin" : "Pin"}
            onClick={onTogglePin}
            className={cn(item.pinned && "text-amber-500 hover:text-amber-600")}
          >
            <Star size={16} className={cn(item.pinned && "fill-amber-400")} />
          </IconButton>
        )}
        <CopyButton value={item.username} label="Copy username">
          <User size={16} />
        </CopyButton>
        <CopyButton value={item.password} label="Copy password">
          <KeyRound size={16} />
        </CopyButton>
      </div>
    </div>
  );
}
