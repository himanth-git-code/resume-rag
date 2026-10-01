import { Badge } from "@/components/ui/badge";
import { absoluteUrl } from "@/lib/validation/employer-profile";
import type { PublicProfile } from "@/types/employer-profile";

type Profile = PublicProfile["profile"];

const period = (start?: string | null, end?: string | null, current?: boolean | null) =>
  [start, end || (current ? "Present" : null)].filter(Boolean).join(" – ");

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-3">
      <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{title}</h2>
      {children}
    </section>
  );
}

export function ProfileView({ profile }: { profile: Profile }) {
  const skillGroups = new Map<string, string[]>();
  for (const skill of profile.skills ?? []) {
    const key = skill.category ?? "";
    skillGroups.set(key, [...(skillGroups.get(key) ?? []), skill.name]);
  }

  return (
    <article className="grid gap-8">
      <header className="grid gap-1">
        <h1 className="text-3xl font-semibold tracking-tight">{profile.full_name || "Candidate"}</h1>
        {profile.headline && <p className="text-lg text-muted-foreground">{profile.headline}</p>}
        <p className="text-sm text-muted-foreground">
          {[profile.location, profile.email, profile.phone].filter(Boolean).join(" · ")}
        </p>
      </header>

      {profile.summary && (
        <Section title="Summary">
          <p className="whitespace-pre-wrap">{profile.summary}</p>
        </Section>
      )}

      {!!profile.experience?.length && (
        <Section title="Experience">
          <div className="grid gap-5">
            {profile.experience.map((e, i) => (
              <div key={i} className="grid gap-1.5">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h3 className="font-medium">{[e.title, e.company].filter(Boolean).join(" · ")}</h3>
                  <span className="text-sm text-muted-foreground">{period(e.start_date, e.end_date, e.is_current)}</span>
                </div>
                {e.description && <p className="text-sm">{e.description}</p>}
                {[...e.responsibilities, ...e.achievements].length > 0 && (
                  <ul className="list-disc space-y-1 pl-5 text-sm">
                    {[...e.responsibilities, ...e.achievements].map((line, j) => (
                      <li key={j}>{line}</li>
                    ))}
                  </ul>
                )}
                {e.technologies.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {e.technologies.map((t) => (
                      <Badge key={t} variant="secondary">
                        {t}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {!!profile.projects?.length && (
        <Section title="Projects">
          <div className="grid gap-4">
            {profile.projects.map((p, i) => (
              <div key={i} className="grid gap-1">
                <h3 className="font-medium">
                  {p.url ? (
                    <a href={absoluteUrl(p.url)} target="_blank" rel="noopener noreferrer nofollow" className="underline-offset-4 hover:underline">
                      {p.name}
                    </a>
                  ) : (
                    p.name
                  )}
                  {p.role && <span className="font-normal text-muted-foreground"> · {p.role}</span>}
                </h3>
                {p.description && <p className="text-sm">{p.description}</p>}
                {p.technologies.length > 0 && (
                  <p className="text-sm text-muted-foreground">{p.technologies.join(", ")}</p>
                )}
              </div>
            ))}
          </div>
        </Section>
      )}

      {skillGroups.size > 0 && (
        <Section title="Skills">
          <div className="grid gap-2">
            {[...skillGroups].map(([category, names]) => (
              <div key={category} className="flex flex-wrap items-center gap-1.5">
                {category && <span className="mr-1 text-sm text-muted-foreground">{category}:</span>}
                {names.map((n) => (
                  <Badge key={n} variant="outline">
                    {n}
                  </Badge>
                ))}
              </div>
            ))}
          </div>
        </Section>
      )}

      {!!profile.education?.length && (
        <Section title="Education">
          {profile.education.map((e, i) => (
            <p key={i} className="text-sm">
              <span className="font-medium">{[e.degree, e.field_of_study].filter(Boolean).join(", ")}</span>
              {e.institution && ` · ${e.institution}`}
              {period(e.start_date, e.end_date) && <span className="text-muted-foreground"> · {period(e.start_date, e.end_date)}</span>}
            </p>
          ))}
        </Section>
      )}

      {!!profile.certifications?.length && (
        <Section title="Certifications">
          {profile.certifications.map((c, i) => (
            <p key={i} className="text-sm">
              <span className="font-medium">{c.name}</span>
              {c.issuer && ` · ${c.issuer}`}
              {c.issue_date && <span className="text-muted-foreground"> · {c.issue_date}</span>}
            </p>
          ))}
        </Section>
      )}

      {!!profile.achievements?.length && (
        <Section title="Achievements">
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {profile.achievements.map((a, i) => (
              <li key={i}>
                <span className="font-medium">{a.title}</span>
                {a.description && ` · ${a.description}`}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {!!profile.links?.length && (
        <Section title="Links">
          <ul className="grid gap-1 text-sm">
            {profile.links.map((l, i) => (
              <li key={i}>
                <a href={absoluteUrl(l.url)} target="_blank" rel="noopener noreferrer nofollow" className="underline underline-offset-4">
                  {l.label || l.url}
                </a>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </article>
  );
}
