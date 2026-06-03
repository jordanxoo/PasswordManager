import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";
import { cn } from "../../lib/cn";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, invalid, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-md border bg-white px-3 text-sm text-zinc-900 shadow-sm transition-colors",
        "placeholder:text-zinc-400 focus-visible:outline-none focus-visible:ring-4",
        invalid
          ? "border-red-300 focus-visible:border-red-400 focus-visible:ring-red-500/10"
          : "border-zinc-200 focus-visible:border-zinc-400 focus-visible:ring-zinc-900/10",
        className,
      )}
      {...props}
    />
  );
});
