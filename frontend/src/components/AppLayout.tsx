import { Link, Outlet } from "react-router-dom";
import { KeyRound, Settings } from "lucide-react";
import { useAuth } from "../stores/authStore";
import { Logo } from "./Logo";
import { Button } from "./ui/Button";

export function AppLayout() {
  const email = useAuth((s) => s.email);
  const logout = useAuth((s) => s.logout);

  return (
    <div className="min-h-screen">
      <header className="border-b border-zinc-200 bg-surface">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          <Link to="/" aria-label="Vault">
            <Logo />
          </Link>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-zinc-500 sm:inline">{email}</span>
            <Link
              to="/generator"
              aria-label="Password generator"
              className="rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-zinc-900/10"
            >
              <KeyRound size={18} />
            </Link>
            <Link
              to="/settings"
              aria-label="Settings"
              className="rounded-md p-1.5 text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-zinc-900/10"
            >
              <Settings size={18} />
            </Link>
            <Button variant="secondary" size="sm" onClick={() => void logout()}>
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
