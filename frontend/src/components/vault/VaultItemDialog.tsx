import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AnimatePresence, motion } from "framer-motion";
import { Eye, EyeOff, Dices } from "lucide-react";
import { ApiError } from "@pm/core";
import { Modal } from "../ui/Modal";
import { Button } from "../ui/Button";
import { Input } from "../ui/Input";
import { Field } from "../ui/Field";
import { Textarea } from "../ui/Textarea";
import { IconButton } from "../ui/IconButton";
import { ErrorBanner } from "../ui/ErrorBanner";
import { PasswordGenerator } from "../generator/PasswordGenerator";
import { type VaultDraft, type VaultItem } from "../../lib/vault";
import { useCreateVault, useUpdateVault } from "../../lib/vaultQueries";

const schema = z.object({
  name: z.string().min(1, "Name is required"),
  url: z.string().min(1, "Website is required"),
  username: z.string(),
  password: z.string().min(1, "Password is required"),
  notes: z.string(),
});
type Values = z.infer<typeof schema>;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Present => edit mode; absent => create mode. */
  item?: VaultItem;
}

const blank = (): Values => ({ name: "", url: "", username: "", password: "", notes: "" });

export function VaultItemDialog({ open, onOpenChange, item }: Props) {
  const create = useCreateVault();
  const update = useUpdateVault();
  const [showPassword, setShowPassword] = useState(false);
  const [showGenerator, setShowGenerator] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(schema), defaultValues: blank() });

  // Re-seed the form each time the dialog opens (for create or a specific item).
  useEffect(() => {
    if (!open) return;
    setFormError(null);
    setShowPassword(false);
    setShowGenerator(false);
    reset(
      item
        ? {
            name: item.name,
            url: item.url,
            username: item.username,
            password: item.password,
            notes: item.notes,
          }
        : blank(),
    );
  }, [open, item, reset]);

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null);
    const draft: VaultDraft = values;
    try {
      if (item) await update.mutateAsync({ id: item.id, draft });
      else await create.mutateAsync(draft);
      onOpenChange(false);
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Couldn't save. Please try again.");
    }
  });

  return (
    <Modal open={open} onOpenChange={onOpenChange} title={item ? "Edit item" : "New item"}>
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {formError && <ErrorBanner message={formError} />}
        <Field label="Name" htmlFor="v-name" error={errors.name?.message}>
          <Input id="v-name" autoFocus placeholder="GitHub" invalid={!!errors.name} {...register("name")} />
        </Field>
        <Field label="Website" htmlFor="v-url" error={errors.url?.message}>
          <Input id="v-url" placeholder="github.com" invalid={!!errors.url} {...register("url")} />
        </Field>
        <Field label="Username" htmlFor="v-username">
          <Input id="v-username" autoComplete="off" placeholder="you@example.com" {...register("username")} />
        </Field>
        <Field label="Password" htmlFor="v-password" error={errors.password?.message}>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                id="v-password"
                type={showPassword ? "text" : "password"}
                autoComplete="off"
                className="pr-10 font-mono"
                invalid={!!errors.password}
                {...register("password")}
              />
              <div className="absolute inset-y-0 right-1 flex items-center">
                <IconButton
                  label={showPassword ? "Hide password" : "Show password"}
                  onClick={() => setShowPassword((v) => !v)}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </IconButton>
              </div>
            </div>
            <IconButton
              label="Password generator"
              aria-expanded={showGenerator}
              className={
                showGenerator
                  ? "h-10 w-10 border border-zinc-300 bg-zinc-100 text-zinc-900"
                  : "h-10 w-10 border border-zinc-200"
              }
              onClick={() => setShowGenerator((v) => !v)}
            >
              <Dices size={16} />
            </IconButton>
          </div>
          <AnimatePresence initial={false}>
            {showGenerator && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.18 }}
                className="overflow-hidden"
              >
                <div className="mt-3 rounded-lg border border-zinc-200 bg-canvas p-4">
                  <PasswordGenerator
                    onUse={(pw) => {
                      setValue("password", pw, { shouldValidate: true });
                      setShowPassword(true);
                      setShowGenerator(false);
                    }}
                  />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </Field>
        <Field label="Notes" htmlFor="v-notes">
          <Textarea id="v-notes" rows={3} placeholder="Optional" {...register("notes")} />
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Saving…" : "Save"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
