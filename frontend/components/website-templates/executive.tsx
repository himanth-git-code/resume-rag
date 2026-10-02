import type { SiteData } from "@/types/site";

import { SectionBody } from "./sections";

/** Executive: centred, generous whitespace, headings in a left column on wide screens. */
export function ExecutiveTemplate({ site, widgets }: { site: SiteData; widgets?: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-5xl px-6 py-16 sm:py-24">
      <header className="grid gap-3 border-b border-[var(--site-border)] pb-12 text-center">
        <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl" style={{ fontFamily: "var(--site-heading)" }}>
          {site.hero.name}
        </h1>
        {site.hero.headline && <p className="text-xl text-[var(--site-accent)]">{site.hero.headline}</p>}
        {site.hero.tagline && <p className="mx-auto max-w-2xl text-[var(--site-muted)]">{site.hero.tagline}</p>}
      </header>
      <div className="grid gap-14 pt-12">
        {site.sections.map((s) => (
          <section key={s.key} className="grid gap-4 md:grid-cols-[12rem_1fr] md:gap-10">
            <h2
              className="text-sm font-semibold uppercase tracking-[0.18em] text-[var(--site-accent)]"
              style={{ fontFamily: "var(--site-heading)" }}
            >
              {s.title}
            </h2>
            <SectionBody sectionKey={s.key} content={site.content} />
          </section>
        ))}
        {widgets}
      </div>
    </div>
  );
}
