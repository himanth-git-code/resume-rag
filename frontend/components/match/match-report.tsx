import { Badge } from "@/components/ui/badge";
import type { JobMatch } from "@/types/match";

const STATUS = {
  met: { label: "Met", variant: "default" },
  partial: { label: "Partly met", variant: "secondary" },
  no_evidence: { label: "Not found in profile", variant: "outline" },
} as const;

export function MatchReport({ match }: { match: JobMatch }) {
  const strengths = match.summary.strengths ?? [];
  const gaps = match.summary.gaps ?? [];

  return (
    <div className="grid gap-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm text-muted-foreground">{match.job_title || "Job description"}</p>
          <p className="text-4xl font-semibold tracking-tight">
            {match.score === null ? "—" : `${match.score}%`}
            <span className="ml-2 text-base font-normal text-muted-foreground">match</span>
          </p>
        </div>
        <p className="text-sm text-muted-foreground">
          {match.requirements.filter((r) => r.status === "met").length} of {match.requirements.length} requirements met
        </p>
      </div>

      {match.requirements.length === 0 && (
        <p className="text-sm text-muted-foreground">No job requirements could be identified in this description.</p>
      )}

      <ul className="grid gap-3">
        {match.requirements.map((r, i) => (
          <li key={i} className="grid gap-1.5 rounded-lg border p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <span className="font-medium">{r.text}</span>
              <div className="flex gap-1.5">
                {r.importance === "preferred" && <Badge variant="outline">Preferred</Badge>}
                <Badge variant={STATUS[r.status].variant}>{STATUS[r.status].label}</Badge>
              </div>
            </div>
            <p className="text-sm text-muted-foreground">{r.explanation}</p>
            {r.evidence.length > 0 && (
              <p className="text-xs text-muted-foreground">Evidence: {r.evidence.map((e) => e.label).join(" · ")}</p>
            )}
          </li>
        ))}
      </ul>

      {(strengths.length > 0 || gaps.length > 0) && (
        <div className="grid gap-4 sm:grid-cols-2">
          {strengths.length > 0 && (
            <div className="grid gap-1.5">
              <h3 className="text-sm font-semibold">Strengths</h3>
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {strengths.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {gaps.length > 0 && (
            <div className="grid gap-1.5">
              <h3 className="text-sm font-semibold">Required, not found in the profile</h3>
              <ul className="list-disc space-y-1 pl-5 text-sm">
                {gaps.map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-muted-foreground">{match.disclaimer}</p>
    </div>
  );
}

export function MatchProgress({ match }: { match: JobMatch | undefined }) {
  if (!match) return null;
  if (match.status === "failed") {
    return (
      <p role="alert" className="text-sm text-destructive">
        {match.error_message || "The job description couldn't be analysed. Please try again."}
      </p>
    );
  }
  if (match.status !== "done") {
    return (
      <p className="text-sm text-muted-foreground" aria-live="polite">
        Analysing the job description against the profile… this usually takes under a minute.
      </p>
    );
  }
  return <MatchReport match={match} />;
}
