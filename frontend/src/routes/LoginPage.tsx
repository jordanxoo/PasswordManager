import { useState } from "react";
import type { FormEvent } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "@pm/core";
import { useAuth } from "../stores/authStore";
import { AuthShell } from "../components/AuthShell";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Field } from "../components/ui/Field";
import { ErrorBanner } from "../components/ui/ErrorBanner";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Enter your master password"),
});
type Values = z.infer<typeof schema>;

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const justRegistered = (location.state as { registered?: boolean } | null)?.registered;
  const login = useAuth((s) => s.login);
  const status = useAuth((s) => s.status);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema) });

  const onSubmit = handleSubmit(async ({ email, password }) => {
    setFormError(null);
    try {
      const result = await login(email, password);
      if (!result.requires2fa) navigate("/", { replace: true });
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Unable to sign in. Please try again.");
    }
  });

  if (status === "pending2fa") {
    return (
      <AuthShell
        title="Two-factor authentication"
        subtitle="Enter the 6-digit code from your authenticator app."
      >
        <TwoFactorForm onDone={() => navigate("/", { replace: true })} />
      </AuthShell>
    );
  }

  return (
    <AuthShell title="Sign in" subtitle="Unlock your vault with your master password.">
      {justRegistered && (
        <div className="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-[13px] text-emerald-700">
          Account created. Sign in to continue.
        </div>
      )}
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {formError && <ErrorBanner message={formError} />}
        <Field label="Email" htmlFor="email" error={errors.email?.message}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            autoFocus
            invalid={!!errors.email}
            {...register("email")}
          />
        </Field>
        <Field label="Master password" htmlFor="password" error={errors.password?.message}>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            invalid={!!errors.password}
            {...register("password")}
          />
        </Field>
        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Unlocking…" : "Sign in"}
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-zinc-500">
        No account?{" "}
        <Link
          to="/register"
          className="font-medium text-zinc-900 underline-offset-4 hover:underline"
        >
          Create one
        </Link>
      </p>
    </AuthShell>
  );
}

function TwoFactorForm({ onDone }: { onDone: () => void }) {
  const complete2fa = useAuth((s) => s.complete2fa);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await complete2fa(code);
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Invalid code. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      {error && <ErrorBanner message={error} />}
      <Field label="Authentication code" htmlFor="code">
        <Input
          id="code"
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
      <Button type="submit" className="w-full" disabled={submitting || code.length !== 6}>
        {submitting ? "Verifying…" : "Verify"}
      </Button>
    </form>
  );
}
