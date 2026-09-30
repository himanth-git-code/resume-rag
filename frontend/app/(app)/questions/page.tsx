"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { GenerationBanner } from "@/components/questions/generation-banner";
import { QuestionCard } from "@/components/questions/question-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import {
  isGenerating,
  useGenerateQuestions,
  useLatestGeneration,
  useQuestionFacets,
  useQuestions,
} from "@/lib/api/questions";
import { cn } from "@/lib/utils";
import { CATEGORIES, DIFFICULTIES, type QuestionFilters } from "@/lib/validation/questions";

const SELECT =
  "h-9 rounded-md border border-input bg-transparent px-3 text-sm shadow-xs focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 outline-none";

const SOURCE_GROUP = { experience: "Roles", project: "Projects", skill: "Skills" } as Record<string, string>;

function useDebounced<T>(value: T, ms = 300): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(id);
  }, [value, ms]);
  return debounced;
}

export default function QuestionsPage() {
  const [filters, setFilters] = useState<Omit<QuestionFilters, "search">>({});
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebounced(search);
  const activeFilters = { ...filters, search: debouncedSearch };

  const latest = useLatestGeneration();
  const facets = useQuestionFacets();
  const questions = useQuestions(activeFilters, page);
  const generate = useGenerateQuestions();
  const [actionError, setActionError] = useState<string | null>(null);

  const generation = latest.data?.generation ?? null;
  const running = isGenerating(generation?.status);

  function update(next: Partial<QuestionFilters>) {
    setFilters((f) => ({ ...f, ...next }));
    setPage(1);
  }

  async function start(body: Parameters<typeof generate.mutateAsync>[0]) {
    setActionError(null);
    try {
      await generate.mutateAsync(body);
    } catch (error) {
      setActionError(
        error instanceof ApiError && error.status === 429
          ? "You've generated a lot of questions recently. Please try again later."
          : error instanceof ApiError && error.status === 409
            ? "Questions are already being generated."
            : "Couldn't start generating questions. Please try again.",
      );
    }
  }

  if (latest.isPending) return <p className="text-sm text-muted-foreground">Loading…</p>;
  if (latest.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Couldn&apos;t load your questions. Please refresh the page.
      </p>
    );
  }

  if (!latest.data.has_profile) {
    return (
      <div className="grid gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Interview questions</h1>
        <p className="text-sm text-muted-foreground">
          Questions are generated from your saved profile. Save your profile first and they&apos;ll appear here.
        </p>
        <div>
          <Button asChild>
            <Link href="/profile">Go to profile</Link>
          </Button>
        </div>
      </div>
    );
  }

  const total = facets.data?.total ?? 0;
  const sources = facets.data?.sources.filter((s) => SOURCE_GROUP[s.type]) ?? [];
  const results = questions.data?.results ?? [];
  const count = questions.data?.count ?? 0;

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Interview questions</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Practice questions based on your own profile. Talking points show which of your experiences to draw on;
            they never add anything that isn&apos;t in your profile.
          </p>
        </div>
        <div className="flex gap-2">
          {total > 0 && (
            <Button
              variant="outline"
              disabled={running || generate.isPending}
              onClick={() => start({ kind: "more", category: filters.category, source: filters.source })}
            >
              Generate more{filters.category || filters.source ? " like these" : ""}
            </Button>
          )}
          {!generation && (
            <Button disabled={generate.isPending} onClick={() => start({ kind: "full" })}>
              Generate questions
            </Button>
          )}
        </div>
      </div>

      <GenerationBanner
        generation={generation}
        profileChanged={latest.data.profile_changed}
        busy={running || generate.isPending}
        onRegenerate={() => start({ kind: "full" })}
      />
      {actionError && (
        <p role="alert" className="text-sm text-destructive">
          {actionError}
        </p>
      )}

      {total > 0 && (
        <div className="grid gap-4">
          <div className="flex flex-wrap gap-2" role="tablist" aria-label="Category">
            {[undefined, ...CATEGORIES].map((category) => {
              const n = category ? (facets.data?.categories[category] ?? 0) : total;
              if (category && n === 0) return null;
              const selected = filters.category === category;
              return (
                <Button
                  key={category ?? "all"}
                  role="tab"
                  aria-selected={selected}
                  size="sm"
                  variant={selected ? "default" : "outline"}
                  className="capitalize"
                  onClick={() => update({ category })}
                >
                  {category ?? "All"} <span className={cn("text-xs", !selected && "text-muted-foreground")}>{n}</span>
                </Button>
              );
            })}
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <div className="grid gap-1.5">
              <Label htmlFor="q-source">About</Label>
              <select
                id="q-source"
                className={SELECT}
                value={filters.source ?? ""}
                onChange={(e) => update({ source: e.target.value || undefined })}
              >
                <option value="">Everything</option>
                {Object.entries(SOURCE_GROUP).map(([type, group]) => {
                  const options = sources.filter((s) => s.type === type);
                  if (options.length === 0) return null;
                  return (
                    <optgroup key={type} label={group}>
                      {options.map((s) => (
                        <option key={s.ref} value={s.ref}>
                          {s.label} ({s.count})
                        </option>
                      ))}
                    </optgroup>
                  );
                })}
              </select>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="q-difficulty">Difficulty</Label>
              <select
                id="q-difficulty"
                className={cn(SELECT, "capitalize")}
                value={filters.difficulty ?? ""}
                onChange={(e) => update({ difficulty: (e.target.value || undefined) as QuestionFilters["difficulty"] })}
              >
                <option value="">Any</option>
                {DIFFICULTIES.map((d) => (
                  <option key={d} value={d}>
                    {d}
                  </option>
                ))}
              </select>
            </div>
            <div className="grid flex-1 gap-1.5">
              <Label htmlFor="q-search">Search</Label>
              <Input
                id="q-search"
                type="search"
                placeholder="e.g. caching"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
              />
            </div>
          </div>
        </div>
      )}

      {questions.isError && (
        <p role="alert" className="text-sm text-destructive">
          Couldn&apos;t load questions. Please refresh the page.
        </p>
      )}
      {total === 0 && !running && generation?.status !== "failed" && (
        <p className="text-sm text-muted-foreground">No questions yet.</p>
      )}
      {total > 0 && count === 0 && !questions.isPending && (
        <p className="text-sm text-muted-foreground">No questions match these filters.</p>
      )}

      <div className={cn("grid gap-4", questions.isPlaceholderData && "opacity-60")}>
        {results.map((q) => (
          <QuestionCard key={q.id} question={q} />
        ))}
      </div>

      {(questions.data?.previous || questions.data?.next) && (
        <div className="flex items-center justify-between text-sm">
          <Button variant="outline" size="sm" disabled={!questions.data?.previous} onClick={() => setPage((p) => p - 1)}>
            Previous
          </Button>
          <span className="text-muted-foreground">
            Page {page} of {Math.max(1, Math.ceil(count / 20))}
          </span>
          <Button variant="outline" size="sm" disabled={!questions.data?.next} onClick={() => setPage((p) => p + 1)}>
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
