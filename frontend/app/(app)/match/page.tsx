"use client";

import { useState } from "react";

import { JobDescriptionForm } from "@/components/match/job-description-form";
import { MatchProgress } from "@/components/match/match-report";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { matchErrorMessage, useMatch, useMatchHistory, useStartMatch } from "@/lib/api/match";

export default function MatchPage() {
  const [matchId, setMatchId] = useState<string | null>(null);
  const start = useStartMatch();
  const match = useMatch(matchId);
  const history = useMatchHistory();

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Job match</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          Check how your profile matches a job before you apply. Each requirement is marked against evidence from
          your own profile, so you can see what to highlight and what&apos;s missing.
        </p>
      </div>

      <Card>
        <CardContent className="grid gap-5">
          {matchId === null ? (
            <JobDescriptionForm
              pending={start.isPending}
              onSubmit={async (jobDescription) => {
                try {
                  setMatchId((await start.mutateAsync(jobDescription)).id);
                } catch (err) {
                  throw new Error(matchErrorMessage(err));
                }
              }}
            />
          ) : (
            <>
              <MatchProgress match={match.data} />
              <div>
                <Button variant="outline" size="sm" onClick={() => setMatchId(null)}>
                  Check another job
                </Button>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>History</CardTitle>
          <CardDescription>Your own checks, and matches employers ran on your shared profile.</CardDescription>
        </CardHeader>
        <CardContent>
          {history.data?.results.length === 0 && <p className="text-sm text-muted-foreground">No matches yet.</p>}
          <ul className="grid gap-2 text-sm">
            {history.data?.results.map((m) => (
              <li key={m.id}>
                <button
                  type="button"
                  className="flex w-full flex-wrap items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left hover:bg-muted"
                  onClick={() => setMatchId(m.id)}
                >
                  <span className="font-medium">{m.job_title || "Untitled job"}</span>
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <Badge variant="outline">{m.source === "candidate_self" ? "You" : "Employer"}</Badge>
                    {m.status === "done" ? `${m.score ?? "—"}%` : m.status}
                    <span>{new Date(m.created_at).toLocaleDateString()}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
