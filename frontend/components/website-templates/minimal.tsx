import type { SiteData } from "@/types/site";

import { SectionBody } from "./sections";

/** Minimal: a narrow single column, small caps headings, nothing extra. */
export function MinimalTemplate({ site, widgets }: { site: SiteData; widgets?: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-2xl px-6 py-16 sm:py-20">
      <header className="grid gap-1 pb-10">
        <h1 className="text-3xl font-semibold" style={{ fontFamily: "var(--site-heading)" }}>
          {site.hero.name}
        </h1>
        {site.hero.headline && <p className="text-[var(--site-muted)]">{site.hero.headline}</p>}
        {site.hero.tagline && <p className="pt-3">{site.hero.tagline}</p>}
      </header>
      <div className="grid gap-10">
        {site.sections.map((s) => (
          <section key={s.key} className="grid gap-3">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--site-muted)]">{s.title}</h2>
            <SectionBody sectionKey={s.key} content={site.content} />
          </section>
        ))}
        {widgets}
      </div>
    </div>
  );
}
