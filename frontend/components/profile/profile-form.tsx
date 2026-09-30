"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { FormProvider, useForm } from "react-hook-form";

import { CheckboxField, TextAreaField, TextField } from "@/components/profile/fields";
import { RepeatableSection } from "@/components/profile/repeatable-section";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError } from "@/lib/api/client";
import { useSaveProfile } from "@/lib/api/profile";
import { flattenServerErrors, profileFormSchema, toPayload } from "@/lib/validation/profile";
import type { ProfileFormValues } from "@/types/profile";

const NEW = "candidate_input" as const;
const LINES_HINT = "One per line.";
const COMMAS_HINT = "Separate with commas.";

type Props = {
  defaultValues: ProfileFormValues;
  /** The parse job being reviewed, if the form was filled from an AI draft. */
  jobId: number | null;
  onSaved: () => void;
};

export function ProfileForm({ defaultValues, jobId, onSaved }: Props) {
  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileFormSchema),
    defaultValues,
    mode: "onBlur",
  });
  const save = useSaveProfile();
  const [formError, setFormError] = useState<string | null>(null);

  const onSubmit = form.handleSubmit(
    async (values) => {
      setFormError(null);
      try {
        await save.mutateAsync(toPayload(values, jobId));
        form.reset(values);
        onSaved();
      } catch (error) {
        if (error instanceof ApiError && error.status === 400) {
          const problems = flattenServerErrors(error.body);
          for (const { path, message } of problems) {
            form.setError(path as never, { message });
          }
          setFormError("Some fields need attention. Please check the highlighted entries.");
        } else if (error instanceof ApiError && error.status === 409) {
          setFormError("This resume hasn't finished processing yet. Please wait a moment and try again.");
        } else {
          setFormError("Your changes couldn't be saved. Please try again.");
        }
      }
    },
    () => setFormError("Some fields need attention. Please check the highlighted entries."),
  );

  return (
    <FormProvider {...form}>
      <form onSubmit={onSubmit} noValidate className="grid gap-6 pb-24">
        <Card>
          <CardHeader>
            <CardTitle>Basics</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <TextField name="full_name" label="Full name" />
            <TextField name="headline" label="Headline" hint="Your professional title, e.g. Senior Backend Engineer." />
            <TextField name="email" label="Contact email" type="email" />
            <TextField name="phone" label="Phone" type="tel" />
            <TextField name="location" label="Location" />
            <TextAreaField name="summary" label="Summary" rows={4} className="sm:col-span-2" />
          </CardContent>
        </Card>

        <RepeatableSection
          name="experience"
          title="Experience"
          itemLabel="Role"
          emptyItem={{
            source_type: NEW,
            company: "",
            title: "",
            location: "",
            start_date: "",
            end_date: "",
            is_current: false,
            description: "",
            responsibilities: "",
            achievements: "",
            technologies: "",
          }}
          summarize={(e) => [e.title, e.company].filter(Boolean).join(" · ")}
          renderItem={(i) => (
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField name={`experience.${i}.company`} label="Company" />
              <TextField name={`experience.${i}.title`} label="Job title" />
              <TextField name={`experience.${i}.location`} label="Location" />
              <div className="grid grid-cols-2 gap-4">
                <TextField name={`experience.${i}.start_date`} label="Start" hint="e.g. Jan 2020" />
                <TextField name={`experience.${i}.end_date`} label="End" hint="e.g. Present" />
              </div>
              <CheckboxField name={`experience.${i}.is_current`} label="I currently work here" className="sm:col-span-2" />
              <TextAreaField name={`experience.${i}.description`} label="Description" className="sm:col-span-2" />
              <TextAreaField
                name={`experience.${i}.responsibilities`}
                label="Responsibilities"
                hint={LINES_HINT}
                rows={4}
                className="sm:col-span-2"
              />
              <TextAreaField
                name={`experience.${i}.achievements`}
                label="Achievements"
                hint={LINES_HINT}
                rows={3}
                className="sm:col-span-2"
              />
              <TextField
                name={`experience.${i}.technologies`}
                label="Technologies"
                hint={COMMAS_HINT}
                className="sm:col-span-2"
              />
            </div>
          )}
        />

        <RepeatableSection
          name="skills"
          title="Skills"
          itemLabel="Skill"
          emptyItem={{ source_type: NEW, name: "", category: "" }}
          summarize={(k) => k.name}
          renderItem={(i) => (
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField name={`skills.${i}.name`} label="Skill" />
              <TextField name={`skills.${i}.category`} label="Category" hint="Optional, e.g. Languages" />
            </div>
          )}
        />

        <RepeatableSection
          name="education"
          title="Education"
          itemLabel="Education"
          emptyItem={{
            source_type: NEW,
            institution: "",
            degree: "",
            field_of_study: "",
            start_date: "",
            end_date: "",
            grade: "",
          }}
          summarize={(e) => [e.degree, e.institution].filter(Boolean).join(" · ")}
          renderItem={(i) => (
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField name={`education.${i}.institution`} label="Institution" />
              <TextField name={`education.${i}.degree`} label="Degree" />
              <TextField name={`education.${i}.field_of_study`} label="Field of study" />
              <TextField name={`education.${i}.grade`} label="Grade" />
              <TextField name={`education.${i}.start_date`} label="Start" />
              <TextField name={`education.${i}.end_date`} label="End" />
            </div>
          )}
        />

        <RepeatableSection
          name="projects"
          title="Projects"
          itemLabel="Project"
          emptyItem={{
            source_type: NEW,
            name: "",
            role: "",
            description: "",
            technologies: "",
            url: "",
            start_date: "",
            end_date: "",
          }}
          summarize={(p) => p.name}
          renderItem={(i) => (
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField name={`projects.${i}.name`} label="Name" />
              <TextField name={`projects.${i}.role`} label="Your role" />
              <TextField name={`projects.${i}.start_date`} label="Start" />
              <TextField name={`projects.${i}.end_date`} label="End" />
              <TextField name={`projects.${i}.url`} label="Link" type="url" />
              <TextField name={`projects.${i}.technologies`} label="Technologies" hint={COMMAS_HINT} />
              <TextAreaField name={`projects.${i}.description`} label="Description" className="sm:col-span-2" />
            </div>
          )}
        />

        <RepeatableSection
          name="certifications"
          title="Certifications"
          itemLabel="Certification"
          emptyItem={{
            source_type: NEW,
            name: "",
            issuer: "",
            issue_date: "",
            expiry_date: "",
            credential_id: "",
            url: "",
          }}
          summarize={(c) => c.name}
          renderItem={(i) => (
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField name={`certifications.${i}.name`} label="Name" />
              <TextField name={`certifications.${i}.issuer`} label="Issuer" />
              <TextField name={`certifications.${i}.issue_date`} label="Issued" />
              <TextField name={`certifications.${i}.expiry_date`} label="Expires" />
              <TextField name={`certifications.${i}.credential_id`} label="Credential ID" />
              <TextField name={`certifications.${i}.url`} label="Link" type="url" />
            </div>
          )}
        />

        <RepeatableSection
          name="achievements"
          title="Achievements"
          itemLabel="Achievement"
          emptyItem={{ source_type: NEW, title: "", description: "", date: "" }}
          summarize={(a) => a.title}
          renderItem={(i) => (
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField name={`achievements.${i}.title`} label="Title" />
              <TextField name={`achievements.${i}.date`} label="Date" />
              <TextAreaField name={`achievements.${i}.description`} label="Description" className="sm:col-span-2" />
            </div>
          )}
        />

        <RepeatableSection
          name="links"
          title="Links"
          itemLabel="Link"
          emptyItem={{ source_type: NEW, label: "", url: "" }}
          summarize={(l) => l.label || l.url}
          renderItem={(i) => (
            <div className="grid gap-4 sm:grid-cols-2">
              <TextField name={`links.${i}.label`} label="Label" hint="e.g. LinkedIn, GitHub" />
              <TextField name={`links.${i}.url`} label="URL" type="url" />
            </div>
          )}
        />

        <div className="fixed inset-x-0 bottom-0 border-t bg-background/95 backdrop-blur">
          <div className="mx-auto flex w-full max-w-4xl flex-wrap items-center justify-between gap-3 px-6 py-3">
            <div className="min-h-5 text-sm" aria-live="polite">
              {formError ? (
                <span className="text-destructive">{formError}</span>
              ) : form.formState.isDirty ? (
                <span className="text-muted-foreground">You have unsaved changes.</span>
              ) : null}
            </div>
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? "Saving…" : jobId ? "Save to my profile" : "Save changes"}
            </Button>
          </div>
        </div>
      </form>
    </FormProvider>
  );
}
