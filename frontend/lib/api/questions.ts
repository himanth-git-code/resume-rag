import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { apiGet, apiSend } from "@/lib/api/client";
import {
  facetsSchema,
  generationSchema,
  latestGenerationSchema,
  questionPageSchema,
  questionQuery,
  type QuestionFilters,
} from "@/lib/validation/questions";

const IN_FLIGHT = ["pending", "running"];

export function useQuestions(filters: QuestionFilters, page: number) {
  return useQuery({
    queryKey: ["questions", "list", filters, page],
    queryFn: () => apiGet(`/questions${questionQuery(filters, page)}`, questionPageSchema),
    placeholderData: keepPreviousData,
  });
}

export function useQuestionFacets() {
  return useQuery({ queryKey: ["questions", "facets"], queryFn: () => apiGet("/questions/facets", facetsSchema) });
}

/** Latest generation, polled while it runs; refreshes the question list as sections land. */
export function useLatestGeneration() {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["question-generation", "latest"],
    queryFn: () => apiGet("/questions/generations/latest", latestGenerationSchema),
    refetchInterval: (q) => {
      const status = q.state.data?.generation?.status;
      return status && IN_FLIGHT.includes(status) ? 3_000 : false;
    },
  });

  const progress = query.data?.generation
    ? `${query.data.generation.id}:${query.data.generation.status}:${query.data.generation.sections_done}`
    : null;
  const previous = useRef(progress);
  useEffect(() => {
    if (previous.current !== null && progress !== previous.current) {
      queryClient.invalidateQueries({ queryKey: ["questions"] });
      queryClient.invalidateQueries({ queryKey: ["me"] });
    }
    previous.current = progress;
  }, [progress, queryClient]);

  return query;
}

export function useGenerateQuestions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { kind: "full" | "more"; category?: string; source?: string }) =>
      apiSend("POST", "/questions/generate", generationSchema, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["question-generation"] }),
  });
}

export const isGenerating = (status: string | undefined) => Boolean(status && IN_FLIGHT.includes(status));
