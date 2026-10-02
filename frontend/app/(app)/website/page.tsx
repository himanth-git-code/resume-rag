"use client";

import Link from "next/link";
import { useState } from "react";

import {
  AddressCard,
  BioCard,
  ContentCard,
  PublishCard,
  SectionsCard,
  TemplateCard,
  ThemeCard,
} from "@/components/website-editor/editor-cards";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import { useProfile } from "@/lib/api/profile";
import { useOpenPreview, useUpdateWebsite, useWebsite, useWebsiteCatalog } from "@/lib/api/website";
import type { WebsiteUpdate } from "@/types/website";

export default function WebsitePage() {
  const website = useWebsite();
  const catalog = useWebsiteCatalog();
  const profile = useProfile();
  const update = useUpdateWebsite();
  const preview = useOpenPreview();
  const [error, setError] = useState<string | null>(null);

  if (website.isPending || catalog.isPending || profile.isPending) {
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  }
  if (website.isError || catalog.isError || profile.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load your website settings. Please refresh the page.
      </p>
    );
  }

  const site = website.data;
  async function save(changes: WebsiteUpdate) {
    setError(null);
    try {
      await update.mutateAsync(changes);
    } catch (err) {
      const slugError =
        err instanceof ApiError && err.status === 400 && (err.body as { slug?: string[] } | null)?.slug?.[0];
      setError(slugError || "Your change couldn't be saved. Please try again.");
    }
  }

  async function openPreview() {
    // Open the tab synchronously (popup blockers), then point it at the fresh preview link.
    const tab = window.open("about:blank", "_blank");
    try {
      const { path } = await preview.mutateAsync();
      if (tab) tab.location.href = path;
      else window.location.href = path;
    } catch {
      tab?.close();
      setError("Couldn't open a preview. Please try again.");
    }
  }

  const cardProps = { site, save, busy: update.isPending };

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Website</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            A personal website built from your saved profile. Preview privately, then publish when you&apos;re ready.
          </p>
        </div>
        <Button variant="outline" disabled={preview.isPending || !site.has_profile} onClick={openPreview}>
          {preview.isPending ? "Opening…" : "Open preview"}
        </Button>
      </div>

      {!site.has_profile && (
        <Alert>
          <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
            <span>Save your profile first; your website is built from it.</span>
            <Button asChild size="sm" variant="outline">
              <Link href="/profile">Go to profile</Link>
            </Button>
          </AlertDescription>
        </Alert>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <PublishCard {...cardProps} />
      <AddressCard key={`address-${site.slug}`} {...cardProps} />
      <TemplateCard {...cardProps} catalog={catalog.data} />
      <ThemeCard {...cardProps} catalog={catalog.data} />
      <SectionsCard key={`sections-${site.template}`} {...cardProps} catalog={catalog.data} />
      <ContentCard {...cardProps} profile={profile.data} />
      <BioCard key={`bio-${site.bio.approved_at}`} {...cardProps} />
    </div>
  );
}
