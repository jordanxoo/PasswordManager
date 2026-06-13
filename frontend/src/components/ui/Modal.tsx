import * as Dialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import { X } from "lucide-react";

interface ModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  /** `md` (default) for forms; `lg` for roomier content like version history. */
  size?: "md" | "lg";
  children: ReactNode;
}

const maxWidth = { md: "max-w-md", lg: "max-w-lg" } as const;

export function Modal({ open, onOpenChange, title, description, size = "md", children }: ModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="pm-overlay fixed inset-0 bg-black/50" />
        <Dialog.Content
          className={`pm-content fixed left-1/2 top-1/2 flex max-h-[85vh] w-[calc(100%-2rem)] ${maxWidth[size]} -translate-x-1/2 -translate-y-1/2 flex-col rounded-xl border border-zinc-200 bg-surface shadow-lg focus:outline-none`}
        >
          {/* Header stays put; only the body below scrolls. */}
          <div className="flex shrink-0 items-start justify-between gap-4 p-6 pb-4">
            <div>
              <Dialog.Title className="text-base font-semibold tracking-tight text-zinc-900">
                {title}
              </Dialog.Title>
              {description && (
                <Dialog.Description className="mt-1 text-sm text-zinc-500">
                  {description}
                </Dialog.Description>
              )}
            </div>
            <Dialog.Close
              aria-label="Close"
              className="rounded-md p-1 text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-600 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-zinc-900/10"
            >
              <X size={18} />
            </Dialog.Close>
          </div>
          <div className="overflow-y-auto overscroll-contain px-6 pb-6">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
