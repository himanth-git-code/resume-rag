"use client";

import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

/** Native modal asking for the reason an admin action is taken (kept in the audit log). */
export function ReasonDialog({
  title,
  danger,
  pending,
  error,
  onConfirm,
  onClose,
}: {
  title: string;
  danger: boolean;
  pending: boolean;
  error: string | null;
  onConfirm: (reason: string) => void;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const [reason, setReason] = useState("");

  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      className="m-auto w-[min(28rem,calc(100vw-2rem))] rounded-lg border bg-background p-0 text-foreground backdrop:bg-black/40"
    >
      <form
        className="grid gap-4 p-5"
        onSubmit={(e) => {
          e.preventDefault();
          if (reason.trim()) onConfirm(reason.trim());
        }}
      >
        <h2 className="text-lg font-semibold">{title}</h2>
        <div className="grid gap-2">
          <Label htmlFor="admin-reason">Reason</Label>
          <Textarea
            id="admin-reason"
            required
            maxLength={300}
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Why? This is kept in the audit log."
          />
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" onClick={() => ref.current?.close()}>
            Cancel
          </Button>
          <Button type="submit" variant={danger ? "destructive" : "default"} disabled={pending || !reason.trim()}>
            {pending ? "Working…" : title}
          </Button>
        </div>
      </form>
    </dialog>
  );
}
