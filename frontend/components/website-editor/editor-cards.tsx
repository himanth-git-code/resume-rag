"use client";

import { ArrowDown, ArrowUp } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ApiError } from "@/lib/api/client";
import { checkSlug, useDraftBio } from "@/lib/api/website";
import { usePublishWebsite } from "@/lib/api/website-publish";
import { cn } from "@/lib/utils";
import { moveItem, PALETTE_SWATCH, slugFormatError } from "@/lib/validation/website";
import type { Profile } from "@/types/profile";
import type { WebsiteCatalog, WebsiteSettings, WebsiteUpdate } from "@/types/website";

type CardProps = { site: WebsiteSettings; save: (changes: WebsiteUpdate) => Promise<void>; busy: boolean };

export function AddressCard({ site, save, busy }: CardProps) {
  const [slug, setSlug] = useState(site.slug ?? site.suggested_slug ?? "");
  // Availability result for one exact name; the format rule is checked during render.
  const [checked, setChecked] = useState<{ slug: string; ok: boolean; message: string } | null>(null);
  const unchanged = !slug || slug === site.slug;
  const formatError = unchanged ? null : slugFormatError(slug);

  useEffect(() => {
    if (unchanged || formatError) return;
    const id = setTimeout(async () => {
      try {
        const result = await checkSlug(slug);
        setChecked({ slug, ok: result.available, message: result.available ? "Available" : (result.detail ?? "Not available") });
      } catch {
        // Leave it unchecked; saving still validates on the server.
      }
    }, 400);
    return () => clearTimeout(id);
  }, [slug, unchanged, formatError]);

  const status = unchanged
    ? null
    : formatError
      ? { ok: false, message: formatError }
      : checked?.slug === slug
        ? checked
        : null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Web address</CardTitle>
        <CardDescription>Your site will live at /portfolio/{slug || "your-name"}.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        <div className="flex flex-wrap gap-2">
          <div className="flex min-w-0 flex-1 items-center rounded-md border px-3 text-sm text-muted-foreground">
            /portfolio/
            <Input
              aria-label="Web address"
              className="border-0 px-1 shadow-none focus-visible:ring-0"
              value={slug}
              onChange={(e) => setSlug(e.target.value.toLowerCase().trim())}
            />
          </div>
          <Button disabled={busy || !slug || slug === site.slug || status?.ok === false} onClick={() => save({ slug })}>
            Save
          </Button>
        </div>
        {status && <p className={cn("text-xs", status.ok ? "text-muted-foreground" : "text-destructive")}>{status.message}</p>}
        {site.slug && slug !== site.slug && (
          <p className="text-xs text-muted-foreground">Changing it later breaks links to the old address.</p>
        )}
      </CardContent>
    </Card>
  );
}

export function TemplateCard({ site, save, busy, catalog }: CardProps & { catalog: WebsiteCatalog }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Template</CardTitle>
        <CardDescription>All templates are responsive and use only your saved profile.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {catalog.templates.map((t) => (
          <button
            key={t.key}
            type="button"
            disabled={busy}
            aria-pressed={site.template === t.key}
            onClick={() => site.template !== t.key && save({ template: t.key })}
            className={cn(
              "grid gap-1 rounded-lg border p-4 text-left transition-colors hover:bg-muted",
              site.template === t.key && "border-primary ring-2 ring-primary/30",
            )}
          >
            <span className="font-medium">{t.name}</span>
            <span className="text-sm text-muted-foreground">{t.description}</span>
          </button>
        ))}
      </CardContent>
    </Card>
  );
}

export function ThemeCard({ site, save, busy, catalog }: CardProps & { catalog: WebsiteCatalog }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Look and feel</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-5">
        <div className="grid gap-2">
          <Label>Colour</Label>
          <div className="flex flex-wrap gap-2">
            {catalog.palettes.map((p) => (
              <button
                key={p.key}
                type="button"
                title={p.name}
                aria-label={p.name}
                aria-pressed={site.theme.palette === p.key}
                disabled={busy}
                onClick={() => save({ theme: { palette: p.key } })}
                className={cn("size-9 rounded-full border-2 border-transparent", site.theme.palette === p.key && "border-foreground")}
                style={{ backgroundColor: PALETTE_SWATCH[p.key] }}
              />
            ))}
          </div>
        </div>
        <div className="flex items-center justify-between gap-4">
          <Label htmlFor="dark-mode">Dark background</Label>
          <Switch
            id="dark-mode"
            checked={site.theme.mode === "dark"}
            disabled={busy}
            onCheckedChange={(dark) => save({ theme: { mode: dark ? "dark" : "light" } })}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="font">Fonts</Label>
          <select
            id="font"
            className="h-9 rounded-md border border-input bg-transparent px-3 text-sm"
            value={site.theme.font}
            disabled={busy}
            onChange={(e) => save({ theme: { font: e.target.value } })}
          >
            {catalog.fonts.map((f) => (
              <option key={f.key} value={f.key}>
                {f.name}
              </option>
            ))}
          </select>
        </div>
      </CardContent>
    </Card>
  );
}

export function SectionsCard({ site, save, busy, catalog }: CardProps & { catalog: WebsiteCatalog }) {
  const [titles, setTitles] = useState(site.overrides.titles);
  const sections = site.sections;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Sections</CardTitle>
        <CardDescription>Show, hide, reorder and rename. Empty sections are left out automatically.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2">
        {sections.map((s, i) => (
          <div key={s.key} className="flex flex-wrap items-center gap-2 rounded-md border p-2">
            <Switch
              aria-label={`Show ${catalog.sections[s.key]}`}
              checked={s.visible}
              disabled={busy}
              onCheckedChange={(visible) => save({ sections: sections.map((x) => (x.key === s.key ? { ...x, visible } : x)) })}
            />
            <Input
              aria-label={`Title for ${catalog.sections[s.key]}`}
              className="h-8 min-w-0 flex-1"
              placeholder={catalog.sections[s.key]}
              value={titles[s.key] ?? ""}
              maxLength={60}
              onChange={(e) => setTitles({ ...titles, [s.key]: e.target.value })}
              onBlur={() => (titles[s.key] ?? "") !== (site.overrides.titles[s.key] ?? "") && save({ overrides: { titles } })}
            />
            <Button size="icon" variant="ghost" aria-label="Move up" disabled={busy || i === 0} onClick={() => save({ sections: moveItem(sections, i, i - 1) })}>
              <ArrowUp />
            </Button>
            <Button
              size="icon"
              variant="ghost"
              aria-label="Move down"
              disabled={busy || i === sections.length - 1}
              onClick={() => save({ sections: moveItem(sections, i, i + 1) })}
            >
              <ArrowDown />
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function toggle(list: number[] | null, all: number[], id: number, on: boolean): number[] | null {
  const current = new Set(list ?? all);
  if (on) current.add(id);
  else current.delete(id);
  const next = all.filter((x) => current.has(x));
  return next.length === all.length ? null : next;
}

export function ContentCard({ site, save, busy, profile }: CardProps & { profile: Profile | null }) {
  const [tagline, setTagline] = useState(site.overrides.tagline);
  const [intro, setIntro] = useState(site.overrides.intro);
  const projects = (profile?.projects ?? []).filter((p) => p.id != null);
  const achievements = (profile?.achievements ?? []).filter((a) => a.id != null);
  const projectIds = projects.map((p) => p.id as number);
  const achievementIds = achievements.map((a) => a.id as number);
  const bullets = [...new Set((profile?.experience ?? []).flatMap((e) => [...(e.responsibilities ?? []), ...(e.achievements ?? [])]))];
  const dirty = tagline !== site.overrides.tagline || intro !== site.overrides.intro;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Content</CardTitle>
        <CardDescription>Website-only wording. Everything else comes from your saved profile.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        <div className="grid gap-1.5">
          <Label htmlFor="tagline">Tagline</Label>
          <Input id="tagline" maxLength={160} value={tagline} onChange={(e) => setTagline(e.target.value)} placeholder="One line under your name" />
        </div>
        <div className="grid gap-1.5">
          <Label htmlFor="intro">Intro</Label>
          <Textarea id="intro" rows={3} maxLength={1000} value={intro} onChange={(e) => setIntro(e.target.value)} placeholder="A short opening paragraph for the About section" />
        </div>
        <div>
          <Button size="sm" disabled={busy || !dirty} onClick={() => save({ overrides: { tagline, intro } })}>
            Save wording
          </Button>
        </div>

        {projects.length > 0 && (
          <fieldset className="grid gap-2">
            <legend className="text-sm font-medium">Featured projects</legend>
            {projects.map((p) => (
              <label key={p.id} className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={(site.overrides.featured_projects ?? projectIds).includes(p.id as number)}
                  disabled={busy}
                  onCheckedChange={(on) =>
                    save({ overrides: { featured_projects: toggle(site.overrides.featured_projects, projectIds, p.id as number, on === true) } })
                  }
                />
                {p.name}
              </label>
            ))}
          </fieldset>
        )}

        {achievements.length > 0 && (
          <fieldset className="grid gap-2">
            <legend className="text-sm font-medium">Featured achievements</legend>
            {achievements.map((a) => (
              <label key={a.id} className="flex items-center gap-2 text-sm">
                <Checkbox
                  checked={(site.overrides.featured_achievements ?? achievementIds).includes(a.id as number)}
                  disabled={busy}
                  onCheckedChange={(on) =>
                    save({
                      overrides: { featured_achievements: toggle(site.overrides.featured_achievements, achievementIds, a.id as number, on === true) },
                    })
                  }
                />
                {a.title}
              </label>
            ))}
          </fieldset>
        )}

        {site.template === "executive" && bullets.length > 0 && (
          <fieldset className="grid gap-2">
            <legend className="text-sm font-medium">Leadership highlights</legend>
            <p className="text-xs text-muted-foreground">Pick bullets from your experience to show under Leadership.</p>
            {bullets.map((b) => (
              <label key={b} className="flex items-start gap-2 text-sm">
                <Checkbox
                  className="mt-0.5"
                  checked={site.overrides.leadership.includes(b)}
                  disabled={busy}
                  onCheckedChange={(on) =>
                    save({
                      overrides: {
                        leadership: on === true ? [...site.overrides.leadership, b] : site.overrides.leadership.filter((x) => x !== b),
                      },
                    })
                  }
                />
                {b}
              </label>
            ))}
          </fieldset>
        )}
      </CardContent>
    </Card>
  );
}

export function BioCard({ site, save, busy }: CardProps) {
  const [text, setText] = useState(site.bio.text);
  const [person, setPerson] = useState<"first" | "third">("first");
  const draft = useDraftBio();
  const drafting = site.bio_draft.status === "pending";

  return (
    <Card>
      <CardHeader>
        <CardTitle>About me</CardTitle>
        <CardDescription>
          Shown in the About section instead of your profile summary. Write it yourself, or start from an AI draft
          based only on your profile. Nothing is published until you save it here.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        <Textarea rows={6} maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} aria-label="About me" />
        <div className="flex flex-wrap items-center gap-2">
          <Button size="sm" disabled={busy || text === site.bio.text} onClick={() => save({ bio_text: text })}>
            Save and approve
          </Button>
          {site.bio.approved_at && (
            <Badge variant="secondary">{site.bio.source === "ai" ? "AI draft, approved by you" : "Written by you"}</Badge>
          )}
        </div>

        <div className="grid gap-2 rounded-lg border p-3">
          <div className="flex flex-wrap items-center gap-2">
            <select
              aria-label="Writing style"
              className="h-8 rounded-md border border-input bg-transparent px-2 text-sm"
              value={person}
              onChange={(e) => setPerson(e.target.value as "first" | "third")}
            >
              <option value="first">First person (&ldquo;I&rdquo;)</option>
              <option value="third">Third person</option>
            </select>
            <Button size="sm" variant="outline" disabled={drafting || draft.isPending} onClick={() => draft.mutate(person)}>
              {drafting ? "Drafting…" : "Draft with AI"}
            </Button>
          </div>
          {site.bio_draft.status === "failed" && <p className="text-sm text-destructive">The draft couldn&apos;t be written. Please try again.</p>}
          {draft.isError && <p className="text-sm text-destructive">Couldn&apos;t start a draft. Please try again.</p>}
          {site.bio_draft.status === "done" && site.bio_draft.text && (
            <div className="grid gap-2">
              <p className="text-sm whitespace-pre-line">{site.bio_draft.text}</p>
              <div>
                <Button size="sm" variant="secondary" onClick={() => setText(site.bio_draft.text ?? "")}>
                  Use this draft
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">Check every fact, edit as you like, then save to approve.</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}


export function PublishCard({ site, save, busy }: CardProps) {
  const publish = usePublishWebsite("publish");
  const unpublish = usePublishWebsite("unpublish");
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const status = site.publish;
  const url = status.path && typeof window !== "undefined" ? `${window.location.origin}${status.path}` : status.path;
  const working = publish.isPending || unpublish.isPending;

  async function run(action: typeof publish) {
    setError(null);
    try {
      await action.mutateAsync();
    } catch (err) {
      const problems = err instanceof ApiError ? (err.body as { problems?: string[] } | null)?.problems : null;
      setError(problems?.join(" ") || "That didn't work. Please try again.");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Publish</CardTitle>
        <CardDescription>
          Publishing makes a copy of your site public. Later changes stay private until you publish again.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4">
        {status.published ? (
          <div className="grid gap-2 text-sm">
            <p>
              <Badge>Live</Badge> <span className="ml-1">Version {status.version}</span>
              <span className="text-muted-foreground">
                {" "}
                · published {status.published_at ? new Date(status.published_at).toLocaleString() : ""}
              </span>
            </p>
            {url && (
              <div className="flex flex-wrap gap-2">
                <Input readOnly value={url} className="min-w-0 flex-1 font-mono text-xs" onFocus={(e) => e.target.select()} />
                <Button
                  variant="outline"
                  onClick={async () => {
                    await navigator.clipboard.writeText(url);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                >
                  {copied ? "Copied" : "Copy"}
                </Button>
                <Button asChild variant="outline">
                  <a href={status.path ?? "#"} target="_blank" rel="noopener noreferrer">
                    Visit
                  </a>
                </Button>
              </div>
            )}
            {status.has_changes && <p className="text-amber-700 dark:text-amber-400">You have changes since you last published.</p>}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Not published yet.</p>
        )}

        {site.publish_problems.length > 0 && (
          <ul className="list-disc pl-5 text-sm text-muted-foreground">
            {site.publish_problems.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        )}

        <div className="grid gap-3 rounded-lg border p-3">
          <div className="flex items-center justify-between gap-4">
            <Label htmlFor="show-chatbot">Show the AI assistant on my site</Label>
            <Switch id="show-chatbot" checked={site.show_chatbot} disabled={busy} onCheckedChange={(v) => save({ show_chatbot: v })} />
          </div>
          <div className="flex items-center justify-between gap-4">
            <Label htmlFor="show-matching">Show job description matching on my site</Label>
            <Switch id="show-matching" checked={site.show_matching} disabled={busy} onCheckedChange={(v) => save({ show_matching: v })} />
          </div>
          <p className="text-xs text-muted-foreground">
            These also follow the assistant and matching switches on your Employer profile page.
          </p>
        </div>

        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button disabled={working || site.publish_problems.length > 0 || (status.published && !status.has_changes)} onClick={() => run(publish)}>
            {publish.isPending ? "Publishing…" : status.published ? "Publish changes" : "Publish site"}
          </Button>
          {status.published && (
            <Button
              variant="outline"
              disabled={working}
              onClick={() => window.confirm("Take your site offline? The link will stop working until you publish again.") && run(unpublish)}
            >
              {unpublish.isPending ? "Unpublishing…" : "Unpublish"}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
