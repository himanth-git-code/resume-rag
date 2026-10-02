import { PreviewGuard } from "@/components/website-templates/preview-guard";
import { SiteRenderer } from "@/components/website-templates/site-renderer";
import { fetchSiteData } from "@/lib/site-server";

export default async function PreviewPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = await params;
  const site = await fetchSiteData(`/api/website/render/preview/${encodeURIComponent(token)}/`);

  if (!site) {
    return (
      <main className="grid min-h-screen place-items-center p-6 text-center">
        <div className="grid gap-2">
          <h1 className="text-xl font-semibold">This preview link has expired</h1>
          <p className="text-sm text-muted-foreground">Open a new preview from the website editor.</p>
        </div>
      </main>
    );
  }

  return (
    <PreviewGuard>
      <SiteRenderer site={site} />
    </PreviewGuard>
  );
}
