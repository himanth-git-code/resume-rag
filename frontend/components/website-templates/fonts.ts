import { Inter, Lato, Merriweather, Playfair_Display, Source_Sans_3, Space_Grotesk } from "next/font/google";

const inter = Inter({ subsets: ["latin"], variable: "--font-site-inter", display: "swap" });
const playfair = Playfair_Display({ subsets: ["latin"], variable: "--font-site-playfair", display: "swap" });
const sourceSans = Source_Sans_3({ subsets: ["latin"], variable: "--font-site-source-sans", display: "swap" });
const grotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-site-grotesk", display: "swap" });
const merriweather = Merriweather({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-site-merriweather", display: "swap" });
const lato = Lato({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-site-lato", display: "swap" });

/** Font pairings offered in the editor (keys match the backend catalog). */
export const FONT_PAIRS: Record<string, { heading: string; body: string; classNames: string[] }> = {
  inter: { heading: "var(--font-site-inter)", body: "var(--font-site-inter)", classNames: [inter.variable] },
  serif: {
    heading: "var(--font-site-playfair)",
    body: "var(--font-site-source-sans)",
    classNames: [playfair.variable, sourceSans.variable],
  },
  grotesk: { heading: "var(--font-site-grotesk)", body: "var(--font-site-inter)", classNames: [grotesk.variable] },
  classic: {
    heading: "var(--font-site-merriweather)",
    body: "var(--font-site-lato)",
    classNames: [merriweather.variable, lato.variable],
  },
};
