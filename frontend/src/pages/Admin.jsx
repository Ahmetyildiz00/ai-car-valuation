import { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import { Database, Loader, Play, Users } from "lucide-react";
import {
  getAdminStats,
  getScrapeStatus,
  triggerScrapeTopModels,
} from "../api/admin";

const POLL_MS = 4000;

export default function Admin() {
  const [stats, setStats] = useState(null);
  const [status, setStatus] = useState({ state: "idle" });
  const [perModel, setPerModel] = useState(500);
  const [starting, setStarting] = useState(false);

  const refreshStats = async () => {
    try {
      const res = await getAdminStats();
      setStats(res.data);
    } catch {}
  };

  const refreshStatus = async () => {
    try {
      const res = await getScrapeStatus();
      setStatus(res.data);
    } catch {}
  };

  useEffect(() => {
    refreshStats();
    refreshStatus();
  }, []);

  useEffect(() => {
    if (status.state !== "running") return;
    const id = setInterval(() => {
      refreshStatus();
      refreshStats();
    }, POLL_MS);
    return () => clearInterval(id);
  }, [status.state]);

  const handleStart = async () => {
    setStarting(true);
    try {
      await triggerScrapeTopModels(perModel);
      toast.success("Scrape başlatıldı (arka planda çalışıyor)");
      await refreshStatus();
    } catch (err) {
      const detail = err.response?.data?.detail;
      const msg = typeof detail === "string" ? detail : detail?.message;
      toast.error(msg || "Scrape başlatılamadı");
    } finally {
      setStarting(false);
    }
  };

  const isRunning = status.state === "running";
  const progressPct =
    isRunning && status.total_target
      ? Math.min(100, Math.round((status.scraped_total / status.total_target) * 100))
      : 0;

  return (
    <div className="admin-page">
      <div className="dashboard-header">
        <div>
          <h1>Admin Panel</h1>
          <p>Sistem yönetimi ve veri toplama araçları.</p>
        </div>
      </div>

      <div className="admin-grid">
        <div className="admin-card">
          <div className="admin-card-header">
            <Users size={18} />
            <span>Kullanıcılar</span>
          </div>
          <div className="admin-card-value">{stats?.users ?? "—"}</div>
        </div>

        <div className="admin-card">
          <div className="admin-card-header">
            <Database size={18} />
            <span>Scraped Cars</span>
          </div>
          <div className="admin-card-value">{stats?.scraped_cars ?? "—"}</div>
        </div>
      </div>

      <div className="admin-section">
        <div className="admin-section-header">
          <h2>Veri Çekme</h2>
          <p>
            En çok tercih edilen 10 marka/model çiftinden, her biri için seçtiğiniz adette
            ilan çekilir. Arka planda çalışır, ~30-60 dk sürebilir.
          </p>
        </div>

        <div className="admin-controls">
          <div className="form-group">
            <label>Model başına ilan adedi</label>
            <input
              type="number"
              min={50}
              max={1000}
              step={50}
              value={perModel}
              onChange={(e) => setPerModel(Number(e.target.value) || 500)}
              disabled={isRunning}
            />
          </div>
          <button
            className="btn-primary"
            onClick={handleStart}
            disabled={starting || isRunning}
          >
            {starting ? (
              <>
                <Loader size={16} className="spin" />
                Başlatılıyor...
              </>
            ) : isRunning ? (
              <>
                <Loader size={16} className="spin" />
                Çalışıyor
              </>
            ) : (
              <>
                <Play size={16} />
                Scrape Başlat
              </>
            )}
          </button>
        </div>

        {(isRunning || status.state === "completed") && (
          <div className="admin-progress">
            <div className="admin-progress-header">
              <span>
                {isRunning ? "İlerleme" : "Tamamlandı"}:{" "}
                <strong>
                  {status.scraped_total ?? 0} / {status.total_target ?? 0}
                </strong>
              </span>
              <span className="admin-progress-pct">{progressPct}%</span>
            </div>
            <div className="admin-progress-bar">
              <div
                className="admin-progress-fill"
                style={{ width: `${progressPct}%` }}
              />
            </div>
            {status.current && (
              <div className="admin-progress-current">
                İşlenen: <strong>{status.current.label}</strong>{" "}
                ({status.current.index}/{status.current.total})
              </div>
            )}
            {status.state === "completed" && status.per_model_results && (
              <div className="admin-progress-results">
                <h4>Sonuçlar</h4>
                <ul>
                  {Object.entries(status.per_model_results).map(([label, n]) => (
                    <li key={label}>
                      {label}: <strong>{n}</strong>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
