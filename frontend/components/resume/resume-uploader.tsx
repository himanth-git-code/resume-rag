"use client";

import { useRef, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { uploadErrorMessage, useUploadResume } from "@/lib/api/resume";
import { cn } from "@/lib/utils";
import { checkResumeFile, RESUME_ACCEPT, RESUME_MAX_MB } from "@/lib/validation/resume";

export function ResumeUploader({ disabled = false }: { disabled?: boolean }) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const upload = useUploadResume();
  const busy = disabled || upload.isPending;

  async function submit(file: File | undefined) {
    if (!file || busy) return;
    const problem = checkResumeFile(file);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    try {
      await upload.mutateAsync(file);
    } catch (err) {
      setError(uploadErrorMessage(err));
    } finally {
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="grid gap-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          if (!busy) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void submit(e.dataTransfer.files[0]);
        }}
        className={cn(
          "flex flex-col items-center gap-3 rounded-lg border border-dashed p-8 text-center transition-colors",
          dragging && "border-primary bg-muted",
          busy && "opacity-60",
        )}
      >
        <p className="text-sm">
          Drag your resume here, or{" "}
          <Button
            type="button"
            variant="link"
            className="h-auto p-0"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
          >
            choose a file
          </Button>
        </p>
        <p className="text-xs text-muted-foreground">PDF or Word (.docx), up to {RESUME_MAX_MB} MB</p>
        {upload.isPending && <p className="text-sm text-muted-foreground">Uploading…</p>}
        <input
          ref={inputRef}
          type="file"
          accept={RESUME_ACCEPT}
          className="sr-only"
          aria-label="Resume file"
          onChange={(e) => void submit(e.target.files?.[0])}
          disabled={busy}
        />
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
