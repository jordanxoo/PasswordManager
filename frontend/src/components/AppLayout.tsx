import { Outlet } from "react-router-dom";
import { useAuth } from "../stores/authStore";
import { Logo } from "./Logo";
import { Button } from "./ui/Button";

export function AppLayout() {
  const email = useAuth((s) => s.email);
  const logout = useAuth((s) => s.logout);

  return (
    <div className="min-h-screen">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          <Logo />
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-zinc-500 sm:inline">{email}</span>
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
