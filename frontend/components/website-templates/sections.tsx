/**
 * Section renderers shared by all website templates (server components).
 * Templates decide layout and order; these render one section's content in a
 * given visual variant. All content comes from SiteData, never from the LLM.
 */
import { absoluteUrl } from "@/lib/validation/employer-profile";
import { period } from "@/lib/validation/site";
import { cn } from "@/lib/utils";
import type { SiteContent, SiteSectionKey } from "@/types/site";

export type Variant = "plain" | "cards" | "tiles";

const chip = "rounded-full border border-[var(--site-border)] px-2.5 py-0.5 text-xs";
const card = "rounded-xl border border-[var(--site-border)] bg-[var(--site-card)] p-5";
const muted = "text-[var(--site-muted)]";
const link = "underline decoration-[var(--site-accent)] underline-offset-4 hover:text-[var(--site-accent)]";

function Chips({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <ul className="flex flex-wrap gap-1.5">
      {items.map((t) => (
        <li key={t} className={chip}>
          {t}
        </li>
      ))}
    </ul>
  );
}

function Bullets({ items }: { items: string[] }) {
  if (!items.length) return null;
  return (
    <ul className="list-disc space-y-1 pl-5">
      {items.map((b, i) => (
        <li key={i}>{b}</li>
      ))}
    </ul>
  );
}

function About({ c }: { c: NonNullable<SiteContent["about"]> }) {
  return (
    <div className="grid gap-4">
      {c.intro && <p className="text-lg">{c.intro}</p>}
      {c.text && <p className={cn("whitespace-pre-line leading-relaxed", c.intro && muted)}>{c.text}</p>}
    </div>
  );
}

function Experience({ c, variant }: { c: NonNullable<SiteContent["experience"]>; variant: Variant }) {
  return (
    <ol className={cn("grid", variant === "plain" ? "gap-8" : "gap-4")}>
      {c.map((e, i) => (
        <li key={i} className={cn("grid gap-2", variant !== "plain" && card)}>
          <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
            <h3 className="text-lg font-semibold" style={{ fontFamily: "var(--site-heading)" }}>
              {[e.title, e.company].filter(Boolean).join(" · ")}
            </h3>
            <span className={cn("text-sm", muted)}>
              {[period(e.start_date, e.end_date, e.is_current), e.location].filter(Boolean).join(" · ")}
            </span>
          </div>
          {e.description && <p>{e.description}</p>}
          <Bullets items={[...e.responsibilities, ...e.achievements]} />
          <Chips items={e.technologies} />
        </li>
      ))}
    </ol>
  );
}

function Projects({ c, variant }: { c: NonNullable<SiteContent["projects"]>; variant: Variant }) {
  return (
    <ul className={cn("grid gap-4", variant !== "plain" && "sm:grid-cols-2")}>
      {c.map((p, i) => (
        <li
          key={i}
          className={cn(
            "grid content-start gap-2",
            variant === "cards" && card,
            variant === "tiles" && "min-h-48 rounded-2xl bg-[var(--site-accent)] p-6 text-[var(--site-on-accent)]",
          )}
        >
          <h3 className={cn("font-semibold", variant === "tiles" ? "text-2xl" : "text-lg")} style={{ fontFamily: "var(--site-heading)" }}>
            {p.url ? (
              <a href={absoluteUrl(p.url)} target="_blank" rel="noopener noreferrer nofollow" className="hover:underline">
                {p.name}
              </a>
            ) : (
              p.name
            )}
          </h3>
          {(p.role || p.start_date) && (
            <p className={cn("text-sm", variant !== "tiles" && muted)}>
              {[p.role, period(p.start_date, p.end_date)].filter(Boolean).join(" · ")}
            </p>
          )}
          {p.description && <p className={variant === "tiles" ? "opacity-90" : undefined}>{p.description}</p>}
          {variant === "tiles" ? (
            p.technologies.length > 0 && <p className="text-sm opacity-80">{p.technologies.join(" · ")}</p>
          ) : (
            <Chips items={p.technologies} />
          )}
        </li>
      ))}
    </ul>
  );
}

function SkillGroups({ groups }: { groups: NonNullable<SiteContent["skills"]> }) {
  return (
    <div className="grid gap-3">
      {groups.map((g, i) => (
        <div key={i} className="grid gap-1.5">
          {g.category && <p className={cn("text-sm font-medium", muted)}>{g.category}</p>}
          <Chips items={g.items} />
        </div>
      ))}
    </div>
  );
}

function TechStack({ c }: { c: NonNullable<SiteContent["tech_stack"]> }) {
  return (
    <div className="grid gap-4">
      <SkillGroups groups={c.groups} />
      {c.also_used.length > 0 && (
        <div className="grid gap-1.5">
          <p className={cn("text-sm font-medium", muted)}>Also used</p>
          <Chips items={c.also_used} />
        </div>
      )}
    </div>
  );
}

function Highlights({ c }: { c: NonNullable<SiteContent["highlights"]> }) {
  return (
    <ul className="grid gap-3">
      {c.map((h, i) => (
        <li key={i} className="border-l-2 border-[var(--site-accent)] pl-4">
          <p>{h.text}</p>
          {h.context && <p className={cn("text-sm", muted)}>{h.context}</p>}
        </li>
      ))}
    </ul>
  );
}

function Achievements({ c }: { c: NonNullable<SiteContent["achievements"]> }) {
  return (
    <ul className="grid gap-3">
      {c.map((a, i) => (
        <li key={i}>
          <p className="font-medium">
            {a.title}
            {a.date && <span className={cn("ml-2 text-sm font-normal", muted)}>{a.date}</span>}
          </p>
          {a.description && <p className={muted}>{a.description}</p>}
        </li>
      ))}
    </ul>
  );
}

function Education({ c }: { c: NonNullable<SiteContent["education"]> }) {
  return (
    <ul className="grid gap-3">
      {c.map((e, i) => (
        <li key={i}>
          <p className="font-medium">{[e.degree, e.field_of_study].filter(Boolean).join(", ") || e.institution}</p>
          <p className={cn("text-sm", muted)}>
            {[e.degree || e.field_of_study ? e.institution : null, period(e.start_date, e.end_date), e.grade]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </li>
      ))}
    </ul>
  );
}

function Certifications({ c }: { c: NonNullable<SiteContent["certifications"]> }) {
  return (
    <ul className="grid gap-2">
      {c.map((cert, i) => (
        <li key={i}>
          <span className="font-medium">
            {cert.url ? (
              <a href={absoluteUrl(cert.url)} target="_blank" rel="noopener noreferrer nofollow" className={link}>
                {cert.name}
              </a>
            ) : (
              cert.name
            )}
          </span>
          <span className={muted}> {[cert.issuer, cert.issue_date].filter(Boolean).join(" · ")}</span>
        </li>
      ))}
    </ul>
  );
}

function Contact({ c }: { c: NonNullable<SiteContent["contact"]> }) {
  return (
    <ul className="grid gap-2">
      {c.email && (
        <li>
          <a href={`mailto:${c.email}`} className={link}>
            {c.email}
          </a>
        </li>
      )}
      {c.phone && <li>{c.phone}</li>}
      {c.links.map((l, i) => (
        <li key={i}>
          <a href={absoluteUrl(l.url)} target="_blank" rel="noopener noreferrer nofollow me" className={link}>
            {l.label || l.url}
          </a>
        </li>
      ))}
    </ul>
  );
}

/** Render one section's body. Unknown keys render nothing (forward compatibility). */
export function SectionBody({ sectionKey, content, variant = "plain" }: { sectionKey: SiteSectionKey; content: SiteContent; variant?: Variant }) {
  switch (sectionKey) {
    case "about":
      return content.about ? <About c={content.about} /> : null;
    case "experience":
      return content.experience ? <Experience c={content.experience} variant={variant} /> : null;
    case "leadership":
      return content.leadership ? <Bullets items={content.leadership} /> : null;
    case "achievements":
      return content.achievements ? <Achievements c={content.achievements} /> : null;
    case "highlights":
      return content.highlights ? <Highlights c={content.highlights} /> : null;
    case "skills":
      return content.skills ? <SkillGroups groups={content.skills} /> : null;
    case "tech_stack":
      return content.tech_stack ? <TechStack c={content.tech_stack} /> : null;
    case "projects":
      return content.projects ? <Projects c={content.projects} variant={variant} /> : null;
    case "github":
      return content.github ? (
        <a href={absoluteUrl(content.github.url)} target="_blank" rel="noopener noreferrer nofollow me" className={link}>
          {content.github.url.replace(/^https?:\/\//, "")}
        </a>
      ) : null;
    case "education":
      return content.education ? <Education c={content.education} /> : null;
    case "certifications":
      return content.certifications ? <Certifications c={content.certifications} /> : null;
    case "contact":
      return content.contact ? <Contact c={content.contact} /> : null;
    default:
      return null;
  }
}
