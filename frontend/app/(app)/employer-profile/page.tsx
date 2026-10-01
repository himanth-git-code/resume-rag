"use client";

import Link from "next/link";
import { useState } from "react";

import { Conversations } from "@/components/employer-profile/conversations";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  useEmployerProfile,
  useProfileActivity,
  useRegenerateLink,
  useUpdateEmployerProfile,
} from "@/lib/api/employer-profile";
import { endOfDayIso, SECTION_LABEL, SECTIONS } from "@/lib/validation/employer-profile";

const EVENT_LABEL = { view: "Profile viewed", chat_session: "Chat started", match: "Job match run" } as const;

function Toggle({
  id,
  label,
  hint,
  checked,
  disabled,
  onChange,
}: {
  id: string;
  label: string;
  hint?: string;
  checked: boolean;
  disabled?: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="grid gap-0.5">
        <Label htmlFor={id}>{label}</Label>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      <Switch id={id} checked={checked} disabled={disabled} onCheckedChange={onChange} />
    </div>
  );
}

export default function EmployerProfilePage() {
  const settings = useEmployerProfile();
  const update = useUpdateEmployerProfile();
  const regenerate = useRegenerateLink();
  const activity = useProfileActivity();
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Earliest selectable expiry date (tomorrow), computed once rather than on every render.
  const [minExpiry] = useState(() => new Date(Date.now() + 86_400_000).toISOString().slice(0, 10));

  if (settings.isPending) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (settings.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load your employer profile settings. Please refresh the page.
      </p>
    );
  }

  const data = settings.data;
  const url = typeof window === "undefined" ? data.path : `${window.location.origin}${data.path}`;
  const expiresOn = data.expires_at ? data.expires_at.slice(0, 10) : "";

  async function save(changes: Parameters<typeof update.mutateAsync>[0]) {
    setError(null);
    try {
      await update.mutateAsync(changes);
    } catch {
      setError("Your change couldn't be saved. Please try again.");
    }
  }

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Employer profile</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Share a private link with employers. They see the sections you choose and can ask an AI assistant questions
          answered only from your saved profile.
        </p>
      </div>

      {data.has_profile === false && (
        <Alert>
          <AlertDescription className="flex flex-wrap items-center justify-between gap-3">
            <span>Save your profile first; the link shows nothing until you do.</span>
            <Button asChild size="sm" variant="outline">
              <Link href="/profile">Go to profile</Link>
            </Button>
          </AlertDescription>
        </Alert>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Sharing</CardTitle>
          <CardDescription>Anyone with the link can view your profile while sharing is on.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-5">
          <Toggle
            id="enabled"
            label="Share my profile"
            checked={data.enabled}
            disabled={update.isPending}
            onChange={(enabled) => save({ enabled })}
          />
          <div className="grid gap-1.5">
            <Label htmlFor="link">Your link</Label>
            <div className="flex flex-wrap gap-2">
              <Input id="link" readOnly value={url} className="min-w-0 flex-1 font-mono text-xs" onFocus={(e) => e.target.select()} />
              <Button
                variant="outline"
                onClick={async () => {
                  await navigator.clipboard.writeText(url);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
              >
                {copied ? "Copied" : "Copy"}
              </Button>
              <Button asChild variant="outline">
                <a href={data.path} target="_blank" rel="noopener noreferrer">
                  Preview
                </a>
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              {data.enabled ? "Live." : "Turned off: the link shows “not available”."} Created{" "}
              {new Date(data.token_created_at).toLocaleDateString()}.
            </p>
          </div>
          <div className="flex flex-wrap items-end gap-4">
            <div className="grid gap-1.5">
              <Label htmlFor="expires">Expires on (optional)</Label>
              <Input
                id="expires"
                type="date"
                value={expiresOn}
                min={minExpiry}
                onChange={(e) => save({ expires_at: e.target.value ? endOfDayIso(e.target.value) : null })}
              />
            </div>
            <Button
              variant="outline"
              disabled={regenerate.isPending}
              onClick={() => {
                if (window.confirm("Create a new link? The current link will stop working immediately.")) {
                  regenerate.mutate();
                }
              }}
            >
              {regenerate.isPending ? "Creating…" : "Create new link"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>What employers can see</CardTitle>
          <CardDescription>Hidden sections are left off the page and are never used by the assistant.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          {SECTIONS.map((section) => (
            <Toggle
              key={section}
              id={`section-${section}`}
              label={SECTION_LABEL[section].label}
              hint={SECTION_LABEL[section].hint}
              checked={data.visible_sections[section] ?? false}
              disabled={update.isPending}
              onChange={(value) => save({ visible_sections: { ...data.visible_sections, [section]: value } })}
            />
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>AI features</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4">
          <Toggle
            id="chatbot"
            label="Assistant"
            hint="Employers can ask questions; answers come only from the sections above."
            checked={data.chatbot_enabled}
            disabled={update.isPending}
            onChange={(chatbot_enabled) => save({ chatbot_enabled })}
          />
          <Toggle
            id="matching"
            label="Job description matching"
            hint="Employers can paste a job description and see how your profile matches, with evidence."
            checked={data.matching_enabled}
            disabled={update.isPending}
            onChange={(matching_enabled) => save({ matching_enabled })}
          />
        </CardContent>
      </Card>

      <Conversations />

      <Card>
        <CardHeader>
          <CardTitle>Activity</CardTitle>
          {activity.data && (
            <CardDescription>
              {activity.data.views} views from {activity.data.unique_visitors} visitors
            </CardDescription>
          )}
        </CardHeader>
        <CardContent>
          {activity.isPending && <p className="text-sm text-muted-foreground">Loading…</p>}
          {activity.data?.results.length === 0 && <p className="text-sm text-muted-foreground">No activity yet.</p>}
          <ul className="grid gap-2 text-sm">
            {activity.data?.results.map((event) => (
              <li key={event.id} className="flex justify-between gap-4">
                <span>{EVENT_LABEL[event.kind]}</span>
                <span className="text-muted-foreground">{new Date(event.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
