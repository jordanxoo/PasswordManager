import { PasswordGenerator } from "../components/generator/PasswordGenerator";

export function GeneratorPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-zinc-900">Password generator</h1>
        <p className="mt-1 text-sm text-zinc-500">
          Strong, random passwords generated on your device — they never leave it.
        </p>
      </div>

      <section className="mx-auto max-w-lg rounded-xl border border-zinc-200 bg-surface p-5">
        <PasswordGenerator />
      </section>
    </div>
  );
}
