import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";

import { apiGet, apiSend } from "@/lib/api/client";
import {
  adminPaymentPageSchema,
  adminQuery,
  adminTemplateSchema,
  adminUserDetailSchema,
  adminUserPageSchema,
  aiJobsSchema,
  auditPageSchema,
  overviewSchema,
  templateVersionPageSchema,
  type UserAction,
} from "@/lib/validation/admin";

type Params = Record<string, string | number | boolean | undefined>;

export const useAdminOverview = () =>
  useQuery({ queryKey: ["admin", "overview"], queryFn: () => apiGet("/admin/overview", overviewSchema) });

export const useAdminUsers = (params: Params) =>
  useQuery({
    queryKey: ["admin", "users", params],
    queryFn: () => apiGet(`/admin/users${adminQuery(params)}`, adminUserPageSchema),
    placeholderData: keepPreviousData,
  });

export const useAdminUser = (id: number) =>
  useQuery({ queryKey: ["admin", "user", id], queryFn: () => apiGet(`/admin/users/${id}`, adminUserDetailSchema) });

export function useAdminUserAction(id: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { action: UserAction; reason: string }) =>
      apiSend("POST", `/admin/users/${id}/actions`, adminUserDetailSchema, input),
    onSuccess: (data) => {
      queryClient.setQueryData(["admin", "user", id], data);
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
  });
}

export const useAdminPayments = (params: Params) =>
  useQuery({
    queryKey: ["admin", "payments", params],
    queryFn: () => apiGet(`/admin/payments${adminQuery(params)}`, adminPaymentPageSchema),
    placeholderData: keepPreviousData,
  });

export const useAdminAudit = (params: Params) =>
  useQuery({
    queryKey: ["admin", "audit", params],
    queryFn: () => apiGet(`/admin/audit${adminQuery(params)}`, auditPageSchema),
    placeholderData: keepPreviousData,
  });

export const useAiJobs = () =>
  useQuery({ queryKey: ["admin", "ai-jobs"], queryFn: () => apiGet("/admin/ai-jobs", aiJobsSchema), refetchInterval: 60_000 });

export const useAdminTemplates = () =>
  useQuery({ queryKey: ["admin", "templates"], queryFn: () => apiGet("/admin/templates", z.array(adminTemplateSchema)) });

export const useTemplateVersions = () =>
  useQuery({ queryKey: ["admin", "template-versions"], queryFn: () => apiGet("/admin/templates/versions", templateVersionPageSchema) });

export function useUpdateTemplate() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { key: string } & Partial<{ enabled: boolean; premium: boolean; name: string; description: string; default_sections: string[] }>) =>
      apiSend("PATCH", "/admin/templates", z.array(adminTemplateSchema), input),
    onSuccess: (data) => {
      queryClient.setQueryData(["admin", "templates"], data);
      queryClient.invalidateQueries({ queryKey: ["admin", "template-versions"] });
    },
  });
}

export function useRestoreTemplates() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (number: number) => apiSend("POST", `/admin/templates/versions/${number}/restore`, z.array(adminTemplateSchema)),
    onSuccess: (data) => {
      queryClient.setQueryData(["admin", "templates"], data);
      queryClient.invalidateQueries({ queryKey: ["admin", "template-versions"] });
    },
  });
}
