"use client";

import { useState } from "react";

import { LoadState, formatDateTime } from "@/components/admin/bits";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { SECTION_TITLES } from "@/lib/admin/sample-site";
import { errorDetail } from "@/lib/admin/errors";
import { useAdminTemplates, useRestoreTemplates, useTemplateVersions, useUpdateTemplate } from "@/lib/api/admin";
import { sectionRows, templatePreviewHref, type adminTemplateSchema } from "@/lib/validation/admin";
import { moveItem } from "@/lib/validation/website";
import type { z } from "zod";

type Template = z.infer<typeof adminTemplateSchema>;

const title = (key: string) => (SECTION_TITLES as Record<string, string>)[key] ?? key;

function TemplateCard({ template }: { template: Template }) {
  const update = useUpdateTemplate();
  const [name, setName] = useState(template.name);
  const [description, setDescription] = useState(template.description);
  const [rows, setRows] = useState(() => sectionRows(template.supported, template.sections));
  const chosen = rows.filter((r) => r.on).map((r) => r.key);
  const dirty =
    name !== template.name || description !== template.description || chosen.join() !== template.sections.join();

  const save = (values: Parameters<typeof update.mutate>[0]) => update.mutate(values);

  return (
    <Card>
      <CardContent className="grid gap-4 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <h2 className="text-base font-medium">{template.name}</h2>
            <span className="font-mono text-xs text-muted-foreground">{template.key}</span>
            {!template.enabled && <Badge variant="outline">Hidden</Badge>}
          </div>
          <span className="text-xs text-muted-foreground">
            Used by {template.sites} site{template.sites === 1 ? "" : "s"} ({template.published_sites} published)
          </span>
        </div>

        <div className="flex flex-wrap gap-6">
          <label className="flex items-center gap-2">
            <Switch
              checked={template.enabled}
              disabled={update.isPending}
              onCheckedChange={(enabled) => save({ key: template.key, enabled })}
            />
            Available to candidates
          </label>
          <label className="flex items-center gap-2">
            <Switch
              checked={template.premium}
              disabled={update.isPending}
              onCheckedChange={(premium) => save({ key: template.key, premium })}
            />
            Pro only
          </label>
        </div>

        <div className="grid gap-2">
          <Label htmlFor={`name-${template.key}`}>Name</Label>
          <Input id={`name-${template.key}`} maxLength={60} value={name} onChange={(e) => setName(e.target.value)} />
          <Label htmlFor={`desc-${template.key}`}>Description</Label>
          <Textarea id={`desc-${template.key}`} maxLength={300} rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>

        <div className="grid gap-1">
          <span className="text-xs text-muted-foreground">Default sections for new sites (top to bottom)</span>
          {rows.map((r, i) => (
            <div key={r.key} className="flex items-center gap-2">
              <input
                type="checkbox"
                aria-label={`Include ${title(r.key)}`}
                checked={r.on}
                onChange={() => setRows(rows.map((x) => (x.key === r.key ? { ...x, on: !x.on } : x)))}
              />
              <span className={r.on ? undefined : "text-muted-foreground"}>{title(r.key)}</span>
              <span className="ml-auto flex gap-1">
                <Button size="xs" variant="ghost" aria-label={`Move ${title(r.key)} up`} disabled={i === 0} onClick={() => setRows(moveItem(rows, i, i - 1))}>
                  ↑
                </Button>
                <Button
                  size="xs"
                  variant="ghost"
                  aria-label={`Move ${title(r.key)} down`}
                  disabled={i === rows.length - 1}
                  onClick={() => setRows(moveItem(rows, i, i + 1))}
                >
                  ↓
                </Button>
              </span>
            </div>
          ))}
        </div>

        {update.isError && (
          <p role="alert" className="text-destructive">
            {errorDetail(update.error)}
          </p>
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <Button asChild size="sm" variant="outline">
            <a href={templatePreviewHref(template.key, chosen.length ? chosen : template.sections)} target="_blank" rel="noopener">
              Preview
            </a>
          </Button>
          <Button
            size="sm"
            disabled={!dirty || !chosen.length || !name.trim() || update.isPending}
            onClick={() => save({ key: template.key, name: name.trim(), description: description.trim(), default_sections: chosen })}
          >
            {update.isPending ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function Versions() {
  const { data } = useTemplateVersions();
  const restore = useRestoreTemplates();
  if (!data?.results.length) return null;
  return (
    <Card>
      <CardContent className="grid gap-2 text-sm">
        <h2 className="font-medium">Version history</h2>
        {restore.isError && (
          <p role="alert" className="text-destructive">
            {errorDetail(restore.error)}
          </p>
        )}
        {data.results.map((v, i) => (
          <div key={v.number} className="flex flex-wrap items-center justify-between gap-2 border-b pb-2 last:border-0 last:pb-0">
            <span>
              <span className="font-medium">v{v.number}</span> · {v.note}
              <span className="text-xs text-muted-foreground">
                {" "}
                · {v.changed_by ?? "unknown"} · {formatDateTime(v.created_at)}
              </span>
            </span>
            {i === 0 ? (
              <Badge variant="secondary">Current</Badge>
            ) : (
              <Button
                size="sm"
                variant="outline"
                disabled={restore.isPending}
                onClick={() => {
                  if (window.confirm(`Restore the catalog to version ${v.number}?`)) restore.mutate(v.number);
                }}
              >
                Restore
              </Button>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

export default function AdminTemplatesPage() {
  const { data, isPending, isError } = useAdminTemplates();
  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Templates</h1>
        <p className="text-sm text-muted-foreground">
          Layouts live in code; here you control which templates candidates can pick, which need Pro, and their default sections.
          Hidden templates keep serving already-published sites.
        </p>
      </div>
      <LoadState isPending={isPending} isError={isError} />
      {data?.map((t) => (
        <TemplateCard key={`${t.key}-${t.name}-${t.description}-${t.sections.join()}`} template={t} />
      ))}
      <Versions />
    </div>
  );
}
