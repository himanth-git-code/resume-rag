import { AppHeader } from "@/components/app-header";
import { RequireAuth } from "@/components/auth/require-auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <RequireAuth>
      <AppHeader />
      <main className="mx-auto w-full max-w-4xl flex-1 p-6">{children}</main>
    </RequireAuth>
  );
}
