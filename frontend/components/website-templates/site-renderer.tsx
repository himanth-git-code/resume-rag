import type { SiteData } from "@/types/site";

import { CreativeTemplate } from "./creative";
import { ExecutiveTemplate } from "./executive";
import { MinimalTemplate } from "./minimal";
import { ModernTemplate } from "./modern";
import { TechnicalTemplate } from "./technical";
import { fontClassNames, themeStyle } from "./theme";

const TEMPLATES = {
  executive: ExecutiveTemplate,
  modern: ModernTemplate,
  technical: TechnicalTemplate,
  creative: CreativeTemplate,
  minimal: MinimalTemplate,
};

/** Render a site from SiteData with its theme. Server component: no template code ships to the browser. */
export function SiteRenderer({ site, widgets }: { site: SiteData; widgets?: React.ReactNode }) {
  const Template = TEMPLATES[site.template] ?? ModernTemplate;
  return (
    <div className={`${fontClassNames} min-h-screen bg-[var(--site-bg)] text-[var(--site-fg)]`} style={themeStyle(site.theme)}>
      <Template site={site} widgets={widgets} />
      <footer className="border-t border-[var(--site-border)] py-6 text-center text-xs text-[var(--site-muted)]">
        © {site.hero.name}
      </footer>
    </div>
  );
}
