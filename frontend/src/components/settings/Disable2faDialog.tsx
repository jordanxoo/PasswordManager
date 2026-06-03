import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { ApiError } from "@pm/core";
import { useDisable2fa } from "../../lib/profileQueries";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Field } from "../ui/Field";
import { ErrorBanner } from "../ui/ErrorBanner";

/** Turn 2FA off. Requires a current TOTP code so a hijacked session can't do it. */
export function Disable2faDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const disable = useDisable2fa();

  useEffect(() => {
    if (!open) {
      setCode("");
      setError(null);
    }
  }, [open]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await disable.mutateAsync(code);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Invalid code. Try again.");
    }
  };

  return (
    <Modal
      open={open}
      onOpenChange={onOpenChange}
      title="Disable two-factor authentication"
      description="Enter a current code from your authenticator to turn 2FA off."
    >
      <form onSubmit={submit} className="space-y-4">
        {error && <ErrorBanner message={error} />}
        <Field label="Authentication code" htmlFor="disable-2fa-code">
          <Input
            id="disable-2fa-code"
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
          variant="secondary"
          className="w-full border-red-200 text-red-700 hover:bg-red-50"
          disabled={disable.isPending || code.length !== 6}
        >
          {disable.isPending ? "Disabling…" : "Disable 2FA"}
        </Button>
      </form>
    </Modal>
  );
}
