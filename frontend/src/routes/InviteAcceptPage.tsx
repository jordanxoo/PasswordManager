import { useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@pm/core";
import { useAuth } from "../stores/authStore";
import { useAcceptInvitation } from "../lib/orgQueries";
import { api } from "../lib/api";
import {
  setPendingInvite,
  getPendingInvite,
  clearPendingInvite,
} from "../lib/pendingInvite";
import { AuthShell } from "../components/AuthShell";
import { Button } from "../components/ui/Button";
import { ErrorBanner } from "../components/ui/ErrorBanner";

const ROLE_LABEL: Record<string, string> = { owner: "Owner", admin: "Admin", member: "Member" };

export function InviteAcceptPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const status = useAuth((s) => s.status);
  const token = params.get("token") ?? getPendingInvite() ?? "";

  // Persist the token so it survives a login/register detour.
  useEffect(() => {
    if (params.get("token")) setPendingInvite(params.get("token")!);
  }, [params]);

  const authed = status === "authenticated";

  const lookup = useQuery({
    queryKey: ["invite", token],
    enabled: authed && !!token,
    retry: false,
    queryFn: () => api.lookupInvitation(token),
  });
  const accept = useAcceptInvitation();

  async function onAccept() {
    try {
      const { org_id } = await accept.mutateAsync(token);
      clearPendingInvite();
      navigate(`/organizations/${org_id}`, { replace: true });
    } catch {
      /* surfaced via accept.error below */
    }
  }

  if (!token) {
    return (
      <AuthShell title="Invitation" subtitle="This link is missing its token.">
        <Link to="/" className="text-sm font-medium text-zinc-900 underline-offset-4 hover:underline">
          Go home
        </Link>
      </AuthShell>
    );
  }

  if (!authed) {
    return (
      <AuthShell
        title="You've been invited"
        subtitle="Sign in or create an account with the invited email to accept."
      >
        <div className="flex flex-col gap-3">
          <Button onClick={() => navigate("/login")}>Sign in</Button>
          <Button variant="secondary" onClick={() => navigate("/register")}>
            Create account
          </Button>
        </div>
      </AuthShell>
    );
  }

  if (lookup.isLoading) {
    return <AuthShell title="Invitation" subtitle="Loading…"><div /></AuthShell>;
  }

  if (lookup.isError) {
    const msg =
      lookup.error instanceof ApiError ? lookup.error.message : "Invitation not found.";
    return (
      <AuthShell title="Invitation" subtitle="We couldn't open this invite.">
        <ErrorBanner message={msg} />
        <div className="mt-4">
          <Link to="/" className="text-sm font-medium text-zinc-900 underline-offset-4 hover:underline">
            Go home
          </Link>
        </div>
      </AuthShell>
    );
  }

  const invite = lookup.data!;
  const invalid = invite.status !== "pending" || invite.expired;

  return (
    <AuthShell
      title={`Join ${invite.org_name}`}
      subtitle={`You were invited as ${ROLE_LABEL[invite.role] ?? invite.role}.`}
    >
      <div className="space-y-4">
        {accept.isError && (
          <ErrorBanner
            message={
              accept.error instanceof ApiError ? accept.error.message : "Could not accept."
            }
          />
        )}
        {invalid ? (
          <ErrorBanner
            message={invite.expired ? "This invitation has expired." : "This invitation is no longer valid."}
          />
        ) : (
          <>
            <p className="text-sm text-zinc-500">
              After you accept, an admin confirms you and you'll get access to the shared vault.
            </p>
            <Button className="w-full" disabled={accept.isPending} onClick={() => void onAccept()}>
              {accept.isPending ? "Joining…" : "Accept invitation"}
            </Button>
          </>
        )}
      </div>
    </AuthShell>
  );
}
