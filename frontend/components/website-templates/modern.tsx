import type { SiteData } from "@/types/site";

import { SectionBody } from "./sections";

/** Modern Professional: accent hero band, card-based sections. */
export function ModernTemplate({ site, widgets }: { site: SiteData; widgets?: React.ReactNode }) {
  return (
    <div>
      <header className="bg-[var(--site-accent)] px-6 py-16 text-[var(--site-on-accent)] sm:py-20">
        <div className="mx-auto grid max-w-4xl gap-3">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl" style={{ fontFamily: "var(--site-heading)" }}>
            {site.hero.name}
          </h1>
          {site.hero.headline && <p className="text-xl opacity-90">{site.hero.headline}</p>}
          {site.hero.tagline && <p className="max-w-2xl opacity-80">{site.hero.tagline}</p>}
          {site.hero.location && <p className="text-sm opacity-70">{site.hero.location}</p>}
        </div>
      </header>
      <div className="mx-auto grid max-w-4xl gap-6 px-6 py-12">
        {site.sections.map((s) => (
          <section key={s.key} className="grid gap-4 rounded-2xl border border-[var(--site-border)] bg-[var(--site-card)] p-6 sm:p-8">
            <h2 className="text-2xl font-semibold" style={{ fontFamily: "var(--site-heading)" }}>
              {s.title}
            </h2>
            <SectionBody sectionKey={s.key} content={site.content} variant="plain" />
          </section>
        ))}
        {widgets}
      </div>
    </div>
  );
}
