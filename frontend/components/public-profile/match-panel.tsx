"use client";

import { useState } from "react";

import { JobDescriptionForm } from "@/components/match/job-description-form";
import { MatchProgress } from "@/components/match/match-report";
import { Turnstile } from "@/components/public-profile/turnstile";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { matchErrorMessage, usePublicMatch, useStartPublicMatch } from "@/lib/api/match";

export function MatchPanel({ token, name, turnstileSiteKey }: { token: string; name: string; turnstileSiteKey: string | null }) {
  const [matchId, setMatchId] = useState<string | null>(null);
  const [botToken, setBotToken] = useState<string | null>(null);
  const start = useStartPublicMatch(token);
  const match = usePublicMatch(token, matchId);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Match a job</CardTitle>
        <CardDescription>
          Paste a job description to see which requirements {name}&apos;s profile shows evidence for.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        {matchId === null ? (
          <JobDescriptionForm
            pending={start.isPending}
            disabled={!!turnstileSiteKey && !botToken}
            onSubmit={async (jobDescription) => {
              try {
                const created = await start.mutateAsync({ job_description: jobDescription, turnstile_token: botToken });
                setMatchId(created.id);
                // Turnstile tokens are single-use; "Match another job" needs a fresh one.
                setBotToken(null);
              } catch (err) {
                setBotToken(null);
                throw new Error(matchErrorMessage(err));
              }
            }}
          >
            {turnstileSiteKey && <Turnstile siteKey={turnstileSiteKey} onToken={setBotToken} />}
          </JobDescriptionForm>
        ) : (
          <>
            <MatchProgress match={match.data} />
            {match.isError && <p className="text-sm text-destructive">Couldn&apos;t load the report.</p>}
            <div>
              <Button variant="outline" size="sm" onClick={() => setMatchId(null)}>
                Match another job
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
