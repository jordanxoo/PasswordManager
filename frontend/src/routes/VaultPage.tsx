import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Database, Plus, Search } from "lucide-react";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { VaultRow } from "../components/vault/VaultRow";
import { VaultItemDialog } from "../components/vault/VaultItemDialog";
import { ViewItemDialog } from "../components/vault/ViewItemDialog";
import { DeleteItemDialog } from "../components/vault/DeleteItemDialog";
import {
  useCreateManyVault,
  useTogglePin,
  useVaultItems,
} from "../lib/vaultQueries";
import { generateMockDrafts, type VaultItem } from "../lib/vault";

export function VaultPage() {
  const { data: items, isLoading, isError } = useVaultItems();
  const togglePin = useTogglePin();
  const createMany = useCreateManyVault();

  const [query, setQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<VaultItem | undefined>(undefined);
  const [viewing, setViewing] = useState<VaultItem | null>(null);
  const [deleting, setDeleting] = useState<VaultItem | null>(null);

  // Filter, then pinned-first, then alphabetical.
  const visible = useMemo(() => {
    const base = items ?? [];
    const q = query.trim().toLowerCase();
    const filtered = q
      ? base.filter((i) => [i.name, i.url, i.username].some((f) => f.toLowerCase().includes(q)))
      : base;
    return filtered.slice().sort((a, b) => {
      if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
      return a.name.localeCompare(b.name);
    });
  }, [items, query]);

  const openCreate = () => {
    setEditing(undefined);
    setDialogOpen(true);
  };
  const openEdit = (item: VaultItem) => {
    setViewing(null);
    setEditing(item);
    setDialogOpen(true);
  };

  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900">Vault</h1>
          <p className="mt-1 text-sm text-zinc-500">
            {items
              ? `${items.length} ${items.length === 1 ? "item" : "items"}`
              : "Your encrypted logins"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {import.meta.env.DEV && (
            <Button
              variant="secondary"
              onClick={() => createMany.mutate(generateMockDrafts())}
              disabled={createMany.isPending}
            >
              <Database size={16} />
              {createMany.isPending ? "Adding…" : "Mock data"}
            </Button>
          )}
          <Button onClick={openCreate}>
            <Plus size={16} />
            New item
          </Button>
        </div>
      </div>

      <div className="relative mt-6">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
        <Input
          className="pl-9"
          placeholder="Search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="mt-4">
        {isLoading ? (
          <StateCard>Decrypting your vault…</StateCard>
        ) : isError ? (
          <StateCard>Couldn't load your vault. Try reloading.</StateCard>
        ) : visible.length === 0 ? (
          <EmptyState hasItems={!!items && items.length > 0} onCreate={openCreate} />
        ) : (
          <div className="divide-y divide-zinc-100 overflow-hidden rounded-xl border border-zinc-200 bg-white">
            <AnimatePresence initial={false}>
              {visible.map((item) => (
                <motion.div
                  key={item.id}
                  layout
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.15 }}
                >
                  <VaultRow
                    item={item}
                    onView={() => setViewing(item)}
                    onTogglePin={() => togglePin.mutate(item)}
                  />
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      <VaultItemDialog open={dialogOpen} onOpenChange={setDialogOpen} item={editing} />
      <ViewItemDialog
        item={viewing}
        onClose={() => setViewing(null)}
        onEdit={openEdit}
        onDelete={(it) => {
          setViewing(null);
          setDeleting(it);
        }}
      />
      <DeleteItemDialog item={deleting} onClose={() => setDeleting(null)} />
    </div>
  );
}

function EmptyState({ hasItems, onCreate }: { hasItems: boolean; onCreate: () => void }) {
  if (hasItems) return <StateCard>No items match your search.</StateCard>;
  return (
    <div className="rounded-xl border border-dashed border-zinc-300 bg-white py-16 text-center">
      <p className="text-sm font-medium text-zinc-900">No items yet</p>
      <p className="mx-auto mt-1 max-w-xs text-sm text-zinc-500">
        Add your first login — it's encrypted in your browser before it ever leaves this device.
      </p>
      <div className="mt-4 flex justify-center">
        <Button onClick={onCreate}>
          <Plus size={16} />
          New item
        </Button>
      </div>
    </div>
  );
}

function StateCard({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white py-12 text-center text-sm text-zinc-500">
      {children}
    </div>
  );
}
