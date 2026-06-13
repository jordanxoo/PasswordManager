import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  generateOrgKey,
  importPublicKey,
  wrapOrgKey,
  unwrapOrgKey,
  type Organization,
} from "@pm/core";
import { api } from "./api";
import { useAuth } from "../stores/authStore";
import { useVaultContext } from "../stores/vaultContext";

const ORGS_KEY = ["organizations"] as const;
const membersKey = (orgId: string) => ["organizations", orgId, "members"] as const;

/** Organizations the current user belongs to (with role + wrapped org key). */
export function useOrgs() {
  const encryptionKey = useAuth((s) => s.encryptionKey);
  return useQuery({
    queryKey: ORGS_KEY,
    enabled: !!encryptionKey,
    queryFn: () => api.listOrgs(),
  });
}

/** Create an org: generate a fresh org key and wrap it with the user's own key. */
export function useCreateOrg() {
  const qc = useQueryClient();
  const publicKey = useAuth((s) => s.publicKey);
  return useMutation({
    mutationFn: async (name: string) => {
      const orgKey = await generateOrgKey();
      const ownPub = await importPublicKey(publicKey!);
      const wrapped = await wrapOrgKey(orgKey, ownPub);
      return api.createOrg(name, wrapped);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ORGS_KEY }),
  });
}

export function useMembers(orgId: string) {
  return useQuery({
    queryKey: membersKey(orgId),
    queryFn: () => api.listMembers(orgId),
  });
}

/**
 * Add a member: unwrap the org key with our private key, then re-wrap it with
 * the new member's public key. The plaintext org key never leaves the browser.
 */
export function useAddMember(org: Organization | undefined) {
  const qc = useQueryClient();
  const privateKey = useAuth((s) => s.privateKey);
  return useMutation({
    mutationFn: async ({ email, role }: { email: string; role: string }) => {
      if (!org) throw new Error("Organization not loaded yet — try again in a moment.");
      if (!privateKey) throw new Error("Session locked. Please sign in again.");
      // Unwrap our copy of the org key, then re-wrap it for the new member.
      const orgKey = await unwrapOrgKey(org.wrapped_org_key, privateKey);
      const target = await api.getPublicKey(email);
      const targetPub = await importPublicKey(target.public_key);
      const wrapped = await wrapOrgKey(orgKey, targetPub);
      return api.addMember(org.id, email, role, wrapped);
    },
    onSuccess: () => org && qc.invalidateQueries({ queryKey: membersKey(org.id) }),
  });
}

export function useChangeRole(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.changeMemberRole(orgId, userId, role),
    onSuccess: () => qc.invalidateQueries({ queryKey: membersKey(orgId) }),
  });
}

export function useRemoveMember(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => api.removeMember(orgId, userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: membersKey(orgId) }),
  });
}

export function useUpdateOrgSettings(orgId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (memberWrite: boolean) => api.updateOrgSettings(orgId, memberWrite),
    onSuccess: () => qc.invalidateQueries({ queryKey: ORGS_KEY }),
  });
}

const ROLE_RANK: Record<string, number> = { member: 1, admin: 2, owner: 3 };

/**
 * The AES key + write permission for the currently selected vault context.
 * Personal => the user's own encryption key (always writable). Org => the org
 * key, unwrapped once from the membership's wrapped copy with the private key
 * and cached; writable per the org's member_write setting and the user's role.
 */
export function useActiveVaultKey() {
  const orgId = useVaultContext((s) => s.orgId);
  const encryptionKey = useAuth((s) => s.encryptionKey);
  const privateKey = useAuth((s) => s.privateKey);
  const { data: orgs } = useOrgs();
  const org = orgId ? orgs?.find((o) => o.id === orgId) : undefined;

  const orgKeyQuery = useQuery({
    queryKey: ["orgKey", orgId],
    enabled: !!org && !!privateKey,
    staleTime: Infinity,
    queryFn: () => unwrapOrgKey(org!.wrapped_org_key, privateKey!),
  });

  if (!orgId) {
    return { key: encryptionKey ?? undefined, isLoading: false, canWrite: true };
  }
  const canWrite = !!org && (org.member_write || ROLE_RANK[org.role] >= ROLE_RANK.admin);
  return { key: orgKeyQuery.data, isLoading: orgKeyQuery.isLoading, canWrite };
}
