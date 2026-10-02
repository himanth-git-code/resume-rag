import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { cache } from "react";

import { SiteRenderer } from "@/components/website-templates/site-renderer";
import { SiteWidgets } from "@/components/website-templates/site-widgets";
import { fetchSiteData } from "@/lib/site-server";

type Props = { params: Promise<{ slug: string }> };

// One backend request per page render, shared by metadata and the page.
const getSite = cache((slug: string) => fetchSiteData(`/api/public/sites/${encodeURIComponent(slug)}/`));

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const site = await getSite(slug);
  if (!site) return { title: "Not found", robots: { index: false } };
  const siteUrl = process.env.SITE_URL;
  return {
    title: site.meta.title,
    description: site.meta.description || undefined,
    openGraph: { type: "profile", title: site.meta.title, description: site.meta.description || undefined },
    ...(siteUrl ? { metadataBase: new URL(siteUrl), alternates: { canonical: `/portfolio/${slug}` } } : {}),
  };
}

export default async function PortfolioPage({ params }: Props) {
  const { slug } = await params;
  const site = await getSite(slug);
  if (!site) notFound();
  return <SiteRenderer site={site} widgets={<SiteWidgets site={site} />} />;
}
