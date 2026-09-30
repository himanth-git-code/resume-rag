import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiGet, apiSend } from "@/lib/api/client";
import { noteListSchema, noteSchema } from "@/lib/validation/notes";
import type { NoteInput } from "@/types/notes";

const NOTES_KEY = ["notes"] as const;

export function useNotes() {
  return useQuery({ queryKey: NOTES_KEY, queryFn: () => apiGet("/notes", noteListSchema) });
}

function useNotesMutation<TArgs>(fn: (args: TArgs) => Promise<unknown>) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOTES_KEY });
      // Notes feed the knowledge base, which re-indexes in the background.
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });
}

export const useCreateNote = () => useNotesMutation((input: NoteInput) => apiSend("POST", "/notes", noteSchema, input));

export const useUpdateNote = () =>
  useNotesMutation(({ id, ...input }: NoteInput & { id: number }) => apiSend("PUT", `/notes/${id}`, noteSchema, input));

// DELETE answers 204 with no body.
export const useDeleteNote = () => useNotesMutation((id: number) => apiSend("DELETE", `/notes/${id}`, z.null()));
