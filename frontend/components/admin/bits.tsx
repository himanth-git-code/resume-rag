"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";

export const SELECT = "h-9 rounded-md border border-input bg-transparent px-2 text-sm";

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("en-IN", { dateStyle: "medium" });
}

/** A search box value that settles 300 ms after typing stops. */
export function useDebounced(value: string, ms = 300): string {
  const [settled, setSettled] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setSettled(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return settled;
}

export function Pager({
  page,
  count,
  pageSize = 25,
  onPage,
}: {
  page: number;
  count: number;
  pageSize?: number;
  onPage: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;
  return (
    <div className="flex items-center justify-end gap-2 text-sm">
      <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        Previous
      </Button>
      <span className="text-muted-foreground">
        Page {page} of {pages}
      </span>
      <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => onPage(page + 1)}>
        Next
      </Button>
    </div>
  );
}

export function LoadState({ isPending, isError, empty }: { isPending: boolean; isError: boolean; empty?: boolean }) {
  if (isPending) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (isError) return <p className="text-sm text-destructive">Couldn&apos;t load this. Try again shortly.</p>;
  if (empty) return <p className="text-sm text-muted-foreground">Nothing matches.</p>;
  return null;
}
