import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import {
  Car,
  Upload,
  Loader,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";
import { createValuation, createValuationWithImage } from "../api/valuation";

const BRANDS = [
  "BMW", "Mercedes", "Audi", "Volkswagen", "Toyota", "Honda", "Ford",
  "Renault", "Fiat", "Hyundai", "Opel", "Peugeot", "Citroen", "Nissan",
  "Kia", "Volvo", "Skoda", "Dacia",
];

const FUEL_TYPES = ["Benzin", "Dizel", "LPG", "Hibrit", "Elektrik"];
const TRANSMISSIONS = ["Manuel", "Otomatik", "Yarı Otomatik"];
const BODY_TYPES = ["Sedan", "Hatchback", "SUV", "Coupe", "Station Wagon", "MPV", "Cabrio", "Pickup"];

export default function Valuation() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  const [form, setForm] = useState({
    brand: "",
    model: "",
    year: new Date().getFullYear(),
    mileage: 0,
    fuel_type: "",
    transmission: "",
    body_type: "",
    color: "",
    engine_size: "",
    damage_records: "",
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: name === "year" || name === "mileage" ? Number(value) : value,
    }));
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(file);
      setImagePreview(URL.createObjectURL(file));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!form.brand || !form.model || !form.fuel_type || !form.transmission) {
      toast.error("Please fill in all required fields");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      let res;
      if (image) {
        const formData = new FormData();
        Object.entries(form).forEach(([key, val]) => {
          if (val !== "" && val !== null) formData.append(key, val);
        });
        formData.append("image", image);
        res = await createValuationWithImage(formData);
      } else {
        res = await createValuation(form);
      }

      setResult(res.data);
      toast.success("Valuation completed!");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Valuation failed");
    } finally {
      setLoading(false);
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

  return (
    <div className="valuation-page">
      <div className="valuation-form-container">
        <div className="form-header">
          <Car size={28} />
          <h1>New Car Valuation</h1>
          <p>Enter your car details for an AI-powered price estimate</p>
        </div>

        <form onSubmit={handleSubmit} className="valuation-form">
          <div className="form-grid">
            <div className="form-group">
              <label>Brand *</label>
              <select name="brand" value={form.brand} onChange={handleChange} required>
                <option value="">Select brand</option>
                {BRANDS.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Model *</label>
              <input
                type="text"
                name="model"
                value={form.model}
                onChange={handleChange}
                placeholder="e.g. 320i, Corolla, Focus"
                required
              />
            </div>

            <div className="form-group">
              <label>Year *</label>
              <input
                type="number"
                name="year"
                value={form.year}
                onChange={handleChange}
                min={1990}
                max={new Date().getFullYear()}
                required
              />
            </div>

            <div className="form-group">
              <label>Mileage (km) *</label>
              <input
                type="number"
                name="mileage"
                value={form.mileage}
                onChange={handleChange}
                min={0}
                required
              />
            </div>

            <div className="form-group">
              <label>Fuel Type *</label>
              <select name="fuel_type" value={form.fuel_type} onChange={handleChange} required>
                <option value="">Select fuel type</option>
                {FUEL_TYPES.map((f) => (
                  <option key={f} value={f}>{f}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Transmission *</label>
              <select name="transmission" value={form.transmission} onChange={handleChange} required>
                <option value="">Select transmission</option>
                {TRANSMISSIONS.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Body Type</label>
              <select name="body_type" value={form.body_type} onChange={handleChange}>
                <option value="">Select body type</option>
                {BODY_TYPES.map((b) => (
                  <option key={b} value={b}>{b}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Color</label>
              <input
                type="text"
                name="color"
                value={form.color}
                onChange={handleChange}
                placeholder="e.g. Beyaz, Siyah"
              />
            </div>

            <div className="form-group">
              <label>Engine Size</label>
              <input
                type="text"
                name="engine_size"
                value={form.engine_size}
                onChange={handleChange}
                placeholder="e.g. 1.6, 2.0"
              />
            </div>
          </div>

          <div className="form-group full-width">
            <label>Damage Records</label>
            <textarea
              name="damage_records"
              value={form.damage_records}
              onChange={handleChange}
              placeholder="Describe any damage history, paint jobs, accidents..."
              rows={3}
            />
          </div>

          <div className="form-group full-width">
            <label>Car Image (optional)</label>
            <div className="image-upload">
              <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                id="car-image"
              />
              <label htmlFor="car-image" className="upload-label">
                {imagePreview ? (
                  <img src={imagePreview} alt="Preview" className="image-preview" />
                ) : (
                  <>
                    <Upload size={32} />
                    <span>Click to upload a car image</span>
                    <span className="upload-hint">
                      The AI will analyze exterior condition, paint quality, and damages
                    </span>
                  </>
                )}
              </label>
            </div>
          </div>

          <button type="submit" className="btn-primary btn-large" disabled={loading}>
            {loading ? (
              <>
                <Loader size={20} className="spin" />
                Analyzing with AI...
              </>
            ) : (
              <>
                <TrendingUp size={20} />
                Get Valuation
              </>
            )}
          </button>
        </form>
      </div>

      {result && (
        <div className="result-container">
          <div className="result-card">
            <div className="result-header">
              <CheckCircle size={28} className="success-icon" />
              <h2>Valuation Result</h2>
            </div>

            <div className="result-car-info">
              <h3>
                {result.brand} {result.model} ({result.year})
              </h3>
              <p>{result.mileage?.toLocaleString()} km | {result.fuel_type} | {result.transmission}</p>
            </div>

            <div className="result-price">
              <div className="price-main">
                <span className="price-label">Estimated Value</span>
                <span className="price-amount">
                  {formatPrice(result.predicted_price)}
                </span>
              </div>
              <div className="price-range-display">
                <div className="range-item">
                  <span>Min</span>
                  <span>{formatPrice(result.price_min)}</span>
                </div>
                <div className="range-item">
                  <span>Max</span>
                  <span>{formatPrice(result.price_max)}</span>
                </div>
                <div className="range-item">
                  <span>Condition</span>
                  <span>{result.condition_score}/10</span>
                </div>
              </div>
            </div>

            {result.ai_analysis && (
              <div className="result-analysis">
                <h4>
                  <AlertTriangle size={16} />
                  AI Analysis
                </h4>
                <p>{result.ai_analysis}</p>
              </div>
            )}

            <div className="result-actions">
              <button
                onClick={() => {
                  setResult(null);
                  setForm({
                    brand: "", model: "", year: new Date().getFullYear(),
                    mileage: 0, fuel_type: "", transmission: "",
                    body_type: "", color: "", engine_size: "", damage_records: "",
                  });
                  setImage(null);
                  setImagePreview(null);
                }}
                className="btn-secondary"
              >
                New Valuation
              </button>
              <button onClick={() => navigate("/dashboard")} className="btn-primary">
                View All Valuations
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
