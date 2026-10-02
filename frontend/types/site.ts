/** The render contract produced by the backend's WebsiteService.build_site_data. */

type Nullable<T> = T | null | undefined;

export type SiteTheme = { palette: string; mode: "light" | "dark"; font: string };

export type SiteExperience = {
  company: Nullable<string>;
  title: Nullable<string>;
  location: Nullable<string>;
  start_date: Nullable<string>;
  end_date: Nullable<string>;
  is_current: Nullable<boolean>;
  description: Nullable<string>;
  responsibilities: string[];
  achievements: string[];
  technologies: string[];
};

export type SiteProject = {
  name: string;
  role: Nullable<string>;
  description: Nullable<string>;
  technologies: string[];
  url: Nullable<string>;
  start_date: Nullable<string>;
  end_date: Nullable<string>;
};

export type SkillGroup = { category: Nullable<string>; items: string[] };

export type SiteContent = {
  about?: { intro: Nullable<string>; text: Nullable<string> };
  experience?: SiteExperience[];
  leadership?: string[];
  achievements?: { title: string; description: Nullable<string>; date: Nullable<string> }[];
  highlights?: { text: string; context: Nullable<string> }[];
  skills?: SkillGroup[];
  tech_stack?: { groups: SkillGroup[]; also_used: string[] };
  projects?: SiteProject[];
  github?: { label: string; url: string };
  education?: {
    institution: Nullable<string>;
    degree: Nullable<string>;
    field_of_study: Nullable<string>;
    start_date: Nullable<string>;
    end_date: Nullable<string>;
    grade: Nullable<string>;
  }[];
  certifications?: { name: string; issuer: Nullable<string>; issue_date: Nullable<string>; url: Nullable<string> }[];
  contact?: {
    email: Nullable<string>;
    phone: Nullable<string>;
    location: Nullable<string>;
    links: { label: Nullable<string>; url: string }[];
  };
};

export type SiteSectionKey = keyof SiteContent;

export type SiteData = {
  version: number;
  template: "executive" | "modern" | "technical" | "creative" | "minimal";
  theme: SiteTheme;
  hero: { name: string; headline: Nullable<string>; tagline: Nullable<string>; location: Nullable<string> };
  sections: { key: SiteSectionKey; title: string }[];
  content: SiteContent;
  widgets: { chatbot: boolean; matching: boolean; slug?: string; turnstile_site_key?: string | null };
  meta: { title: string; description: string };
};
