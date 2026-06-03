import type { ReactNode } from "react";

interface FieldProps {
  label: string;
  htmlFor: string;
  error?: string;
  hint?: string;
  children: ReactNode;
}

export function Field({ label, htmlFor, error, hint, children }: FieldProps) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-zinc-700">
        {label}
      </label>
      {children}
      {error ? (
        <p className="text-[13px] text-red-600">{error}</p>
      ) : hint ? (
        <p className="text-[13px] text-zinc-500">{hint}</p>
      ) : null}
    </div>
  );
}
