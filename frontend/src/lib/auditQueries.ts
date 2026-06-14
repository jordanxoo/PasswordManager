import { useQuery } from "@tanstack/react-query";
import { unwrapOrgKey } from "@pm/core";
import { api } from "./api";
import { useAuth } from "../stores/authStore";
import { useOrgs } from "./orgQueries";
import { useCollections } from "./collectionQueries";
import { decodeEntry } from "./vault";

/** The organization activity feed (admin+), optionally scoped to a collection
 *  ("general" = org-wide shared items, undefined = everything). */
export function useOrgAudit(orgId: string, enabled: boolean, collectionId?: string) {
  return useQuery({
    queryKey: ["orgAudit", orgId, collectionId ?? "all"],
    enabled,
    queryFn: () => api.orgAudit(orgId, collectionId),
  });
}

/**
 * Map of vault_id -> decrypted name across the org's "General" vault and every
 * collection the admin can access, so the audit feed can show item names.
 * Names are resolved client-side; ids the admin can't decrypt stay unmapped.
 */
export function useOrgItemNames(orgId: string, enabled: boolean) {
  const privateKey = useAuth((s) => s.privateKey);
  const { data: orgs } = useOrgs();
  const { data: collections } = useCollections(orgId);
  const org = orgs?.find((o) => o.id === orgId);

  return useQuery({
    queryKey: ["orgItemNames", orgId, (collections ?? []).map((c) => c.id).join(",")],
    enabled: enabled && !!org?.wrapped_org_key && !!privateKey,
    queryFn: async () => {
      const map = new Map<string, string>();
      const sources: { wrapped: string; cid?: string }[] = [
        { wrapped: org!.wrapped_org_key!, cid: undefined },
        ...(collections ?? []).map((c) => ({ wrapped: c.wrapped_collection_key, cid: c.id })),
      ];
      for (const src of sources) {
        try {
          const key = await unwrapOrgKey(src.wrapped, privateKey!);
          const items = await api.listAllVault(orgId, src.cid);
          for (const it of items) {
            try {
              const decoded = await decodeEntry(it, key);
              map.set(it.id, decoded.name);
            } catch {
              /* skip undecryptable */
            }
          }
        } catch {
          /* skip inaccessible source */
        }
      }
      return map;
    },
  });
}
