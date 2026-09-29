import Link from "next/link";

import { HealthStatus } from "@/components/health-status";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold tracking-tight">AI Professional Identity</h1>
      <div className="flex gap-3">
        <Button asChild>
          <Link href="/signup">Create account</Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/login">Sign in</Link>
        </Button>
      </div>
      <HealthStatus />
    </main>
  );
}
