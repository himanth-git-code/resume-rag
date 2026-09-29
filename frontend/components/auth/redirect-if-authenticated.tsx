"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useSession } from "@/lib/api/auth";

/** Sends already signed-in users from the login/signup pages to the dashboard. */
export function RedirectIfAuthenticated({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated) router.replace("/dashboard");
  }, [isAuthenticated, router]);

  return children;
}
