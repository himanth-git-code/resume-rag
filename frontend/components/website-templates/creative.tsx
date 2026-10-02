import type { SiteData } from "@/types/site";

import { SectionBody } from "./sections";

/** Creative: oversized typography and a visual project grid. */
export function CreativeTemplate({ site, widgets }: { site: SiteData; widgets?: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-6xl px-6 py-16 sm:py-24">
      <header className="grid gap-6 pb-16">
        <h1
          className="text-5xl leading-[0.95] font-bold tracking-tight break-words sm:text-7xl lg:text-8xl"
          style={{ fontFamily: "var(--site-heading)" }}
        >
          {site.hero.name}
        </h1>
        {site.hero.headline && <p className="text-2xl text-[var(--site-accent)] sm:text-3xl">{site.hero.headline}</p>}
        {site.hero.tagline && <p className="max-w-2xl text-lg text-[var(--site-muted)]">{site.hero.tagline}</p>}
      </header>
      <div className="grid gap-20">
        {site.sections.map((s) => (
          <section key={s.key} className="grid gap-6">
            <h2 className="text-3xl font-bold sm:text-4xl" style={{ fontFamily: "var(--site-heading)" }}>
              {s.title}
            </h2>
            <SectionBody sectionKey={s.key} content={site.content} variant={s.key === "projects" ? "tiles" : "plain"} />
          </section>
        ))}
        {widgets}
      </div>
    </div>
  );
}
