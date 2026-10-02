import type { CheckoutSession } from "@/types/payments";

const SCRIPT_SRC = "https://checkout.razorpay.com/v1/checkout.js";

type RazorpayInstance = { open: () => void };
type RazorpayConstructor = new (options: Record<string, unknown>) => RazorpayInstance;

declare global {
  interface Window {
    Razorpay?: RazorpayConstructor;
  }
}

function loadScript(): Promise<RazorpayConstructor> {
  if (window.Razorpay) return Promise.resolve(window.Razorpay);
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.onload = () => (window.Razorpay ? resolve(window.Razorpay) : reject(new Error("Razorpay unavailable")));
    script.onerror = () => reject(new Error("Couldn't load Razorpay checkout"));
    document.head.appendChild(script);
  });
}

/**
 * Open Razorpay Checkout for an order. `onDone` fires when the buyer finishes or
 * closes the window; the backend (webhook/reconciliation) decides the outcome.
 */
export async function openRazorpayCheckout(session: CheckoutSession, onDone: (dismissed: boolean) => void) {
  const Razorpay = await loadScript();
  const { checkout } = session;
  const instance = new Razorpay({
    key: checkout.key,
    order_id: checkout.order_id,
    amount: checkout.amount,
    currency: checkout.currency,
    name: checkout.name,
    description: "One-time purchase",
    prefill: checkout.prefill,
    // The handler's payment id/signature are deliberately not trusted for access.
    handler: () => onDone(false),
    modal: { ondismiss: () => onDone(true) },
  });
  instance.open();
}
