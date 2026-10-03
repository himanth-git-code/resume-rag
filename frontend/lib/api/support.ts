import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiGet, apiSend } from "@/lib/api/client";
import { staffListSchema, staffQuery, ticketPageSchema, ticketSchema, type StaffFilters } from "@/lib/validation/support";

function form(fields: Record<string, string | boolean | undefined | null>, files: File[]): FormData {
  const data = new FormData();
  for (const [k, v] of Object.entries(fields)) if (v !== undefined && v !== null && v !== "") data.append(k, String(v));
  for (const f of files) data.append("files", f);
  return data;
}

function useRefreshBadges() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: ["me"] });
}

// ----- candidate -------------------------------------------------------------

export function useMyTickets(page = 1) {
  return useQuery({
    queryKey: ["support", "mine", page],
    queryFn: () => apiGet(`/support/tickets${page > 1 ? `?page=${page}` : ""}`, ticketPageSchema),
  });
}

export function useMyTicket(number: string) {
  const refresh = useRefreshBadges();
  return useQuery({
    queryKey: ["support", "ticket", number],
    queryFn: async () => {
      const ticket = await apiGet(`/support/tickets/${encodeURIComponent(number)}`, ticketSchema);
      refresh(); // opening a ticket marks it read
      return ticket;
    },
    refetchInterval: 30_000,
  });
}

export function useOpenTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { subject: string; description: string; priority: string; files: File[] }) =>
      apiSend(
        "POST",
        "/support/tickets",
        ticketSchema,
        form({ subject: input.subject, description: input.description, priority: input.priority }, input.files),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["support", "mine"] }),
  });
}

export function useReply(number: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { body: string; files: File[] }) =>
      apiSend("POST", `/support/tickets/${encodeURIComponent(number)}/messages`, ticketSchema, form({ body: input.body }, input.files)),
    onSuccess: (ticket) => queryClient.setQueryData(["support", "ticket", number], ticket),
  });
}

export function useCloseTicket(number: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiSend("POST", `/support/tickets/${encodeURIComponent(number)}/close`, ticketSchema),
    onSuccess: (ticket) => queryClient.setQueryData(["support", "ticket", number], ticket),
  });
}

// ----- staff -----------------------------------------------------------------

export function useStaffInbox(filters: StaffFilters, page: number) {
  return useQuery({
    queryKey: ["support", "staff", "inbox", filters, page],
    queryFn: () => apiGet(`/admin/support/tickets${staffQuery(filters, page)}`, ticketPageSchema),
    placeholderData: keepPreviousData,
    refetchInterval: 60_000,
  });
}

export function useStaffTicket(number: string) {
  const refresh = useRefreshBadges();
  return useQuery({
    queryKey: ["support", "staff", "ticket", number],
    queryFn: async () => {
      const ticket = await apiGet(`/admin/support/tickets/${encodeURIComponent(number)}`, ticketSchema);
      refresh();
      return ticket;
    },
    refetchInterval: 30_000,
  });
}

export function useStaffUsers() {
  return useQuery({ queryKey: ["support", "staff", "users"], queryFn: () => apiGet("/admin/support/staff", staffListSchema), staleTime: 300_000 });
}

export function useStaffReply(number: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { body: string; internal: boolean; status?: string; files: File[] }) =>
      apiSend(
        "POST",
        `/admin/support/tickets/${encodeURIComponent(number)}/messages`,
        ticketSchema,
        form({ body: input.body, internal: input.internal, status: input.status }, input.files),
      ),
    onSuccess: (ticket) => queryClient.setQueryData(["support", "staff", "ticket", number], ticket),
  });
}

export function useStaffUpdate(number: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (changes: { status?: string; priority?: string; assigned_to?: number | null }) =>
      apiSend("PATCH", `/admin/support/tickets/${encodeURIComponent(number)}`, ticketSchema, changes),
    onSuccess: (ticket) => {
      queryClient.setQueryData(["support", "staff", "ticket", number], ticket);
      queryClient.invalidateQueries({ queryKey: ["support", "staff", "inbox"] });
    },
  });
}
