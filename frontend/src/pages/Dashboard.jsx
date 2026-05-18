import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "react-hot-toast";
import {
  PlusCircle,
  Trash2,
  TrendingUp,
  Calendar,
  Gauge,
  Fuel,
} from "lucide-react";
import { getValuations, deleteValuation } from "../api/valuation";
import ConfirmModal from "../components/ConfirmModal";

export default function Dashboard() {
  const [valuations, setValuations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pendingDeleteId, setPendingDeleteId] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const fetchValuations = async () => {
    try {
      const res = await getValuations();
      setValuations(res.data.valuations);
    } catch {
      toast.error("Değerlemeler yüklenemedi");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchValuations();
  }, []);

  const pendingDelete = valuations.find((v) => v.id === pendingDeleteId);

  const confirmDelete = async () => {
    if (!pendingDeleteId) return;
    setDeleting(true);
    try {
      await deleteValuation(pendingDeleteId);
      setValuations((prev) => prev.filter((v) => v.id !== pendingDeleteId));
      toast.success("Değerleme silindi");
      setPendingDeleteId(null);
    } catch {
      toast.error("Silinemedi");
    } finally {
      setDeleting(false);
    }
  };

  const formatPrice = (price) => {
    if (!price) return "—";
    return new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency: "TRY",
      maximumFractionDigits: 0,
    }).format(price);
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner" />
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <div>
          <h1>Değerlemelerim</h1>
          <p>{valuations.length} değerleme</p>
        </div>
        <Link to="/valuation" className="btn-primary">
          <PlusCircle size={18} />
          Yeni Değerleme
        </Link>
      </div>

      {valuations.length === 0 ? (
        <div className="empty-state">
          <TrendingUp size={64} />
          <h2>Henüz değerleme yok</h2>
          <p>İlk araç değerlemenizi oluşturmak için başlayın.</p>
          <Link to="/valuation" className="btn-primary">
            Başla
          </Link>
        </div>
      ) : (
        <div className="valuation-grid">
          {valuations.map((v) => (
            <div key={v.id} className="valuation-card">
              <div className="valuation-card-header">
                <h3>
                  {v.brand} {v.model}
                </h3>
                <button
                  onClick={() => setPendingDeleteId(v.id)}
                  className="btn-icon-danger"
                  title="Sil"
                >
                  <Trash2 size={16} />
                </button>
              </div>

              <div className="valuation-card-details">
                <div className="detail-item">
                  <Calendar size={14} />
                  <span>{v.year}</span>
                </div>
                <div className="detail-item">
                  <Gauge size={14} />
                  <span>{v.mileage?.toLocaleString("tr-TR")} km</span>
                </div>
                <div className="detail-item">
                  <Fuel size={14} />
                  <span>{v.fuel_type}</span>
                </div>
              </div>

              {v.predicted_price ? (
                <div className="valuation-card-price">
                  <span className="price-label">Tahmini Değer</span>
                  <span className="price-value">{formatPrice(v.predicted_price)}</span>
                  <span className="price-range">
                    {formatPrice(v.price_min)} — {formatPrice(v.price_max)}
                  </span>
                </div>
              ) : (
                <div className="valuation-card-price">
                  <span className="price-label">Tahmin mevcut değil</span>
                </div>
              )}

              {v.condition_score && (
                <div className="condition-bar">
                  <span>Durum</span>
                  <div className="bar-track">
                    <div
                      className="bar-fill"
                      style={{ width: `${v.condition_score * 10}%` }}
                    />
                  </div>
                  <span>{v.condition_score}/10</span>
                </div>
              )}

              <div className="valuation-card-date">
                {new Date(v.created_at).toLocaleDateString("tr-TR")}
              </div>
            </div>
          ))}
        </div>
      )}

      <ConfirmModal
        open={Boolean(pendingDeleteId)}
        title="Değerlemeyi sil"
        message={
          pendingDelete
            ? `${pendingDelete.brand} ${pendingDelete.model} (${pendingDelete.year}) değerlemesi kalıcı olarak silinecek. Bu işlem geri alınamaz.`
            : ""
        }
        confirmLabel="Sil"
        cancelLabel="Vazgeç"
        loading={deleting}
        onConfirm={confirmDelete}
        onCancel={() => !deleting && setPendingDeleteId(null)}
      />
    </div>
  );
}
