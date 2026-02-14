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

export default function Dashboard() {
  const [valuations, setValuations] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchValuations = async () => {
    try {
      const res = await getValuations();
      setValuations(res.data.valuations);
    } catch {
      toast.error("Failed to load valuations");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchValuations();
  }, []);

  const handleDelete = async (id) => {
    if (!confirm("Delete this valuation?")) return;
    try {
      await deleteValuation(id);
      setValuations((prev) => prev.filter((v) => v.id !== id));
      toast.success("Valuation deleted");
    } catch {
      toast.error("Failed to delete");
    }
  };

  const formatPrice = (price) => {
    if (!price) return "N/A";
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
          <h1>Your Valuations</h1>
          <p>{valuations.length} total valuation{valuations.length !== 1 ? "s" : ""}</p>
        </div>
        <Link to="/valuation" className="btn-primary">
          <PlusCircle size={18} />
          New Valuation
        </Link>
      </div>

      {valuations.length === 0 ? (
        <div className="empty-state">
          <TrendingUp size={64} />
          <h2>No valuations yet</h2>
          <p>Create your first car valuation to get started.</p>
          <Link to="/valuation" className="btn-primary">
            Get Started
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
                  onClick={() => handleDelete(v.id)}
                  className="btn-icon-danger"
                  title="Delete"
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
                  <span>{v.mileage?.toLocaleString()} km</span>
                </div>
                <div className="detail-item">
                  <Fuel size={14} />
                  <span>{v.fuel_type}</span>
                </div>
              </div>

              {v.predicted_price ? (
                <div className="valuation-card-price">
                  <span className="price-label">Estimated Value</span>
                  <span className="price-value">
                    {formatPrice(v.predicted_price)}
                  </span>
                  <span className="price-range">
                    {formatPrice(v.price_min)} — {formatPrice(v.price_max)}
                  </span>
                </div>
              ) : (
                <div className="valuation-card-price">
                  <span className="price-label">Prediction unavailable</span>
                </div>
              )}

              {v.condition_score && (
                <div className="condition-bar">
                  <span>Condition</span>
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
    </div>
  );
}
