"use client";

import { ParseStatusPanel } from "@/components/resume/parse-status";
import { ResumeUploader } from "@/components/resume/resume-uploader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { isInProgress, useLatestResumeJob } from "@/lib/api/resume";

export default function ResumePage() {
  const { data: job, isPending, isError } = useLatestResumeJob();
  const processing = job ? isInProgress(job.status) : false;

  return (
    <div className="grid gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Resume</h1>
        <p className="text-sm text-muted-foreground">
          Upload your resume and we&apos;ll extract your professional details for you to review.
        </p>
      </div>

      {job && (
        <Card>
          <CardHeader>
            <CardTitle>Latest upload</CardTitle>
          </CardHeader>
          <CardContent>
            <ParseStatusPanel job={job} />
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{job ? "Upload a new version" : "Upload your resume"}</CardTitle>
          <CardDescription>Your file is stored privately and is only used to build your profile.</CardDescription>
        </CardHeader>
        <CardContent>
          {isPending ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : isError ? (
            <p role="alert" className="text-sm text-destructive">
              Couldn&apos;t load your resume status. Please refresh the page.
            </p>
          ) : (
            <ResumeUploader disabled={processing} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
