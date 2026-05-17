import { toast } from "react-hot-toast";

/**
 * Pull a user-facing message from an axios error response.
 * Handles FastAPI's typical shapes:
 *   - { detail: "string" }
 *   - { detail: { message, code, ... } }
 *   - { detail: [ { msg, loc, type }, ... ] }       (validation errors)
 */
export function extractErrorMessage(err, fallback = "Bir hata oluştu") {
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;

  if (typeof detail === "string") return detail;

  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    if (detail.message) return detail.message;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    const first = detail[0];
    if (first?.msg) {
      const field = Array.isArray(first.loc) ? first.loc[first.loc.length - 1] : null;
      return field ? `${field}: ${first.msg}` : first.msg;
    }
  }

  if (status === 401) return "Oturumunuz sonlandı, lütfen tekrar giriş yapın.";
  if (status === 403) return "Bu işlem için yetkiniz yok.";
  if (status === 404) return "Aradığınız kayıt bulunamadı.";
  if (status === 429) return "Çok fazla istek attınız, lütfen birazdan tekrar deneyin.";
  if (status >= 500) return "Sunucu şu an cevap veremiyor, birazdan tekrar deneyin.";
  if (err?.code === "ERR_NETWORK") return "Sunucuya bağlanılamıyor. İnternet bağlantınızı kontrol edin.";

  return err?.message || fallback;
}

/**
 * Show an error toast with a sensible message extracted from `err`.
 * Returns the message so callers can also use it inline.
 */
export function showErrorToast(err, fallback) {
  const msg = extractErrorMessage(err, fallback);
  toast.error(msg);
  return msg;
}
