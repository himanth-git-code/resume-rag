import { TEMPLATE_KEYS } from "@/lib/validation/site";
import type { SiteContent, SiteData, SiteSectionKey } from "@/types/site";

/** Section headings (mirrors backend apps/websites/catalog.SECTIONS). */
export const SECTION_TITLES: Record<SiteSectionKey, string> = {
  about: "About",
  experience: "Experience",
  leadership: "Leadership",
  achievements: "Achievements",
  highlights: "Technical highlights",
  skills: "Skills",
  tech_stack: "Technology stack",
  projects: "Projects",
  github: "GitHub",
  education: "Education",
  certifications: "Certifications",
  contact: "Contact",
};

/** Fictional sample candidate used only for admin template previews. */
const SAMPLE_CONTENT: Required<SiteContent> = {
  about: {
    intro: "Engineer who turns messy problems into dependable products.",
    text: "Ten years building data-heavy web platforms, most recently leading a team of six across payments and analytics.",
  },
  experience: [
    {
      company: "Example Corp",
      title: "Senior Software Engineer",
      location: "Bengaluru",
      start_date: "Mar 2021",
      end_date: null,
      is_current: true,
      description: "Leads the payments platform team.",
      responsibilities: ["Own the checkout and billing services", "Mentor four engineers"],
      achievements: ["Cut checkout latency by 40%"],
      technologies: ["Python", "Django", "PostgreSQL", "AWS"],
    },
    {
      company: "Sample Labs",
      title: "Software Engineer",
      location: "Remote",
      start_date: "Jun 2017",
      end_date: "Feb 2021",
      is_current: false,
      description: null,
      responsibilities: ["Built reporting dashboards"],
      achievements: [],
      technologies: ["TypeScript", "React"],
    },
  ],
  leadership: ["Led a six-person team through a platform migration", "Ran the engineering hiring loop"],
  achievements: [{ title: "Engineering excellence award", description: "For the payments re-architecture.", date: "2023" }],
  highlights: [{ text: "Designed an idempotent webhook pipeline", context: "Payments" }],
  skills: [
    { category: "Languages", items: ["Python", "TypeScript", "SQL"] },
    { category: "Platforms", items: ["AWS", "Docker", "PostgreSQL"] },
  ],
  tech_stack: {
    groups: [
      { category: "Backend", items: ["Django", "Celery", "PostgreSQL"] },
      { category: "Frontend", items: ["React", "Next.js"] },
    ],
    also_used: ["Redis", "Terraform"],
  },
  projects: [
    { name: "Ledger", role: "Lead", description: "Double-entry ledger for marketplace payouts.", technologies: ["Python"], url: null, start_date: "2022", end_date: null },
    { name: "Insights", role: null, description: "Self-serve analytics dashboards.", technologies: ["React"], url: null, start_date: "2019", end_date: "2020" },
  ],
  github: { label: "github.com/sample", url: "https://github.com/" },
  education: [
    { institution: "Sample Institute of Technology", degree: "B.Tech", field_of_study: "Computer Science", start_date: "2013", end_date: "2017", grade: null },
  ],
  certifications: [{ name: "Cloud Practitioner", issuer: "Sample Cloud", issue_date: "2022", url: null }],
  contact: { email: "alex@example.com", phone: null, location: "Bengaluru, India", links: [{ label: "LinkedIn", url: "https://www.linkedin.com/" }] },
};

export function isTemplateKey(key: string): key is SiteData["template"] {
  return (TEMPLATE_KEYS as readonly string[]).includes(key);
}

/** SiteData for previewing `template` with the given section order (unknown keys are dropped). */
export function sampleSiteData(template: SiteData["template"], sections: string[]): SiteData {
  const keys = sections.filter((k): k is SiteSectionKey => k in SECTION_TITLES);
  return {
    version: 1,
    template,
    theme: { palette: "slate", mode: "light", font: "inter" },
    hero: { name: "Alex Sample", headline: "Senior Software Engineer", tagline: "Sample data for template preview", location: "Bengaluru, India" },
    sections: keys.map((key) => ({ key, title: SECTION_TITLES[key] })),
    content: Object.fromEntries(keys.map((k) => [k, SAMPLE_CONTENT[k]])) as SiteContent,
    widgets: { chatbot: false, matching: false },
    meta: { title: "Template preview", description: "Sample data" },
  };
}
