import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Copy, Eye, EyeOff } from "lucide-react";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";
import { IconButton } from "../ui/IconButton";
import { CopyButton } from "../ui/CopyButton";
import type { VaultItem } from "../../lib/vault";

interface Props {
  /** The item to view, or null when closed. */
  item: VaultItem | null;
  onClose: () => void;
  onEdit: (item: VaultItem) => void;
  onDelete: (item: VaultItem) => void;
  /** Hide Edit/Delete for read-only org members. */
  readOnly?: boolean;
}

export function ViewItemDialog({ item, onClose, onEdit, onDelete, readOnly }: Props) {
  const [reveal, setReveal] = useState(false);
  useEffect(() => {
    setReveal(false);
  }, [item]);

  return (
    <Modal
      open={!!item}
      onOpenChange={(open) => !open && onClose()}
      title={item?.name ?? ""}
      description={item?.url || undefined}
    >
      {item && (
        <div className="space-y-4">
          <ReadField label="Username" value={item.username || "—"}>
            {item.username && (
              <CopyButton value={item.username} label="Copy username">
                <Copy size={16} />
              </CopyButton>
            )}
          </ReadField>

          <div className="space-y-1.5">
            <p className="text-sm font-medium text-zinc-700">Password</p>
            <div className="flex items-center gap-1 rounded-md border border-zinc-200 bg-canvas px-3 py-1.5">
              <span className="flex-1 truncate font-mono text-sm text-zinc-900">
                {reveal ? item.password || "—" : "•".repeat(Math.min(item.password.length || 1, 16))}
              </span>
              <IconButton
                label={reveal ? "Hide password" : "Show password"}
                onClick={() => setReveal((v) => !v)}
              >
                {reveal ? <EyeOff size={16} /> : <Eye size={16} />}
              </IconButton>
              <CopyButton value={item.password} label="Copy password">
                <Copy size={16} />
              </CopyButton>
            </div>
          </div>

          {item.notes && (
            <div className="space-y-1.5">
              <p className="text-sm font-medium text-zinc-700">Notes</p>
              <p className="whitespace-pre-wrap rounded-md border border-zinc-200 bg-canvas px-3 py-2 text-sm text-zinc-700">
                {item.notes}
              </p>
            </div>
          )}

          {!readOnly && (
            <div className="flex items-center justify-between pt-2">
              <Button
                variant="secondary"
                className="border-red-200 text-red-600 hover:bg-red-50"
                onClick={() => onDelete(item)}
              >
                Delete
              </Button>
              <Button onClick={() => onEdit(item)}>Edit</Button>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
}

function ReadField({
  label,
  value,
  children,
}: {
  label: string;
  value: string;
  children?: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <p className="text-sm font-medium text-zinc-700">{label}</p>
      <div className="flex items-center gap-1 rounded-md border border-zinc-200 bg-canvas px-3 py-1.5">
        <span className="flex-1 truncate text-sm text-zinc-900">{value}</span>
        {children}
      </div>
    </div>
  );
}
