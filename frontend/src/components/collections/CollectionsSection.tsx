import { useState } from "react";
import { FolderPlus, Trash2, Users } from "lucide-react";
import { ApiError, type Collection } from "@pm/core";
import {
  useCollections,
  useCreateCollection,
  useDeleteCollection,
  useCollectionMembers,
  useGrantCollectionAccess,
  useRevokeCollectionAccess,
} from "../../lib/collectionQueries";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Field } from "../ui/Field";
import { Modal } from "../ui/Modal";
import { ErrorBanner } from "../ui/ErrorBanner";

const errMsg = (e: unknown, fallback: string) =>
  e instanceof ApiError || e instanceof Error ? e.message : fallback;

/** Admin-only management of an org's collections (create, access, delete). */
export function CollectionsSection({ orgId }: { orgId: string }) {
  const { data: collections } = useCollections(orgId);
  const createCollection = useCreateCollection(orgId);
  const deleteCollection = useDeleteCollection(orgId);

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [manage, setManage] = useState<Collection | null>(null);

  async function onCreate() {
    setError("");
    try {
      await createCollection.mutateAsync(name.trim());
      setName("");
      setOpen(false);
    } catch (e) {
      setError(errMsg(e, "Could not create collection"));
    }
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-sm font-medium text-zinc-700">Collections</h2>
        <Button size="sm" variant="secondary" onClick={() => setOpen(true)}>
          <FolderPlus size={16} /> New collection
        </Button>
      </div>

      {!collections || collections.length === 0 ? (
        <p className="rounded-xl border border-dashed border-zinc-300 bg-surface px-4 py-6 text-center text-[13px] text-zinc-500">
          No collections yet. Everything shared lives in “General”.
        </p>
      ) : (
        <ul className="divide-y divide-zinc-200 rounded-xl border border-zinc-200 bg-surface">
          {collections.map((c) => (
            <li key={c.id} className="flex items-center justify-between gap-3 px-4 py-3">
              <span className="truncate text-sm text-zinc-900">{c.name}</span>
              <div className="flex items-center gap-1">
                <Button size="sm" variant="secondary" onClick={() => setManage(c)}>
                  <Users size={15} /> Access
                </Button>
                <button
                  aria-label="Delete collection"
                  onClick={() => {
                    if (window.confirm(`Delete collection “${c.name}” and all its items?`))
                      deleteCollection.mutate(c.id);
                  }}
                  className="rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-600 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-red-500/10"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <Modal open={open} onOpenChange={setOpen} title="New collection"
        description="A separate encryption key is generated in your browser for this collection.">
        <div className="space-y-4">
          {error && <ErrorBanner message={error} />}
          <Field label="Name" htmlFor="coll-name">
            <Input id="coll-name" value={name} onChange={(e) => setName(e.target.value)}
              placeholder="DevOps" autoFocus />
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>Cancel</Button>
            <Button size="sm" disabled={!name.trim() || createCollection.isPending}
              onClick={() => void onCreate()}>
              {createCollection.isPending ? "Creating…" : "Create"}
            </Button>
          </div>
        </div>
      </Modal>

      {manage && (
        <AccessModal orgId={orgId} collection={manage} onClose={() => setManage(null)} />
      )}
    </div>
  );
}

function AccessModal({
  orgId,
  collection,
  onClose,
}: {
  orgId: string;
  collection: Collection;
  onClose: () => void;
}) {
  const { data: members } = useCollectionMembers(orgId, collection.id);
  const grant = useGrantCollectionAccess(orgId, collection);
  const revoke = useRevokeCollectionAccess(orgId, collection.id);
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");

  async function onGrant() {
    setError("");
    try {
      await grant.mutateAsync(email.trim());
      setEmail("");
    } catch (e) {
      setError(errMsg(e, "Could not grant access"));
    }
  }

  return (
    <Modal open onOpenChange={(o) => !o && onClose()} title={`Access — ${collection.name}`}
      description="The collection key is re-encrypted in your browser for each member you add.">
      <div className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <ul className="divide-y divide-zinc-200 rounded-md border border-zinc-200">
          {members?.map((m) => (
            <li key={m.user_id} className="flex items-center justify-between gap-2 px-3 py-2">
              <span className="truncate text-[13px] text-zinc-800">{m.email}</span>
              <button
                aria-label="Revoke access"
                onClick={() => revoke.mutate(m.user_id)}
                className="rounded-md p-1 text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-600"
              >
                <Trash2 size={15} />
              </button>
            </li>
          ))}
          {members && members.length === 0 && (
            <li className="px-3 py-2 text-[13px] text-zinc-500">No one has access yet.</li>
          )}
        </ul>
        <Field label="Add by email" htmlFor="grant-email" hint="Must be a confirmed org member.">
          <div className="flex gap-2">
            <Input id="grant-email" type="email" value={email}
              onChange={(e) => setEmail(e.target.value)} placeholder="teammate@example.com" />
            <Button size="sm" disabled={!email.trim() || grant.isPending}
              onClick={() => void onGrant()}>
              {grant.isPending ? "Adding…" : "Add"}
            </Button>
          </div>
        </Field>
      </div>
    </Modal>
  );
}
