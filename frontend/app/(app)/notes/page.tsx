"use client";

import { useState } from "react";

import { NoteEditor } from "@/components/notes/note-editor";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useCreateNote, useDeleteNote, useNotes, useUpdateNote } from "@/lib/api/notes";
import type { Note } from "@/types/notes";

function NoteCard({ note }: { note: Note }) {
  const [editing, setEditing] = useState(false);
  const update = useUpdateNote();
  const remove = useDeleteNote();

  return (
    <Card>
      <CardHeader>
        <CardTitle>{editing ? "Edit note" : note.title}</CardTitle>
        {!editing && (
          <CardDescription>Updated {new Date(note.updated_at).toLocaleDateString()}</CardDescription>
        )}
      </CardHeader>
      <CardContent className="grid gap-4">
        {editing ? (
          <NoteEditor
            initial={{ title: note.title, body: note.body }}
            submitLabel="Save note"
            pending={update.isPending}
            onSubmit={async (input) => {
              await update.mutateAsync({ id: note.id, ...input });
              setEditing(false);
            }}
            onCancel={() => setEditing(false)}
          />
        ) : (
          <>
            <p className="whitespace-pre-wrap text-sm">{note.body}</p>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                Edit
              </Button>
              <Button
                size="sm"
                variant="ghost"
                disabled={remove.isPending}
                onClick={() => {
                  if (window.confirm(`Delete "${note.title}"?`)) remove.mutate(note.id);
                }}
              >
                {remove.isPending ? "Deleting…" : "Delete"}
              </Button>
            </div>
            {remove.isError && <p className="text-sm text-destructive">The note couldn&apos;t be deleted.</p>}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export default function NotesPage() {
  const { data: notes, isPending, isError } = useNotes();
  const create = useCreateNote();
  const [adding, setAdding] = useState(false);

  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Notes</h1>
          <p className="max-w-2xl text-sm text-muted-foreground">
            Add context that isn&apos;t on your resume, such as details of a project, how you led a team, or why you
            changed roles. Notes feed your interview questions and, later, answers to employers.
          </p>
        </div>
        {!adding && <Button onClick={() => setAdding(true)}>Add note</Button>}
      </div>

      {adding && (
        <Card>
          <CardHeader>
            <CardTitle>New note</CardTitle>
          </CardHeader>
          <CardContent>
            <NoteEditor
              submitLabel="Add note"
              pending={create.isPending}
              onSubmit={async (input) => {
                await create.mutateAsync(input);
                setAdding(false);
              }}
              onCancel={() => setAdding(false)}
            />
          </CardContent>
        </Card>
      )}

      {isPending && <p className="text-sm text-muted-foreground">Loading your notes…</p>}
      {isError && (
        <p role="alert" className="text-sm text-destructive">
          Couldn&apos;t load your notes. Please refresh the page.
        </p>
      )}
      {notes?.length === 0 && !adding && <p className="text-sm text-muted-foreground">You haven&apos;t added any notes yet.</p>}
      {notes?.map((note) => <NoteCard key={note.id} note={note} />)}
    </div>
  );
}
