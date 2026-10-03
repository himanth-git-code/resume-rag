import { FileText } from "lucide-react";

import { cn } from "@/lib/utils";
import { formatBytes } from "@/lib/validation/support";
import type { SupportMessage } from "@/types/support";

function Attachments({ items }: { items: SupportMessage["attachments"] }) {
  if (!items.length) return null;
  return (
    <ul className="flex flex-wrap gap-2 pt-2">
      {items.map((a) =>
        a.content_type.startsWith("image/") ? (
          <li key={a.id}>
            <a href={a.url} target="_blank" rel="noopener noreferrer" title={a.original_name}>
              {/* eslint-disable-next-line @next/next/no-img-element -- authenticated API image, not optimisable */}
              <img src={a.url} alt={a.original_name} className="h-20 w-28 rounded-md border object-cover" />
            </a>
          </li>
        ) : (
          <li key={a.id}>
            <a href={a.url} className="flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs hover:bg-muted">
              <FileText className="size-4" aria-hidden />
              {a.original_name} · {formatBytes(a.size)}
            </a>
          </li>
        ),
      )}
    </ul>
  );
}

/** A ticket thread. `perspective` decides which side's messages sit on the right. */
export function Conversation({ messages, perspective }: { messages: SupportMessage[]; perspective: "candidate" | "staff" }) {
  return (
    <ol className="grid gap-3">
      {messages.map((m) => {
        if (m.kind === "event") {
          return (
            <li key={m.id} className="text-center text-xs text-muted-foreground">
              {m.body} · {new Date(m.created_at).toLocaleString()}
            </li>
          );
        }
        const mine = perspective === "candidate" ? m.kind === "candidate" : m.kind !== "candidate";
        return (
          <li key={m.id} className={cn("grid gap-1", mine && "justify-items-end")}>
            <div
              className={cn(
                "max-w-[85%] rounded-lg border px-3 py-2 text-sm",
                m.kind === "internal" && "border-amber-300 bg-amber-50 dark:border-amber-700 dark:bg-amber-950",
                m.kind !== "internal" && (mine ? "bg-primary/5" : "bg-muted"),
              )}
            >
              <p className="pb-1 text-xs font-medium text-muted-foreground">
                {m.kind === "internal" ? "Internal note · " : ""}
                {m.author?.name ?? "Support"} · {new Date(m.created_at).toLocaleString()}
              </p>
              <p className="whitespace-pre-wrap">{m.body}</p>
              <Attachments items={m.attachments} />
            </div>
          </li>
        );
      })}
    </ol>
  );
}
