import { useState } from "react";
import { ApiError } from "@pm/core";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";
import { ErrorBanner } from "../ui/ErrorBanner";
import { useDeleteVault } from "../../lib/vaultQueries";
import type { VaultItem } from "../../lib/vault";

interface Props {
  /** The item to delete, or null when the dialog is closed. */
  item: VaultItem | null;
  onClose: () => void;
}

export function DeleteItemDialog({ item, onClose }: Props) {
  const del = useDeleteVault();
  const [error, setError] = useState<string | null>(null);

  const confirm = async () => {
    if (!item) return;
    setError(null);
    try {
      await del.mutateAsync(item.id);
      onClose();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't delete. Please try again.");
    }
  };

  return (
    <Modal
      open={!!item}
      onOpenChange={(open) => !open && onClose()}
      title="Delete item"
      description={item ? `“${item.name}” will be permanently removed from your vault.` : undefined}
    >
      <div className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={confirm}
            disabled={del.isPending}
            className="bg-red-600 hover:bg-red-500 focus-visible:ring-red-600/20"
          >
            {del.isPending ? "Deleting…" : "Delete"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
