import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, MailPlus, Trash2 } from "lucide-react";
import { ApiError } from "@pm/core";
import { useAuth } from "../stores/authStore";
import {
  useOrgs,
  useMembers,
  useChangeRole,
  useRemoveMember,
  useUpdateOrgSettings,
  useInvitations,
  useCreateInvitation,
  useRevokeInvitation,
  useConfirmMember,
} from "../lib/orgQueries";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Field } from "../components/ui/Field";
import { Modal } from "../components/ui/Modal";
import { ErrorBanner } from "../components/ui/ErrorBanner";

const ROLE_RANK: Record<string, number> = { member: 1, admin: 2, owner: 3 };
const ROLE_LABEL: Record<string, string> = { owner: "Owner", admin: "Admin", member: "Member" };

const errMsg = (e: unknown, fallback: string) =>
  e instanceof ApiError || e instanceof Error ? e.message : fallback;

export function OrganizationDetailPage() {
  const { orgId = "" } = useParams();
  const email = useAuth((s) => s.email);
  const { data: orgs } = useOrgs();
  const org = orgs?.find((o) => o.id === orgId);

  const myRank = org ? ROLE_RANK[org.role] ?? 0 : 0;
  const canManage = myRank >= ROLE_RANK.admin;
  const isOwner = myRank >= ROLE_RANK.owner;

  const { data: members, isLoading } = useMembers(orgId);
  const { data: invitations } = useInvitations(orgId, canManage);
  const changeRole = useChangeRole(orgId);
  const removeMember = useRemoveMember(orgId);
  const updateSettings = useUpdateOrgSettings(orgId);
  const createInvitation = useCreateInvitation(orgId);
  const revokeInvitation = useRevokeInvitation(orgId);
  const confirmMember = useConfirmMember(org);

  const [open, setOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [error, setError] = useState("");
  const [confirmError, setConfirmError] = useState("");

  async function onInvite() {
    setError("");
    try {
      await createInvitation.mutateAsync({ email: inviteEmail.trim(), role: inviteRole });
      setInviteEmail("");
      setInviteRole("member");
      setOpen(false);
    } catch (e) {
      setError(errMsg(e, "Could not send invitation"));
    }
  }

  async function onConfirm(userId: string, memberEmail: string) {
    setConfirmError("");
    try {
      await confirmMember.mutateAsync({ userId, email: memberEmail });
    } catch (e) {
      setConfirmError(errMsg(e, "Could not confirm member"));
    }
  }

  if (orgs && !org) {
    return (
      <div className="space-y-4">
        <BackLink />
        <ErrorBanner message="Organization not found." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <BackLink />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900">{org?.name}</h1>
          <p className="mt-1 text-sm text-zinc-500">Members &amp; roles</p>
        </div>
        {canManage && org && (
          <Button size="sm" onClick={() => setOpen(true)}>
            <MailPlus size={16} /> Invite member
          </Button>
        )}
      </div>

      {isOwner && org && (
        <label className="flex items-center justify-between gap-4 rounded-xl border border-zinc-200 bg-surface p-4">
          <span>
            <span className="block text-sm font-medium text-zinc-900">
              Members can add &amp; edit shared items
            </span>
            <span className="mt-0.5 block text-[13px] text-zinc-500">
              When off, only admins and the owner can change the shared vault.
            </span>
          </span>
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={org.member_write}
            disabled={updateSettings.isPending}
            onChange={(e) => updateSettings.mutate(e.target.checked)}
          />
        </label>
      )}

      {confirmError && <ErrorBanner message={confirmError} />}

      {isLoading ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : (
        <ul className="divide-y divide-zinc-200 rounded-xl border border-zinc-200 bg-surface">
          {members?.map((m) => {
            const isSelf = m.email === email;
            return (
              <li key={m.user_id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm text-zinc-900">
                    {m.email}
                    {isSelf && <span className="ml-2 text-[12px] text-zinc-400">(you)</span>}
                  </p>
                  {!m.confirmed && (
                    <p className="text-[12px] text-amber-600">Pending confirmation</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {!m.confirmed && canManage && (
                    <Button
                      size="sm"
                      disabled={confirmMember.isPending}
                      onClick={() => void onConfirm(m.user_id, m.email)}
                    >
                      Confirm
                    </Button>
                  )}
                  {isOwner && m.role !== "owner" ? (
                    <select
                      value={m.role}
                      onChange={(e) =>
                        void changeRole.mutate({ userId: m.user_id, role: e.target.value })
                      }
                      className="h-8 rounded-md border border-zinc-200 bg-surface px-2 text-[13px] text-zinc-700"
                    >
                      <option value="member">Member</option>
                      <option value="admin">Admin</option>
                    </select>
                  ) : (
                    <span className="text-[13px] text-zinc-500">
                      {ROLE_LABEL[m.role] ?? m.role}
                    </span>
                  )}
                  {m.role !== "owner" && (canManage || isSelf) && (
                    <button
                      aria-label={isSelf ? "Leave organization" : "Remove member"}
                      onClick={() => void removeMember.mutate(m.user_id)}
                      className="rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-600 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-red-500/10"
                    >
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}

      {canManage && invitations && invitations.length > 0 && (
        <div>
          <h2 className="mb-2 text-sm font-medium text-zinc-700">Pending invitations</h2>
          <ul className="divide-y divide-zinc-200 rounded-xl border border-zinc-200 bg-surface">
            {invitations.map((inv) => (
              <li key={inv.id} className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm text-zinc-900">{inv.email}</p>
                  <p className="text-[12px] text-zinc-400">
                    Invited as {ROLE_LABEL[inv.role] ?? inv.role}
                  </p>
                </div>
                <button
                  aria-label="Revoke invitation"
                  onClick={() => void revokeInvitation.mutate(inv.id)}
                  className="rounded-md p-1.5 text-zinc-400 transition-colors hover:bg-red-50 hover:text-red-600 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-red-500/10"
                >
                  <Trash2 size={16} />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      <Modal
        open={open}
        onOpenChange={setOpen}
        title="Invite member"
        description="We email a join link. They get access once you confirm them after they accept."
      >
        <div className="space-y-4">
          {error && <ErrorBanner message={error} />}
          <Field label="Email" htmlFor="invite-email" hint="An account isn't required yet.">
            <Input
              id="invite-email"
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="teammate@example.com"
              autoFocus
            />
          </Field>
          <Field label="Role" htmlFor="invite-role">
            <select
              id="invite-role"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="h-10 w-full rounded-md border border-zinc-200 bg-surface px-3 text-sm text-zinc-900"
            >
              <option value="member">Member</option>
              <option value="admin">Admin</option>
            </select>
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!inviteEmail.trim() || createInvitation.isPending}
              onClick={() => void onInvite()}
            >
              {createInvitation.isPending ? "Sending…" : "Send invite"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function BackLink() {
  return (
    <Link
      to="/organizations"
      className="inline-flex items-center gap-1.5 text-[13px] text-zinc-500 transition-colors hover:text-zinc-900"
    >
      <ArrowLeft size={15} /> Organizations
    </Link>
  );
}
