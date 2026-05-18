import { useEffect } from "react";
import { AlertTriangle, Loader, X } from "lucide-react";

/**
 * Reusable confirmation modal. Renders when `open` is true and
 * resolves either `onConfirm` or `onCancel`.
 *
 * Variant `danger` (default) shows a red icon badge for destructive
 * actions; `info` for benign confirmations.
 */
export default function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Onayla",
  cancelLabel = "Vazgeç",
  variant = "danger",
  loading = false,
  onConfirm,
  onCancel,
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => {
      if (e.key === "Escape" && !loading) onCancel?.();
      if (e.key === "Enter" && !loading) onConfirm?.();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, loading, onConfirm, onCancel]);

  if (!open) return null;

  return (
    <div className="cm-overlay" onClick={loading ? undefined : onCancel}>
      <div
        className="cm-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="cm-title"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="cm-close"
          onClick={onCancel}
          disabled={loading}
          aria-label="Kapat"
        >
          <X size={16} />
        </button>

        <div className={`cm-icon cm-icon-${variant}`}>
          <AlertTriangle size={22} />
        </div>

        <h3 id="cm-title" className="cm-title">{title}</h3>
        {message && <p className="cm-message">{message}</p>}

        <div className="cm-actions">
          <button
            className="btn-secondary"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelLabel}
          </button>
          <button
            className={`cm-confirm cm-confirm-${variant}`}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader size={16} className="spin" />
                İşleniyor...
              </>
            ) : (
              confirmLabel
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
