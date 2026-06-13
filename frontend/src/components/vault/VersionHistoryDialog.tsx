import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, Copy, Eye, EyeOff, RotateCcw } from "lucide-react";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";
import { IconButton } from "../ui/IconButton";
import { CopyButton } from "../ui/CopyButton";
import { ErrorBanner } from "../ui/ErrorBanner";
import { useVaultHistory, useRestoreVault } from "../../lib/vaultQueries";
import { diffFields, type VaultItem, type VaultSecret } from "../../lib/vault";
import { relativeTime, formatDateTime } from "../../lib/datetime";
import { cn } from "../../lib/cn";

const FIELD_LABEL: Record<keyof VaultSecret, string> = {
  name: "Name",
  url: "Website",
  username: "Username",
  password: "Password",
  notes: "Notes",
};

const CURRENT_ID = "__current__";

const toSecret = (item: VaultItem): VaultSecret => ({
  name: item.name,
  url: item.url,
  username: item.username,
  password: item.password,
  notes: item.notes,
});

interface Props {
  /** The entry whose history to show, or null when closed. */
  item: VaultItem | null;
  /** Called when the dialog is dismissed — the parent re-opens the view. */
  onClose: () => void;
}

export function VersionHistoryDialog({ item, onClose }: Props) {
  const { data: versions, isLoading, isError } = useVaultHistory(item?.id ?? null);
  const restore = useRestoreVault(item?.id ?? null);

  // Rows can be expanded / revealed independently, so these are sets of ids.
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [revealed, setRevealed] = useState<Set<string>>(new Set());
  const [confirmId, setConfirmId] = useState<string | null>(null);

  // Reset transient UI whenever we open a different entry.
  useEffect(() => {
    setExpanded(new Set());
    setRevealed(new Set());
    setConfirmId(null);
    restore.reset();
  }, [item?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const current = item ? toSecret(item) : null;

  const flip = (set: Set<string>, id: string) => {
    const next = new Set(set);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  };
  const toggle = (id: string) => setExpanded((s) => flip(s, id));
  const toggleReveal = (id: string) => setRevealed((s) => flip(s, id));

  return (
    <Modal
      open={!!item}
      onOpenChange={(open) => !open && onClose()}
      title="Version history"
      description={item ? item.name : undefined}
      size="lg"
    >
      {restore.isError && (
        <div className="mb-4">
          <ErrorBanner message="Couldn't restore that version. Please try again." />
        </div>
      )}

      {/* Current version — the baseline every snapshot is compared against. */}
      {item && current && (
        <TimelineRow
          dotClass="bg-emerald-500"
          header={
            <>
              <p className="text-sm font-medium text-zinc-900">Current version</p>
              <p className="text-[13px] text-zinc-500">Last changed {relativeTime(item.updatedAt)}</p>
            </>
          }
          expanded={expanded.has(CURRENT_ID)}
          onToggle={() => toggle(CURRENT_ID)}
        >
          <VersionFields
            secret={current}
            changed={[]}
            revealed={revealed.has(CURRENT_ID)}
            onToggleReveal={() => toggleReveal(CURRENT_ID)}
          />
        </TimelineRow>
      )}

      <div className="mt-2">
        {isLoading ? (
          <p className="py-6 text-center text-sm text-zinc-500">Loading history…</p>
        ) : isError ? (
          <ErrorBanner message="Couldn't load version history." />
        ) : !versions || versions.length === 0 ? (
          <p className="rounded-lg border border-dashed border-zinc-300 px-3 py-8 text-center text-sm text-zinc-500">
            No previous versions yet. Edits to this item will show up here.
          </p>
        ) : (
          <ol className="space-y-2">
            {versions.map((v) => {
              const changed = current ? diffFields(v.secret, current) : [];
              const confirming = confirmId === v.id;
              return (
                <TimelineRow
                  key={v.id}
                  dotClass="bg-zinc-300"
                  header={
                    <>
                      <p
                        className="text-sm font-medium text-zinc-900"
                        title={formatDateTime(v.changedAt)}
                      >
                        {relativeTime(v.changedAt)}
                      </p>
                      <div className="mt-0.5 flex flex-wrap gap-1">
                        {changed.length === 0 ? (
                          <span className="text-[12px] text-zinc-400">Same as current</span>
                        ) : (
                          changed.map((f) => (
                            <span
                              key={f}
                              className="rounded bg-zinc-100 px-1.5 py-0.5 text-[11px] font-medium text-zinc-600"
                            >
                              {FIELD_LABEL[f]}
                            </span>
                          ))
                        )}
                      </div>
                    </>
                  }
                  expanded={expanded.has(v.id)}
                  onToggle={() => toggle(v.id)}
                >
                  <VersionFields
                    secret={v.secret}
                    changed={changed}
                    revealed={revealed.has(v.id)}
                    onToggleReveal={() => toggleReveal(v.id)}
                  />
                  <div className="flex justify-end pt-3">
                    {confirming ? (
                      <div className="flex items-center gap-2">
                        <span className="text-[13px] text-zinc-500">Restore this version?</span>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => setConfirmId(null)}
                          disabled={restore.isPending}
                        >
                          Cancel
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => restore.mutate(v.id, { onSuccess: onClose })}
                          disabled={restore.isPending}
                        >
                          {restore.isPending ? "Restoring…" : "Confirm"}
                        </Button>
                      </div>
                    ) : (
                      <Button variant="secondary" size="sm" onClick={() => setConfirmId(v.id)}>
                        <RotateCcw size={14} />
                        Restore
                      </Button>
                    )}
                  </div>
                </TimelineRow>
              );
            })}
          </ol>
        )}
      </div>
    </Modal>
  );
}

interface TimelineRowProps {
  dotClass: string;
  header: ReactNode;
  expanded: boolean;
  onToggle: () => void;
  children: ReactNode;
}

function TimelineRow({ dotClass, header, expanded, onToggle, children }: TimelineRowProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-zinc-200">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-canvas focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-zinc-900/10"
      >
        <span className={cn("h-2 w-2 shrink-0 rounded-full", dotClass)} />
        <div className="min-w-0 flex-1">{header}</div>
        <ChevronDown
          size={16}
          className={cn("shrink-0 text-zinc-400 transition-transform", expanded && "rotate-180")}
        />
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <div className="border-t border-zinc-200 px-3 py-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/** Read-only view of one version's fields; changed fields are highlighted and
 *  always shown (even when empty) so additions/removals are legible. */
function VersionFields({
  secret,
  changed,
  revealed,
  onToggleReveal,
}: {
  secret: VaultSecret;
  changed: (keyof VaultSecret)[];
  revealed: boolean;
  onToggleReveal: () => void;
}) {
  return (
    <div className="space-y-3">
      {(["name", "url", "username"] as const).map((f) =>
        secret[f] || changed.includes(f) ? (
          <ReadRow key={f} label={FIELD_LABEL[f]} value={secret[f]} highlight={changed.includes(f)} />
        ) : null,
      )}

      {(secret.password || changed.includes("password")) && (
        <div className="space-y-1">
          <p className="text-[12px] font-medium text-zinc-500">Password</p>
          <div
            className={cn(
              "flex items-center gap-1 rounded-md border bg-canvas px-3 py-1.5",
              changed.includes("password") ? "border-amber-300" : "border-zinc-200",
            )}
          >
            {secret.password ? (
              <span className="flex-1 truncate font-mono text-sm text-zinc-900">
                {revealed ? secret.password : "•".repeat(Math.min(secret.password.length, 16))}
              </span>
            ) : (
              <span className="flex-1 truncate text-sm italic text-zinc-400">Empty</span>
            )}
            <IconButton
              label={revealed ? "Hide password" : "Show password"}
              onClick={onToggleReveal}
              disabled={!secret.password}
            >
              {revealed ? <EyeOff size={16} /> : <Eye size={16} />}
            </IconButton>
            <CopyButton value={secret.password} label="Copy password">
              <Copy size={16} />
            </CopyButton>
          </div>
        </div>
      )}

      {(secret.notes || changed.includes("notes")) && (
        <ReadRow label="Notes" value={secret.notes} highlight={changed.includes("notes")} multiline />
      )}
    </div>
  );
}

function ReadRow({
  label,
  value,
  highlight,
  multiline,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  multiline?: boolean;
}) {
  const empty = !value;
  return (
    <div className="space-y-1">
      <p className="text-[12px] font-medium text-zinc-500">{label}</p>
      <p
        className={cn(
          "rounded-md border bg-canvas px-3 py-1.5 text-sm",
          multiline ? "whitespace-pre-wrap" : "truncate",
          highlight ? "border-amber-300" : "border-zinc-200",
          empty ? "italic text-zinc-400" : "text-zinc-900",
        )}
      >
        {empty ? "Empty" : value}
      </p>
    </div>
  );
}
