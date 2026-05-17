import { Toaster, ToastBar, toast } from "react-hot-toast";
import { CheckCircle2, AlertCircle, X, Loader } from "lucide-react";

/**
 * App-wide toast configuration.
 * Card-style toasts with a soft icon badge on the left and a close (X) button.
 */
function ToastIcon({ type }) {
  if (type === "success") {
    return (
      <div className="toast-icon toast-icon-success">
        <CheckCircle2 size={20} />
      </div>
    );
  }
  if (type === "error") {
    return (
      <div className="toast-icon toast-icon-error">
        <AlertCircle size={20} />
      </div>
    );
  }
  if (type === "loading") {
    return (
      <div className="toast-icon toast-icon-loading">
        <Loader size={20} className="spin" />
      </div>
    );
  }
  return null;
}

export default function AppToaster() {
  return (
    <Toaster
      position="top-right"
      gutter={10}
      toastOptions={{
        duration: 4000,
        style: {
          padding: 0,
          background: "transparent",
          boxShadow: "none",
          maxWidth: 380,
        },
        success: { duration: 3500 },
        error: { duration: 5500 },
      }}
    >
      {(t) => (
        <ToastBar toast={t} style={{ padding: 0, background: "transparent", boxShadow: "none" }}>
          {() => (
            <div className={`toast-card toast-${t.type}`}>
              <ToastIcon type={t.type} />
              <div className="toast-message">
                {typeof t.message === "function" ? t.message(t) : t.message}
              </div>
              {t.type !== "loading" && (
                <button
                  className="toast-close"
                  onClick={() => toast.dismiss(t.id)}
                  aria-label="Kapat"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          )}
        </ToastBar>
      )}
    </Toaster>
  );
}
