"use client";

import { useEffect } from "react";

/**
 * Deterrence for the private preview (SPEC §12): discourages casual saving and
 * printing and marks every screen as a preview. This is not DRM; content shown
 * in a browser can always be captured.
 */
export function PreviewGuard({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    const block = (e: Event) => e.preventDefault();
    const keys = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      if ((e.ctrlKey || e.metaKey) && ["s", "p", "u"].includes(key)) e.preventDefault();
    };
    document.addEventListener("contextmenu", block);
    document.addEventListener("dragstart", block);
    document.addEventListener("keydown", keys);
    return () => {
      document.removeEventListener("contextmenu", block);
      document.removeEventListener("dragstart", block);
      document.removeEventListener("keydown", keys);
    };
  }, []);

  return (
    <div className="relative select-none">
      <style>{"@media print { body { display: none !important; } }"}</style>
      {children}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center overflow-hidden"
      >
        <span className="rotate-[-30deg] text-[18vw] font-black tracking-widest whitespace-nowrap text-black/[0.06] dark:text-white/[0.06]">
          PREVIEW
        </span>
      </div>
      <div className="fixed inset-x-0 top-0 z-50 bg-black/80 px-4 py-2 text-center text-xs text-white">
        Private preview · not published · this link expires shortly
      </div>
    </div>
  );
}
