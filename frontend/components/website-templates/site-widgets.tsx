"use client";

import { ChatPanel } from "@/components/public-profile/chat-panel";
import { MatchPanel } from "@/components/public-profile/match-panel";
import type { SiteData } from "@/types/site";

/** Embedded assistant and job matching for a published site (only when enabled). */
export function SiteWidgets({ site }: { site: SiteData }) {
  const { chatbot, matching, slug, turnstile_site_key } = site.widgets;
  if (!slug || (!chatbot && !matching)) return null;
  const apiBase = `/public/sites/${encodeURIComponent(slug)}`;
  const name = site.hero.name || "this candidate";
  return (
    <section aria-label="Ask about this candidate" className="grid gap-6 text-foreground">
      {chatbot && <ChatPanel apiBase={apiBase} name={name} turnstileSiteKey={turnstile_site_key ?? null} />}
      {matching && <MatchPanel apiBase={apiBase} name={name} turnstileSiteKey={turnstile_site_key ?? null} />}
      <p className="text-center text-xs text-[var(--site-muted)]">
        AI answers are based only on information {name} chose to publish.
      </p>
    </section>
  );
}
