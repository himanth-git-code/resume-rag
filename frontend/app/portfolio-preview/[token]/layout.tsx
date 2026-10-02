import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Website preview",
  robots: { index: false, follow: false, nocache: true },
  referrer: "no-referrer",
};

export default function PreviewLayout({ children }: { children: React.ReactNode }) {
  return children;
}
