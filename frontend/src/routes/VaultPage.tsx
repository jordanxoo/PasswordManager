import { Button } from "../components/ui/Button";

export function VaultPage() {
  return (
    <div>
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-zinc-900">Vault</h1>
          <p className="mt-1 text-sm text-zinc-500">Your encrypted logins live here.</p>
        </div>
        <Button>New item</Button>
      </div>

      <div className="mt-8 rounded-xl border border-dashed border-zinc-300 bg-white py-16 text-center">
        <p className="text-sm font-medium text-zinc-900">No items yet</p>
        <p className="mx-auto mt-1 max-w-xs text-sm text-zinc-500">
          Add your first login — it's encrypted in your browser before it ever leaves this device.
        </p>
      </div>
    </div>
  );
}
