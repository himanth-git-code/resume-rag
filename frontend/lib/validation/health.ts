import { z } from "zod";

const componentStatus = z.enum(["ok", "error"]);

export const healthSchema = z.object({
  status: componentStatus,
  database: componentStatus,
  redis: componentStatus,
});
