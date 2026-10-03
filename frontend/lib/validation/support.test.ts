import { describe, expect, it } from "vitest";

import { checkFiles, formatBytes, staffQuery, ticketSchema } from "@/lib/validation/support";

const file = (name: string, bytes: number) => new File([new Uint8Array(bytes)], name);

describe("checkFiles", () => {
  it("accepts up to three small images or PDFs", () => {
    expect(checkFiles([file("a.png", 10), file("b.JPG", 10), file("c.pdf", 10)])).toBeNull();
  });
  it("rejects other types, big files and too many", () => {
    expect(checkFiles([file("a.exe", 10)])).toMatch(/PNG, JPEG or PDF/);
    expect(checkFiles([file("a.png", 5 * 1024 * 1024 + 1)])).toMatch(/5 MB/);
    expect(checkFiles([1, 2, 3, 4].map((i) => file(`${i}.png`, 1)))).toMatch(/at most 3/);
  });
});

describe("staffQuery", () => {
  it("builds the inbox filter query", () => {
    expect(staffQuery({ status: "active", unread: true, search: " sup-1 " }, 2)).toBe("?status=active&unread=1&search=sup-1&page=2");
    expect(staffQuery({})).toBe("");
  });
});

describe("formatBytes", () => {
  it("shows KB or MB", () => {
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });
});

describe("ticketSchema", () => {
  it("parses a ticket with an event and attachment", () => {
    const t = ticketSchema.parse({
      number: "SUP-000001", subject: "Help", priority: "high", status: "waiting_for_user", unread: false,
      created_at: "t", updated_at: "t", description: "d",
      messages: [
        { id: 1, kind: "candidate", author: { name: "You", staff: false }, body: "hi", created_at: "t",
          attachments: [{ id: 3, original_name: "a.png", content_type: "image/png", size: 10, url: "/api/support/attachments/3/" }] },
        { id: 2, kind: "event", author: null, body: "Status changed to Resolved.", attachments: [], created_at: "t" },
      ],
    });
    expect(t.messages[0].attachments[0].url).toContain("/attachments/");
  });
});
