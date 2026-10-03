import { notFound } from "next/navigation";

import { AdminOnly } from "@/components/admin/admin-guard";
import { SiteRenderer } from "@/components/website-templates/site-renderer";
import { isTemplateKey, sampleSiteData } from "@/lib/admin/sample-site";

export const metadata = { robots: { index: false, follow: false } };

/** Admin preview of a template rendered with built-in sample data (no candidate data). */
export default async function TemplatePreviewPage({
  params,
  searchParams,
}: {
  params: Promise<{ key: string }>;
  searchParams: Promise<{ sections?: string }>;
}) {
  const { key } = await params;
  const { sections } = await searchParams;
  if (!isTemplateKey(key)) notFound();
  const site = sampleSiteData(key, (sections ?? "").split(",").filter(Boolean));
  if (site.sections.length === 0) notFound();
  return (
    <AdminOnly padded>
      <SiteRenderer site={site} />
    </AdminOnly>
  );
}
