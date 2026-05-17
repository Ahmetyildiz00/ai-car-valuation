import { useEffect, useState } from "react";
import { toast } from "react-hot-toast";
import { Brain, Database, Users } from "lucide-react";

import {
  getAdminStats,
  getBackfillStatus,
  getModelInfo,
  getScrapeStatus,
  getTrainStatus,
  triggerBackfillEmbeddings,
  triggerScrapeTopModels,
  triggerTrainModel,
} from "../api/admin";
import JobCard from "../components/admin/JobCard";
import ProgressBar from "../components/admin/ProgressBar";
import { usePollingStatus } from "../hooks/usePollingStatus";
import { showErrorToast } from "../lib/errors";

const fmtNum = (n) => (n ?? 0).toLocaleString("tr-TR");

function StatCard({ icon: Icon, label, value }) {
  return (
    <div className="admin-card">
      <div className="admin-card-header">
        <Icon size={18} />
        <span>{label}</span>
      </div>
      <div className="admin-card-value">{value}</div>
    </div>
  );
}

export default function Admin() {
  const [stats, setStats] = useState(null);
  const [modelInfo, setModelInfo] = useState(null);

  const refreshStats = async () => {
    try {
      const res = await getAdminStats();
      setStats(res.data);
    } catch {}
  };
  const refreshModelInfo = async () => {
    try {
      const res = await getModelInfo();
      setModelInfo(res.data);
    } catch {}
  };

  useEffect(() => {
    refreshStats();
    refreshModelInfo();
  }, []);

  // Scrape job
  const scrape = usePollingStatus(getScrapeStatus);
  const [perModel, setPerModel] = useState(200);
  const [scrapeStarting, setScrapeStarting] = useState(false);
  const startScrape = async () => {
    setScrapeStarting(true);
    try {
      await triggerScrapeTopModels(perModel);
      toast.success("Scrape başlatıldı");
      scrape.refresh();
    } catch (e) { showErrorToast(e, "Scrape başlatılamadı"); }
    finally { setScrapeStarting(false); }
  };

  // Train job
  const train = usePollingStatus(getTrainStatus);
  const [trainStarting, setTrainStarting] = useState(false);
  const startTrain = async () => {
    setTrainStarting(true);
    try {
      await triggerTrainModel();
      toast.success("Model eğitimi başlatıldı");
      train.refresh();
    } catch (e) { showErrorToast(e, "Eğitim başlatılamadı"); }
    finally { setTrainStarting(false); }
  };
  useEffect(() => {
    if (train.status.state === "completed") {
      refreshModelInfo();
      refreshStats();
    }
  }, [train.status.state]);

  // Embedding backfill job
  const embed = usePollingStatus(getBackfillStatus);
  const [embedStarting, setEmbedStarting] = useState(false);
  const [embedForce, setEmbedForce] = useState(false);
  const startEmbed = async () => {
    setEmbedStarting(true);
    try {
      await triggerBackfillEmbeddings(embedForce);
      toast.success("Embedding üretimi başlatıldı");
      embed.refresh();
    } catch (e) { showErrorToast(e, "Embedding üretimi başlatılamadı"); }
    finally { setEmbedStarting(false); }
  };

  // Re-poll stats while scrape is running
  useEffect(() => {
    if (scrape.status.state === "running") {
      const id = setInterval(refreshStats, 4000);
      return () => clearInterval(id);
    }
  }, [scrape.status.state]);

  return (
    <div className="admin-page">
      <div className="dashboard-header">
        <div>
          <h1>Admin Panel</h1>
          <p>Sistem yönetimi, veri toplama ve model eğitimi.</p>
        </div>
      </div>

      <div className="admin-grid">
        <StatCard icon={Users} label="Kullanıcılar" value={fmtNum(stats?.users)} />
        <StatCard icon={Database} label="Scraped Cars" value={fmtNum(stats?.scraped_cars)} />
        <StatCard
          icon={Brain}
          label="ML Model"
          value={
            modelInfo?.loaded
              ? `MAE ${fmtNum(Math.round(modelInfo.mae))}`
              : "Yok"
          }
        />
      </div>

      <JobCard
        title="Veri Çekme"
        description="10 marka × 5 popüler model = 50 (marka, model) çifti için her birinden seçtiğiniz adette ilan çekilir. Arka planda çalışır, 200 ilan/model için ~1-2 saat sürebilir."
        status={scrape.status}
        starting={scrapeStarting}
        onStart={startScrape}
        startLabel="Scrape Başlat"
        renderControls={(running) => (
          <div className="form-group">
            <label>Model başına ilan adedi</label>
            <input
              type="number"
              min={50}
              max={1000}
              step={50}
              value={perModel}
              onChange={(e) => setPerModel(Number(e.target.value) || 500)}
              disabled={running}
            />
          </div>
        )}
        renderProgress={(s) =>
          (s.state === "running" || s.state === "completed") && (
            <>
              <ProgressBar
                current={s.scraped_total}
                total={s.total_target}
                label={s.state === "running" ? "İlerleme" : "Tamamlandı"}
              />
              {s.current && (
                <div className="admin-progress-current">
                  İşlenen: <strong>{s.current.label}</strong> ({s.current.index}/{s.current.total})
                </div>
              )}
              {s.state === "completed" && s.per_model_results && (
                <div className="admin-progress-results">
                  <h4>Sonuçlar</h4>
                  <ul>
                    {Object.entries(s.per_model_results).map(([label, n]) => (
                      <li key={label}>{label}: <strong>{n}</strong></li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )
        }
      />

      <JobCard
        title="ML Model Eğitimi"
        description="Mevcut scraped_cars üzerinde HistGradientBoosting fiyat tahmin modeli eğitir. Log-target + outlier filter ile."
        status={train.status}
        starting={trainStarting}
        onStart={startTrain}
        startLabel="Eğitimi Başlat"
        renderProgress={() =>
          modelInfo?.loaded && (
            <div className="admin-progress-results">
              <h4>Mevcut Model</h4>
              <ul>
                <li>Kaynak: <strong>{modelInfo.source}</strong></li>
                <li>Örnek sayısı: <strong>{fmtNum(modelInfo.n_samples)}</strong></li>
                <li>MAE: <strong>{fmtNum(Math.round(modelInfo.mae))} TL</strong></li>
                <li>R²: <strong>{modelInfo.r2?.toFixed(3)}</strong></li>
                <li>Eğitim zamanı: <strong>{modelInfo.trained_at}</strong></li>
              </ul>
            </div>
          )
        }
      />

      <JobCard
        title="Embedding Üretimi"
        description="scraped_cars için semantik benzerlik vektörleri hesaplar. Tahmin kalitesini düşük örneklemli sorgularda artırır."
        status={embed.status}
        starting={embedStarting}
        onStart={startEmbed}
        startLabel="Embedding Üret"
        renderControls={(running) => (
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={embedForce}
              onChange={(e) => setEmbedForce(e.target.checked)}
              disabled={running}
            />
            <span>Tüm satırları zorla yeniden hesapla</span>
          </label>
        )}
        renderProgress={(s) =>
          (s.state === "running" || s.state === "completed") && (
            <ProgressBar
              current={s.processed}
              total={s.total}
              label={s.state === "running" ? "İlerleme" : "Tamamlandı"}
            />
          )
        }
      />
    </div>
  );
}
