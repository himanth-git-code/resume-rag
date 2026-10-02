import type { SiteData } from "@/types/site";

import { SectionBody } from "./sections";

/** Technical / Developer: terminal-flavoured header, stack and projects up front. */
export function TechnicalTemplate({ site, widgets }: { site: SiteData; widgets?: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-5xl px-6 py-14">
      <header className="grid gap-3 rounded-2xl border border-[var(--site-border)] bg-[var(--site-card)] p-8">
        <p className="font-mono text-sm text-[var(--site-accent)]">~/portfolio $ whoami</p>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl" style={{ fontFamily: "var(--site-heading)" }}>
          {site.hero.name}
        </h1>
        {site.hero.headline && <p className="font-mono text-lg">{site.hero.headline}</p>}
        {site.hero.tagline && <p className="text-[var(--site-muted)]">{site.hero.tagline}</p>}
      </header>
      <div className="grid gap-12 pt-12">
        {site.sections.map((s) => (
          <section key={s.key} className="grid gap-5">
            <h2 className="flex items-center gap-3 text-xl font-semibold" style={{ fontFamily: "var(--site-heading)" }}>
              <span className="font-mono text-[var(--site-accent)]">#</span>
              {s.title}
            </h2>
            <SectionBody sectionKey={s.key} content={site.content} variant="cards" />
          </section>
        ))}
        {widgets}
      </div>
    </div>
  );
}
