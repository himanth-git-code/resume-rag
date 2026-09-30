import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { refHref } from "@/lib/validation/questions";
import type { Question } from "@/types/questions";

const DIFFICULTY_LABEL = { foundational: "Foundational", intermediate: "Intermediate", advanced: "Advanced" } as const;

function TalkingPoints({ points }: { points: Question["talking_points"] }) {
  if (points.length === 0) return null;
  return (
    <div className="grid gap-2">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">From your profile</p>
      <ul className="grid gap-1.5 text-sm">
        {points.map((point, i) => (
          <li key={i}>
            <Link href={refHref(point.ref)} className="font-medium underline-offset-4 hover:underline">
              {point.label}
            </Link>
            <span className="text-muted-foreground">: {point.text}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function QuestionCard({ question }: { question: Question }) {
  const extras = question.talking_points.length + question.follow_ups.length;

  return (
    <Card>
      <CardContent className="grid gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary" className="capitalize">
            {question.category}
          </Badge>
          <Badge variant="outline">{DIFFICULTY_LABEL[question.difficulty]}</Badge>
          {question.topic && <span className="text-xs text-muted-foreground">{question.topic}</span>}
        </div>
        <p className="font-medium">{question.text}</p>

        {extras > 0 && (
          <details className="group grid gap-3">
            <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
              {[
                question.talking_points.length > 0 && "talking points",
                question.follow_ups.length > 0 &&
                  `${question.follow_ups.length} follow-up${question.follow_ups.length === 1 ? "" : "s"}`,
              ]
                .filter(Boolean)
                .join(" · ")
                .replace(/^./, (c) => c.toUpperCase())}
            </summary>
            <div className="mt-3 grid gap-4">
              <TalkingPoints points={question.talking_points} />
              {question.follow_ups.length > 0 && (
                <div className="grid gap-2">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Likely follow-ups
                  </p>
                  <ol className="grid list-decimal gap-2 pl-5 text-sm">
                    {question.follow_ups.map((f) => (
                      <li key={f.id} className="grid gap-1">
                        <span>
                          {f.text}{" "}
                          <span className="text-xs text-muted-foreground">({DIFFICULTY_LABEL[f.difficulty]})</span>
                        </span>
                        <TalkingPoints points={f.talking_points} />
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
