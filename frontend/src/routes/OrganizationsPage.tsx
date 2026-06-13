import { useState } from "react";
import { Link } from "react-router-dom";
import { Building2, ChevronRight, Plus } from "lucide-react";
import { ApiError } from "@pm/core";
import { useOrgs, useCreateOrg } from "../lib/orgQueries";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Field } from "../components/ui/Field";
import { Modal } from "../components/ui/Modal";
import { ErrorBanner } from "../components/ui/ErrorBanner";

const ROLE_LABEL: Record<string, string> = {
  owner: "Owner",
  admin: "Admin",
  member: "Member",
};

export function OrganizationsPage() {
  const { data: orgs, isLoading } = useOrgs();
  const create = useCreateOrg();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  async function onCreate() {
    setError("");
    try {
      await create.mutateAsync(name.trim());
      setName("");
      setOpen(false);
    } catch (e) {
      setError(
        e instanceof ApiError || e instanceof Error
          ? e.message
          : "Could not create organization",
      );
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900">Organizations</h1>
          <p className="mt-1 text-sm text-zinc-500">Share secrets securely with your team.</p>
        </div>
        <Button size="sm" onClick={() => setOpen(true)}>
          <Plus size={16} /> New
        </Button>
      </div>

      {isLoading ? (
        <p className="text-sm text-zinc-500">Loading…</p>
      ) : !orgs || orgs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-zinc-300 bg-surface p-10 text-center">
          <Building2 className="mx-auto text-zinc-400" size={28} />
          <p className="mt-3 text-sm text-zinc-500">
            You don't belong to any organization yet.
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {orgs.map((org) => (
            <li key={org.id}>
              <Link
                to={`/organizations/${org.id}`}
                className="flex items-center justify-between rounded-xl border border-zinc-200 bg-surface p-4 transition-colors hover:bg-canvas"
              >
                <div className="flex items-center gap-3">
                  <span className="text-zinc-400">
                    <Building2 size={18} />
                  </span>
                  <span className="text-sm font-medium text-zinc-900">{org.name}</span>
                </div>
                <div className="flex items-center gap-2 text-zinc-400">
                  <span className="text-[13px] text-zinc-500">
                    {ROLE_LABEL[org.role] ?? org.role}
                  </span>
                  <ChevronRight size={16} />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}

      <Modal
        open={open}
        onOpenChange={setOpen}
        title="New organization"
        description="An encryption key is generated in your browser and never leaves it."
      >
        <div className="space-y-4">
          {error && <ErrorBanner message={error} />}
          <Field label="Name" htmlFor="org-name">
            <Input
              id="org-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Acme Inc."
              autoFocus
            />
          </Field>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" size="sm" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              size="sm"
              disabled={!name.trim() || create.isPending}
              onClick={() => void onCreate()}
            >
              {create.isPending ? "Creating…" : "Create"}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
