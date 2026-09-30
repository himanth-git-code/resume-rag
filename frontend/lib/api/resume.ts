import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiGet, apiSend } from "@/lib/api/client";
import { resumeJobSchema, uploadErrorSchema } from "@/lib/validation/resume";
import type { ParseStatus, ResumeJob } from "@/types/resume";

const IN_PROGRESS: ParseStatus[] = ["pending", "parsing"];
const POLL_MS = 2_000;

export const isInProgress = (status: ParseStatus) => IN_PROGRESS.includes(status);

async function fetchLatestJob(): Promise<ResumeJob | null> {
  try {
    return await apiGet("/resumes/jobs/latest", resumeJobSchema);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

/** The candidate's latest parse job, polled while it's still processing. */
export function useLatestResumeJob() {
  return useQuery({
    queryKey: ["resume-job", "latest"],
    queryFn: fetchLatestJob,
    refetchInterval: (query) => {
      const job = query.state.data;
      return job && isInProgress(job.status) ? POLL_MS : false;
    },
  });
}

function useInvalidateResumeState() {
  const queryClient = useQueryClient();
  return (job: ResumeJob) => {
    queryClient.setQueryData(["resume-job", "latest"], job);
    queryClient.invalidateQueries({ queryKey: ["me"] });
  };
}

export function useUploadResume() {
  const onSuccess = useInvalidateResumeState();
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return apiSend("POST", "/resumes", resumeJobSchema, form);
    },
    onSuccess,
  });
}

export function useRetryResumeJob() {
  const onSuccess = useInvalidateResumeState();
  return useMutation({
    mutationFn: (jobId: number) => apiSend("POST", `/resumes/jobs/${jobId}/retry`, resumeJobSchema),
    onSuccess,
  });
}

/** The server's user-facing message for a rejected upload. */
export function uploadErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    const parsed = uploadErrorSchema.safeParse(error.body);
    if (parsed.success) return parsed.data.detail;
    if (error.status === 429) return "You've uploaded several files recently. Please wait a while and try again.";
    if (error.status === 413) return "This file is too large.";
  }
  return "The upload failed. Please check your connection and try again.";
}
