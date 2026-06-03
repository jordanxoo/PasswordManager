import { useState } from "react";
import { ShieldCheck, ShieldOff } from "lucide-react";
import { useProfile, useRecoveryStatus } from "../lib/profileQueries";
import { Button } from "../components/ui/Button";
import { Enable2faDialog } from "../components/settings/Enable2faDialog";
import { Disable2faDialog } from "../components/settings/Disable2faDialog";

export function SettingsPage() {
  const { data: profile, isLoading } = useProfile();
  const enabled = profile?.totp_enabled ?? false;
  const { data: recovery } = useRecoveryStatus(enabled);
  const [enableOpen, setEnableOpen] = useState(false);
  const [disableOpen, setDisableOpen] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-zinc-900">Settings</h1>
        <p className="mt-1 text-sm text-zinc-500">Manage your account security.</p>
      </div>

      <section className="rounded-xl border border-zinc-200 bg-white p-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex gap-3">
            <span
              className={
                enabled
                  ? "mt-0.5 text-emerald-600"
                  : "mt-0.5 text-zinc-400"
              }
            >
              {enabled ? <ShieldCheck size={20} /> : <ShieldOff size={20} />}
            </span>
            <div>
              <h2 className="text-sm font-semibold text-zinc-900">
                Two-factor authentication
              </h2>
              <p className="mt-0.5 text-[13px] text-zinc-500">
                {isLoading
                  ? "Loading…"
                  : enabled
                    ? "Your account is protected with an authenticator app."
                    : "Add a one-time code from an authenticator app at sign-in."}
              </p>
              {enabled && recovery && (
                <p className="mt-1 text-[13px] text-zinc-500">
                  {recovery.remaining} of {recovery.total} recovery codes remaining.
                </p>
              )}
            </div>
          </div>

          {!isLoading &&
            (enabled ? (
              <Button variant="secondary" size="sm" onClick={() => setDisableOpen(true)}>
                Disable
              </Button>
            ) : (
              <Button size="sm" onClick={() => setEnableOpen(true)}>
                Enable
              </Button>
            ))}
        </div>
      </section>

      <Enable2faDialog open={enableOpen} onOpenChange={setEnableOpen} />
      <Disable2faDialog open={disableOpen} onOpenChange={setDisableOpen} />
    </div>
  );
}
