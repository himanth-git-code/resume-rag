"use client";

import { Controller, get, useFormContext } from "react-hook-form";

import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import type { ProfileFormValues } from "@/types/profile";

type FieldProps = {
  // Dotted react-hook-form path, e.g. "experience.0.company".
  name: string;
  label: string;
  hint?: string;
  className?: string;
};

function useFieldError(name: string): string | undefined {
  const {
    formState: { errors },
  } = useFormContext<ProfileFormValues>();
  return get(errors, name)?.message as string | undefined;
}

function FieldShell({ name, label, hint, className, error, children }: FieldProps & { error?: string; children: React.ReactNode }) {
  const id = `field-${name}`;
  return (
    <div className={cn("grid gap-1.5", className)}>
      <Label htmlFor={id}>{label}</Label>
      {children}
      {hint && !error && (
        <p id={`${id}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

function describedBy(name: string, error?: string, hint?: string) {
  if (error) return `field-${name}-error`;
  if (hint) return `field-${name}-hint`;
  return undefined;
}

export function TextField({ type = "text", ...props }: FieldProps & { type?: string }) {
  const { register } = useFormContext<ProfileFormValues>();
  const error = useFieldError(props.name);
  return (
    <FieldShell {...props} error={error}>
      <Input
        id={`field-${props.name}`}
        type={type}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy(props.name, error, props.hint)}
        {...register(props.name as never)}
      />
    </FieldShell>
  );
}

export function TextAreaField({ rows = 3, ...props }: FieldProps & { rows?: number }) {
  const { register } = useFormContext<ProfileFormValues>();
  const error = useFieldError(props.name);
  return (
    <FieldShell {...props} error={error}>
      <Textarea
        id={`field-${props.name}`}
        rows={rows}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy(props.name, error, props.hint)}
        {...register(props.name as never)}
      />
    </FieldShell>
  );
}

export function CheckboxField({ name, label, className }: Omit<FieldProps, "hint">) {
  const { control } = useFormContext<ProfileFormValues>();
  const id = `field-${name}`;
  return (
    <Controller
      control={control}
      name={name as never}
      render={({ field }) => (
        <div className={cn("flex items-center gap-2", className)}>
          <Checkbox
            id={id}
            checked={Boolean(field.value)}
            onCheckedChange={(checked) => field.onChange(checked === true)}
            onBlur={field.onBlur}
          />
          <Label htmlFor={id} className="font-normal">
            {label}
          </Label>
        </div>
      )}
    />
  );
}
