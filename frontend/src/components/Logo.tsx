import { cn } from "../lib/cn";

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
        <rect width="28" height="28" rx="7" className="fill-zinc-900" />
        <path
          d="M14 7.5a4 4 0 0 0-4 4V13h-.25c-.69 0-1.25.56-1.25 1.25v4.5c0 .69.56 1.25 1.25 1.25h8.5c.69 0 1.25-.56 1.25-1.25v-4.5c0-.69-.56-1.25-1.25-1.25H18v-1.5a4 4 0 0 0-4-4Zm2.25 5.5h-4.5v-1.5a2.25 2.25 0 0 1 4.5 0V13Z"
          className="fill-surface"
        />
      </svg>
      <span className="text-[15px] font-semibold tracking-tight text-zinc-900">
        Password Manager
      </span>
    </div>
  );
}
