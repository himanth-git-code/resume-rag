import type { Metadata } from "next";

// A private, shared-by-link page: keep it out of search engines.
export const metadata: Metadata = {
  title: "Candidate profile",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default function PublicProfileLayout({ children }: { children: React.ReactNode }) {
  return <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-10">{children}</main>;
}
