"use client";

import { use } from "react";

import { ChatPanel } from "@/components/public-profile/chat-panel";
import { MatchPanel } from "@/components/public-profile/match-panel";
import { ProfileView } from "@/components/public-profile/profile-view";
import { usePublicProfile } from "@/lib/api/employer-profile";

export default function PublicProfilePage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params);
  const { data, isPending, isError } = usePublicProfile(token);

  if (isPending) return <p className="text-sm text-muted-foreground">Loading profile…</p>;
  if (isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        This profile couldn&apos;t be loaded right now. Please try again shortly.
      </p>
    );
  }
  if (data === null) {
    return (
      <div className="grid gap-2 py-16 text-center">
        <h1 className="text-xl font-semibold">This profile isn&apos;t available</h1>
        <p className="text-sm text-muted-foreground">The link may have expired or been turned off by the candidate.</p>
      </div>
    );
  }

  return (
    <div className="grid gap-10">
      <ProfileView profile={data.profile} />
      {data.chatbot_enabled && (
        <ChatPanel
          apiBase={`/public/p/${encodeURIComponent(token)}`}
          name={data.profile.full_name || "this candidate"}
          turnstileSiteKey={data.turnstile_site_key}
        />
      )}
      {data.matching_enabled && (
        <MatchPanel
          apiBase={`/public/p/${encodeURIComponent(token)}`}
          name={data.profile.full_name || "this candidate"}
          turnstileSiteKey={data.turnstile_site_key}
        />
      )}
      <p className="text-center text-xs text-muted-foreground">
        AI answers are based only on the candidate&apos;s own profile and may be incomplete.
      </p>
    </div>
  );
}
