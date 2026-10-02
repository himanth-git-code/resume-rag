import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiSend } from "@/lib/api/client";
import { websiteSchema } from "@/lib/validation/website";

export function usePublishWebsite(action: "publish" | "unpublish") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => apiSend("POST", `/website/${action}`, websiteSchema),
    onSuccess: (data) => queryClient.setQueryData(["website"], data),
  });
}
