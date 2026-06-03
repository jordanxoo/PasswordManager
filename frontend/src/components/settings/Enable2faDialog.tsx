import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "@pm/core";
import { api } from "../../lib/api";
import { useVerify2fa } from "../../lib/profileQueries";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Field } from "../ui/Field";
import { ErrorBanner } from "../ui/ErrorBanner";
import { CopyButton } from "../ui/CopyButton";
import { Copy } from "lucide-react";
import { RecoveryCodesPanel } from "./RecoveryCodesPanel";

type Setup = { secret: string; qr_code: string };

/**
 * Enroll in TOTP 2FA: fetch a fresh secret/QR on open, confirm a code to enable,
 * then reveal the one-time recovery codes. Nothing is enforced until verify
 * succeeds, so closing early simply abandons the unconfirmed secret.
 */
export function Enable2faDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [setup, setSetup] = useState<Setup | null>(null);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const verify = useVerify2fa();

  // Fetch a secret/QR each time the dialog opens; reset everything on close.
  useEffect(() => {
    if (!open) {
      setSetup(null);
      setSetupError(null);
      setCode("");
      setVerifyError(null);
      setRecoveryCodes(null);
      return;
    }
    let active = true;
    api
      .setup2fa()
      .then((data) => active && setSetup(data))
      .catch((e) =>
        active &&
        setSetupError(e instanceof ApiError ? e.message : "Couldn't start 2FA setup."),
      );
    return () => {
      active = false;
    };
  }, [open]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setVerifyError(null);
    try {
      const result = await verify.mutateAsync(code);
      setRecoveryCodes(result.recovery_codes);
    } catch (err) {
      setVerifyError(err instanceof ApiError ? err.message : "Invalid code. Try again.");
    }
  };

  const inCodesStep = recoveryCodes !== null;

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title={inCodesStep ? "Save your recovery codes" : "Enable two-factor authentication"}
      description={
        inCodesStep
          ? undefined
          : "Scan the QR code with an authenticator app, then enter the 6-digit code."
      }
    >
      {inCodesStep ? (
        <RecoveryCodesPanel codes={recoveryCodes} onDone={() => onOpenChange(false)} />
      ) : setupError ? (
        <ErrorBanner message={setupError} />
      ) : !setup ? (
        <p className="py-8 text-center text-sm text-zinc-500">Preparing setup…</p>
      ) : (
        <form onSubmit={submit} className="space-y-4">
          <div className="flex justify-center">
            <img
              src={`data:image/png;base64,${setup.qr_code}`}
              alt="2FA QR code"
              className="h-44 w-44 rounded-lg border border-zinc-200"
            />
          </div>

          <div className="space-y-1.5">
            <p className="text-sm font-medium text-zinc-700">Can't scan? Enter this key</p>
            <div className="flex items-center gap-2 rounded-md border border-zinc-200 bg-canvas px-3 py-2">
              <code className="flex-1 break-all font-mono text-[13px] text-zinc-700">
                {setup.secret}
              </code>
              <CopyButton value={setup.secret} label="Copy secret">
                <Copy size={16} />
              </CopyButton>
            </div>
          </div>

          {verifyError && <ErrorBanner message={verifyError} />}

          <Field label="Authentication code" htmlFor="enable-2fa-code">
            <Input
              id="enable-2fa-code"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              placeholder="000000"
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              className="text-center tracking-[0.4em]"
              autoFocus
            />
          </Field>

          <Button
            type="submit"
            className="w-full"
            disabled={verify.isPending || code.length !== 6}
          >
            {verify.isPending ? "Verifying…" : "Verify & enable"}
          </Button>
        </form>
      )}
    </Modal>
  );
}
