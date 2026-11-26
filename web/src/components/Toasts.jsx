import { CheckCircle2, AlertTriangle } from "lucide-react";
import { useApp } from "../context/AppContext";

export default function Toasts() {
  const { toasts } = useApp();
  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[min(92vw,380px)] flex-col gap-2" aria-live="polite">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`animate-rise flex items-start gap-3 rounded-xl px-4 py-3 text-sm shadow-lg ring-1 ${
            toast.tone === "error" ? "bg-rose-50 text-rose-900 ring-rose-200" : "bg-ink text-white ring-ink"
          }`}
        >
          {toast.tone === "error" ? (
            <AlertTriangle size={18} className="mt-0.5 shrink-0" />
          ) : (
            <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-mint" />
          )}
          <span>{toast.message}</span>
        </div>
      ))}
    </div>
  );
}
