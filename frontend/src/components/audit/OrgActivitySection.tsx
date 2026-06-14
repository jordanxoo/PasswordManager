import { useState } from "react";
import { useOrgAudit, useOrgItemNames } from "../../lib/auditQueries";
import { useCollections } from "../../lib/collectionQueries";
import type { OrgAuditEntry } from "@pm/core";

const LABEL: Record<string, string> = {
  vault_read: "viewed",
  vault_create: "added",
  vault_update: "edited",
  vault_delete: "deleted",
  org_created: "created the organization",
  org_member_added: "added a member",
  org_member_removed: "removed a member",
  org_role_changed: "changed a role",
  org_key_rotated: "rotated a key",
  collection_created: "created collection",
  collection_deleted: "deleted collection",
  collection_access_granted: "granted collection access",
  collection_access_revoked: "revoked collection access",
};

const isVaultEvent = (t: string) => t.startsWith("vault_");

/** Where the event happened: a collection, the org-wide "General", or the org itself. */
function source(e: OrgAuditEntry, collNames: Map<string, string>): string {
  const m = (e.event_metadata ?? {}) as Record<string, unknown>;
  const cid = m.collection_id as string | undefined;
  if (cid) return collNames.get(cid) ?? "a collection";
  if (isVaultEvent(e.event_type)) return "General";
  return "Organization";
}

function detail(e: OrgAuditEntry, names: Map<string, string> | undefined): string {
  const m = (e.event_metadata ?? {}) as Record<string, unknown>;
  if (isVaultEvent(e.event_type)) {
    const id = m.vault_id as string | undefined;
    const name = id ? names?.get(id) : undefined;
    return name ? `“${name}”` : "an entry";
  }
  if (m.collection_name) return `“${m.collection_name as string}”`;
  if (m.member) return m.member as string;
  if (m.invited) return m.invited as string;
  return "";
}

/** Admin-only feed of who did what in the organization, filterable by collection. */
export function OrgActivitySection({ orgId, enabled }: { orgId: string; enabled: boolean }) {
  // "" = all activity, "general" = org-wide shared items, else a collection id.
  const [scope, setScope] = useState("");
  const { data: collections } = useCollections(enabled ? orgId : null);
  const { data: events, isLoading } = useOrgAudit(orgId, enabled, scope || undefined);
  const { data: names } = useOrgItemNames(orgId, enabled);
  const collNames = new Map((collections ?? []).map((c) => [c.id, c.name]));

  if (!enabled) return null;

  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-2">
        <h2 className="text-sm font-medium text-zinc-700">Activity</h2>
        <select
          aria-label="Activity scope"
          value={scope}
          onChange={(e) => setScope(e.target.value)}
          className="h-8 rounded-md border border-zinc-200 bg-surface px-2 text-[13px] text-zinc-700"
        >
          <option value="">All activity</option>
          <option value="general">General</option>
          {collections?.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>
      {isLoading ? (
        <p className="text-[13px] text-zinc-500">Loading…</p>
      ) : !events || events.length === 0 ? (
        <p className="rounded-xl border border-dashed border-zinc-300 bg-surface px-4 py-6 text-center text-[13px] text-zinc-500">
          No activity yet.
        </p>
      ) : (
        <ul className="divide-y divide-zinc-200 rounded-xl border border-zinc-200 bg-surface">
          {events.map((e) => (
            <li key={e.id} className="flex items-center justify-between gap-3 px-4 py-2.5">
              <p className="min-w-0 truncate text-[13px] text-zinc-800">
                <span className="font-medium">{e.actor_email ?? "Someone"}</span>{" "}
                {LABEL[e.event_type] ?? e.event_type} {detail(e, names)}
              </p>
              <div className="flex shrink-0 items-center gap-2">
                <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[11px] text-zinc-500">
                  {source(e, collNames)}
                </span>
                <span className="text-[12px] text-zinc-400">
                  {e.created_at ? new Date(e.created_at).toLocaleString() : ""}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
