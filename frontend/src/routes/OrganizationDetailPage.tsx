import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, Trash2, UserPlus } from "lucide-react";
import { ApiError } from "@pm/core";
import { useAuth } from "../stores/authStore";
import {
  useOrgs,
  useMembers,
  useAddMember,
  useChangeRole,
  useRemoveMember,
} from "../lib/orgQueries";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Field } from "../components/ui/Field";
import { Modal } from "../components/ui/Modal";
import { ErrorBanner } from "../components/ui/ErrorBanner";

const ROLE_RANK: Record<string, number> = { member: 1, admin: 2, owner: 3 };
const ROLE_LABEL: Record<string, string> = { owner: "Owner", admin: "Admin", member: "Member" };

export function OrganizationDetailPage() {
  const { orgId = "" } = useParams();
  const email = useAuth((s) => s.email);
  const { data: orgs } = useOrgs();
  const org = orgs?.find((o) => o.id === orgId);

  const { data: members, isLoading } = useMembers(orgId);
  const addMember = useAddMember(org);
  const changeRole = useChangeRole(orgId);
  const removeMember = useRemoveMember(orgId);

  const [open, setOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [error, setError] = useState("");

  const myRank = org ? ROLE_RANK[org.role] ?? 0 : 0;
  const canManage = myRank >= ROLE_RANK.admin;
  const isOwner = myRank >= ROLE_RANK.owner;

  async function onAdd() {
    setError("");
    try {
      await addMember.mutateAsync({ email: inviteEmail.trim(), role: inviteRole });
      setInviteEmail("");
      setInviteRole("member");
      setOpen(false);
    } catch (e) {
      setError(
        e instanceof ApiError || e instanceof Error ? e.message : "Could not add member",
      );
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
          <p className="mt-1 text-sm text-zinc-500">Members & roles</p>
        </div>
        {canManage && org && (
          <Button size="sm" onClick={() => setOpen(true)}>
            <UserPlus size={16} /> Add member
          </Button>
        )}
      </div>

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
                </div>
                <div className="flex items-center gap-2">
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

      <Modal
        open={open}
        onOpenChange={setOpen}
        title="Add member"
        description="The org key is re-encrypted in your browser with the new member's public key."
      >
        <div className="space-y-4">
          {error && <ErrorBanner message={error} />}
          <Field
            label="Email"
            htmlFor="invite-email"
            hint="The person must already have an account."
          >
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
              disabled={!inviteEmail.trim() || addMember.isPending}
              onClick={() => void onAdd()}
            >
              {addMember.isPending ? "Adding…" : "Add"}
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
