import type { CSSProperties } from "react";

import type { SiteTheme } from "@/types/site";

import { FONT_PAIRS } from "./fonts";

/** Accent colours per palette, chosen for >= 4.5:1 contrast against the mode's background. */
const ACCENTS: Record<string, { light: string; dark: string }> = {
  slate: { light: "#334155", dark: "#cbd5e1" },
  ocean: { light: "#0b5c8a", dark: "#7cc4ef" },
  forest: { light: "#1f6b45", dark: "#86d3a6" },
  plum: { light: "#6b2f7a", dark: "#d6a6e3" },
  amber: { light: "#8a4b08", dark: "#f5c46b" },
  rose: { light: "#9f1d45", dark: "#f4a3bb" },
};

const BASE = {
  light: { bg: "#ffffff", fg: "#111827", muted: "#4b5563", card: "#f8fafc", border: "#e5e7eb", onAccent: "#ffffff" },
  dark: { bg: "#0b0f17", fg: "#f3f4f6", muted: "#9ca3af", card: "#141a24", border: "#273141", onAccent: "#0b0f17" },
};

/** CSS custom properties consumed by every template (bg-[var(--site-bg)] etc.). */
export function themeStyle(theme: SiteTheme): CSSProperties {
  const mode = theme.mode === "dark" ? "dark" : "light";
  const base = BASE[mode];
  const accent = (ACCENTS[theme.palette] ?? ACCENTS.slate)[mode];
  const fonts = FONT_PAIRS[theme.font] ?? FONT_PAIRS.inter;
  return {
    "--site-bg": base.bg,
    "--site-fg": base.fg,
    "--site-muted": base.muted,
    "--site-card": base.card,
    "--site-border": base.border,
    "--site-accent": accent,
    "--site-on-accent": base.onAccent,
    "--site-heading": fonts.heading,
    "--site-body": fonts.body,
    colorScheme: mode,
    fontFamily: "var(--site-body)",
  } as CSSProperties;
}

export const fontClassNames = Object.values(FONT_PAIRS)
  .flatMap((pair) => pair.classNames)
  .join(" ");
