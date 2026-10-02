import type { z } from "zod";

import type { checkoutSchema, paymentSchema, productSchema } from "@/lib/validation/payments";

export type Product = z.infer<typeof productSchema>;
export type Payment = z.infer<typeof paymentSchema>;
export type CheckoutSession = z.infer<typeof checkoutSchema>;
