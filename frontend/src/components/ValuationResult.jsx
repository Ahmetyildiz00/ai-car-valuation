import { Sparkles, RotateCcw, ArrowRight, Calendar, Gauge, Fuel, Settings2 } from "lucide-react";

function Spec({ icon: Icon, label, value }) {
  return (
    <div className="vr-spec">
      <Icon size={15} className="vr-spec-icon" />
      <span className="vr-spec-label">{label}</span>
      <span className="vr-spec-value">{value}</span>
    </div>
  );
}

/**
 * Hero-style valuation result.
 * Replaces the form on the page entirely while shown.
 */
export default function ValuationResult({
  result,
  formatPrice,
  onReset,
  onPrimary,
  primaryLabel,
}) {
  return (
    <div className="vr">
      <div className="vr-hero">
        <div className="vr-hero-label">Tahmini Piyasa Değeri</div>
        <div className="vr-hero-price">{formatPrice(result.predicted_price)}</div>
        <div className="vr-hero-range">
          {formatPrice(result.price_min)}
          <span className="vr-hero-range-sep">—</span>
          {formatPrice(result.price_max)}
        </div>
      </div>

      <div className="vr-vehicle">
        <h2 className="vr-vehicle-title">
          {result.brand} {result.model}
          <span className="vr-vehicle-year">({result.year})</span>
        </h2>
        <div className="vr-spec-row">
          <Spec icon={Gauge} label="Kilometre" value={`${result.mileage?.toLocaleString("tr-TR")} km`} />
          <Spec icon={Fuel} label="Yakıt" value={result.fuel_type} />
          <Spec icon={Settings2} label="Vites" value={result.transmission} />
          {result.condition_score != null && (
            <Spec icon={Calendar} label="Durum" value={`${result.condition_score}/10`} />
          )}
        </div>
      </div>

      {result.ai_analysis && (
        <div className="vr-analysis">
          <div className="vr-analysis-header">
            <Sparkles size={16} />
            <span>Yapay Zeka Analizi</span>
          </div>
          <p>{result.ai_analysis}</p>
        </div>
      )}

      <div className="vr-actions">
        <button onClick={onReset} className="btn-secondary">
          <RotateCcw size={16} />
          Yeni Değerleme
        </button>
        <button onClick={onPrimary} className="btn-primary">
          {primaryLabel}
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
