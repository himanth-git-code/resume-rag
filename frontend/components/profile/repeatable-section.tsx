"use client";

import { ArrowDown, ArrowUp, Plus, Trash2 } from "lucide-react";
import { type FieldArray, useFieldArray, useFormContext } from "react-hook-form";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { ProfileFormValues, ProfileSection } from "@/types/profile";

type Props<N extends ProfileSection> = {
  name: N;
  title: string;
  description?: string;
  itemLabel: string;
  emptyItem: FieldArray<ProfileFormValues, N>;
  /** Short heading for an item, e.g. its company name. */
  summarize: (item: ProfileFormValues[N][number]) => string;
  renderItem: (index: number) => React.ReactNode;
};

export function RepeatableSection<N extends ProfileSection>({
  name,
  title,
  description,
  itemLabel,
  emptyItem,
  summarize,
  renderItem,
}: Props<N>) {
  const { control, watch } = useFormContext<ProfileFormValues>();
  // Items have their own database `id`, so keep RHF's generated React key under a different name.
  const { fields, append, remove, move } = useFieldArray({ control, name, keyName: "key" });
  const values = watch(name) as ProfileFormValues[N];

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        {description && <CardDescription>{description}</CardDescription>}
      </CardHeader>
      <CardContent className="grid gap-4">
        {fields.length === 0 && <p className="text-sm text-muted-foreground">Nothing added yet.</p>}

        {fields.map((field, index) => {
          const item = values?.[index] as ProfileFormValues[N][number] | undefined;
          const heading = (item && summarize(item)) || `${itemLabel} ${index + 1}`;
          return (
            <fieldset key={field.key} className="grid gap-4 rounded-lg border p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <legend className="flex items-center gap-2 text-sm font-medium">
                  {heading}
                  {item?.source_type === "resume" && (
                    <Badge variant="outline" className="font-normal">
                      from resume
                    </Badge>
                  )}
                </legend>
                <div className="flex gap-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={`Move ${heading} up`}
                    disabled={index === 0}
                    onClick={() => move(index, index - 1)}
                  >
                    <ArrowUp />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={`Move ${heading} down`}
                    disabled={index === fields.length - 1}
                    onClick={() => move(index, index + 1)}
                  >
                    <ArrowDown />
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={`Remove ${heading}`}
                    onClick={() => remove(index)}
                  >
                    <Trash2 />
                  </Button>
                </div>
              </div>
              {renderItem(index)}
            </fieldset>
          );
        })}

        <div>
          <Button type="button" variant="outline" size="sm" onClick={() => append(emptyItem)}>
            <Plus /> Add {itemLabel.toLowerCase()}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
