import { Suspense } from "react";

import { RedirectIfAuthenticated } from "@/components/auth/redirect-if-authenticated";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex flex-1 items-center justify-center p-6">
      {/* The forms read ?next= and ?error= via useSearchParams. */}
      <Suspense>
        <RedirectIfAuthenticated>{children}</RedirectIfAuthenticated>
      </Suspense>
    </main>
  );
}
