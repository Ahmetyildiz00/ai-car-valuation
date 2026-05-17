import { useState, useRef, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import {
  Upload,
  Loader,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  X,
  Link2,
  Info,
  Bot,
} from "lucide-react";
import { createValuationWithImage, getValuationQuota } from "../api/valuation";
import { upgradeSubscription } from "../api/subscription";
import { useAuth } from "../context/AuthContext";
import AiThinking from "../components/AiThinking";
import { showErrorToast } from "../lib/errors";

const FUEL_TYPES = ["Benzin", "Dizel", "LPG", "Hibrit", "Elektrik"];
const TRANSMISSIONS = ["Manuel", "Otomatik", "Yarı Otomatik"];

export default function Valuation() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, subscription, refreshSubscription } = useAuth();
  const fileInputRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [images, setImages] = useState([]);
  const [imagePreviews, setImagePreviews] = useState([]);
  const [imageUrl, setImageUrl] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [paywall, setPaywall] = useState(false);
  const [upgrading, setUpgrading] = useState(false);
  const [anonRemaining, setAnonRemaining] = useState(null);

  const [form, setForm] = useState({
    year: new Date().getFullYear(),
    mileage: "",
    fuel_type: "",
    transmission: "",
    engine_size: "",
    damage_records: "",
  });

  // Pre-fill from landing page navigation state
  useEffect(() => {
    if (location.state?.files?.length > 0) {
      const files = location.state.files.slice(0, 5);
      setImages(files);
      setImagePreviews(files.map((f) => URL.createObjectURL(f)));
    }
    if (location.state?.imageUrl) {
      setImageUrl(location.state.imageUrl);
    }
    if (location.state?.form) {
      setForm((prev) => ({ ...prev, ...location.state.form }));
    }
  }, []);

  const refreshAnonQuota = async () => {
    try {
      const res = await getValuationQuota();
      if (!res.data.authenticated) {
        setAnonRemaining(res.data.remaining);
      } else {
        setAnonRemaining(null);
      }
    } catch {}
  };

  useEffect(() => {
    if (!user) {
      refreshAnonQuota();
    } else {
      setAnonRemaining(null);
    }
  }, [user]);

  const handleUpgrade = async () => {
    setUpgrading(true);
    try {
      await upgradeSubscription(30);
      await refreshSubscription();
      setPaywall(false);
      toast.success("Pro aboneliği aktifleştirildi!");
    } catch {
      toast.error("Abonelik yükseltme başarısız oldu");
    } finally {
      setUpgrading(false);
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: name === "year" || name === "mileage" ? Number(value) : value,
    }));
  };

  const addFiles = (files) => {
    const remaining = 5 - images.length;
    if (remaining <= 0) return;
    const valid = Array.from(files)
      .filter((f) => f.type.startsWith("image/"))
      .slice(0, remaining);
    setImages((prev) => [...prev, ...valid]);
    setImagePreviews((prev) => [
      ...prev,
      ...valid.map((f) => URL.createObjectURL(f)),
    ]);
  };

  const removeImage = (idx) => {
    setImages((prev) => prev.filter((_, i) => i !== idx));
    setImagePreviews((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    addFiles(e.dataTransfer.files);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (user && subscription && !subscription.unlimited && subscription.remaining === 0) {
      setPaywall(true);
      return;
    }
    if (!user && anonRemaining === 0) {
      setPaywall(true);
      return;
    }

    if (images.length === 0 && !imageUrl.trim()) {
      toast.error("Lütfen en az bir araç görseli yükleyin veya URL girin");
      return;
    }

    if (!form.fuel_type || !form.transmission) {
      toast.error("Lütfen yakıt tipi ve vites seçin");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const formData = new FormData();
      Object.entries(form).forEach(([key, val]) => {
        if (val !== "" && val !== null && val !== 0) formData.append(key, val);
      });

      if (images.length > 0) {
        images.forEach((img) => formData.append("images", img));
      }
      if (imageUrl.trim()) {
        formData.append("image_url", imageUrl.trim());
      }

      const res = await createValuationWithImage(formData);
      setResult(res.data);
      toast.success("Değerleme tamamlandı!");
      if (user) {
        refreshSubscription();
      } else {
        refreshAnonQuota();
      }
    } catch (err) {
      if (err.response?.status === 402) {
        setPaywall(true);
        if (user) refreshSubscription();
        else refreshAnonQuota();
      } else {
        showErrorToast(err, "Değerleme başarısız oldu");
      }
    } finally {
      setLoading(false);
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

  const resetForm = () => {
    setResult(null);
    setForm({
      year: new Date().getFullYear(),
      mileage: "",
      fuel_type: "",
      transmission: "",
      engine_size: "",
      damage_records: "",
    });
    setImages([]);
    setImagePreviews([]);
    setImageUrl("");
  };

  return (
    <div className="valuation-page">
      <div className="valuation-form-container">
        <div className="form-header">
          <h1>Araç Değerleme</h1>
          <p>
            Fotoğraf yükleyin, yapay zeka marka ve model gibi bilgileri otomatik
            algılar. Siz sadece km ve yakıt tipi gibi ek bilgileri girin.
          </p>
          {!user && anonRemaining !== null && anonRemaining > 0 && (
            <div className="quota-banner">
              <Info size={14} />
              <span>
                Kalan ücretsiz deneme hakkı: <strong>{anonRemaining}</strong>. Aylık 10 değerleme için{" "}
                <button type="button" className="link-btn" onClick={() => navigate("/register")}>
                  üye olun
                </button>
                .
              </span>
            </div>
          )}
          {user && subscription && !subscription.unlimited && (
            <div className="quota-banner">
              <Info size={14} />
              <span>
                Bu ay kalan değerleme hakkı:{" "}
                <strong>
                  {subscription.remaining} / {subscription.monthly_limit}
                </strong>
                . Sınırsız kullanım için{" "}
                <button type="button" className="link-btn" onClick={() => setPaywall(true)}>
                  Pro'ya geçin
                </button>
                .
              </span>
            </div>
          )}
          {user && subscription?.unlimited && (
            <div className="quota-banner quota-banner-pro">
              <TrendingUp size={14} />
              <span>
                <strong>Pro</strong> abonelik aktif — sınırsız değerleme.
              </span>
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="valuation-form">
          {/* Image upload — required */}
          <div className="form-section">
            <div className="form-section-label">
              Araç Görseli <span className="required-star">*</span>
              <span className="section-hint">
                (en fazla 5 görsel · <Info size={13} className="inline-icon" /> Net ve iyi aydınlatılmış fotoğraflar daha iyi sonuç verir)
              </span>
            </div>

            <div
              className={`drop-zone-form ${dragOver ? "drag-over" : ""} ${images.length > 0 ? "has-images" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => images.length === 0 && fileInputRef.current?.click()}
            >
              <input
                type="file"
                ref={fileInputRef}
                accept="image/*"
                multiple
                onChange={(e) => addFiles(e.target.files)}
                style={{ display: "none" }}
              />

              {images.length === 0 ? (
                <div className="drop-zone-empty">
                  <Upload size={28} />
                  <p>
                    Görselleri sürükleyin veya{" "}
                    <span className="drop-zone-link" onClick={() => fileInputRef.current?.click()}>
                      seçin
                    </span>
                  </p>
                  <span className="drop-zone-hint">Ekran görüntüsü kaliteyi düşürebilir</span>
                </div>
              ) : (
                <div className="preview-grid-form">
                  {imagePreviews.map((src, i) => (
                    <div key={i} className="preview-item-form">
                      <img src={src} alt={`Görsel ${i + 1}`} />
                      <button
                        type="button"
                        className="preview-remove-form"
                        onClick={(e) => { e.stopPropagation(); removeImage(i); }}
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                  {images.length < 5 && (
                    <div
                      className="preview-add-form"
                      onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                    >
                      <Upload size={18} />
                      <span>Ekle</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* URL input */}
            <div className="url-or-divider"><span>VEYA URL</span></div>
            <div className="url-input-wrap-form">
              <Link2 size={15} className="url-icon" />
              <input
                type="url"
                placeholder="Görsel bağlantısı yapıştırın"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                className="url-input-form"
              />
            </div>
          </div>

          {/* Car details */}
          <div className="form-section">
            <div className="form-section-label">Araç Bilgileri</div>
            <div className="form-grid">
              <div className="form-group">
                <label>Yıl <span className="required-star">*</span></label>
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
                <label>Kilometre (km) <span className="required-star">*</span></label>
                <input
                  type="number"
                  name="mileage"
                  value={form.mileage}
                  onChange={handleChange}
                  placeholder="örn. 85000"
                  min={0}
                  required
                />
              </div>

              <div className="form-group">
                <label>Yakıt Tipi <span className="required-star">*</span></label>
                <select name="fuel_type" value={form.fuel_type} onChange={handleChange} required>
                  <option value="">Seçin</option>
                  {FUEL_TYPES.map((f) => (
                    <option key={f} value={f}>{f}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Vites <span className="required-star">*</span></label>
                <select name="transmission" value={form.transmission} onChange={handleChange} required>
                  <option value="">Seçin</option>
                  {TRANSMISSIONS.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Motor Hacmi (L)</label>
                <input
                  type="text"
                  name="engine_size"
                  value={form.engine_size}
                  onChange={handleChange}
                  placeholder="örn. 1.6 (litre)"
                />
              </div>

            </div>

            <div className="form-group" style={{ marginTop: "0.75rem" }}>
              <label>Hasar / Değişen &amp; Boyalı Parçalar</label>
              <textarea
                name="damage_records"
                value={form.damage_records}
                onChange={handleChange}
                placeholder="örn. Ön tampon boyalı, sol ön kapı değişen, tavan hasarlı..."
                rows={2}
              />
            </div>
          </div>

          {/* Info box */}
          <div className="info-box">
            <Info size={16} />
            <p>
              Marka, model, renk ve kasa tipi görsellerden yapay zeka tarafından otomatik tespit edilir. Kilometre, yakıt tipi, vites ve motor hacmi gibi bilgiler görselden okunamayacağı için sizden istenmektedir.
            </p>
          </div>

          <button type="submit" className="btn-primary btn-large" disabled={loading}>
            {loading ? (
              <>
                <Loader size={20} className="spin" />
                Yapay Zeka Analiz Ediyor...
              </>
            ) : (
              <>
                <Bot size={20} />
                Değerlemeyi Başlat
              </>
            )}
          </button>
        </form>
      </div>

      {loading && <AiThinking />}

      {paywall && (
        <div className="paywall-overlay" onClick={() => setPaywall(false)}>
          <div className="paywall-modal" onClick={(e) => e.stopPropagation()}>
            <button className="paywall-close" onClick={() => setPaywall(false)} aria-label="Kapat">
              <X size={18} />
            </button>
            <div className="paywall-icon">
              <TrendingUp size={28} />
            </div>
            {!user ? (
              <>
                <h3>Ücretsiz deneme hakkınız doldu</h3>
                <p>
                  3 ücretsiz değerlemenizi kullandınız. Ücretsiz üyelikle{" "}
                  <strong>ayda 10 değerleme</strong>, Pro ile <strong>sınırsız değerleme</strong>{" "}
                  hakkı kazanırsınız.
                </p>
                <div className="paywall-actions">
                  <button className="btn-secondary" onClick={() => navigate("/login")}>
                    Giriş Yap
                  </button>
                  <button className="btn-primary" onClick={() => navigate("/register")}>
                    Üye Ol
                  </button>
                </div>
              </>
            ) : (
              <>
                <h3>Pro aboneliğe geçin</h3>
                <p>
                  {subscription?.remaining === 0
                    ? `Bu ayki ${subscription.monthly_limit} değerleme hakkınız doldu. `
                    : `Ücretsiz planda ayda ${subscription?.monthly_limit ?? 10} değerleme hakkınız var. `}
                  Pro aboneliği ile <strong>sınırsız değerleme</strong> yapabilirsiniz.
                </p>
                <div className="paywall-actions">
                  <button className="btn-secondary" onClick={() => setPaywall(false)} disabled={upgrading}>
                    Vazgeç
                  </button>
                  <button className="btn-primary" onClick={handleUpgrade} disabled={upgrading}>
                    {upgrading ? (
                      <>
                        <Loader size={16} className="spin" />
                        Yükseltiliyor...
                      </>
                    ) : (
                      "Pro'ya Geç"
                    )}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {result && (
        <div className="result-container">
          <div className="result-card">
            <div className="result-header">
              <CheckCircle size={28} className="success-icon" />
              <h2>Değerleme Sonucu</h2>
            </div>

            <div className="result-car-info">
              <h3>
                {result.brand} {result.model} ({result.year})
              </h3>
              <p>
                {result.mileage?.toLocaleString("tr-TR")} km &middot; {result.fuel_type} &middot; {result.transmission}
              </p>
            </div>

            <div className="result-price">
              <div className="price-main">
                <span className="price-label">Tahmini Piyasa Değeri</span>
                <span className="price-amount">{formatPrice(result.predicted_price)}</span>
              </div>
              <div className="price-range-display">
                <div className="range-item">
                  <span>Minimum</span>
                  <span>{formatPrice(result.price_min)}</span>
                </div>
                <div className="range-item">
                  <span>Maksimum</span>
                  <span>{formatPrice(result.price_max)}</span>
                </div>
                <div className="range-item">
                  <span>Durum Skoru</span>
                  <span>{result.condition_score}/10</span>
                </div>
              </div>
            </div>

            {result.ai_analysis && (
              <div className="result-analysis">
                <h4>
                  <AlertTriangle size={16} />
                  AI Analizi
                </h4>
                <p>{result.ai_analysis}</p>
              </div>
            )}

            <div className="result-actions">
              <button onClick={resetForm} className="btn-secondary">
                Yeni Değerleme
              </button>
              {user ? (
                <button onClick={() => navigate("/dashboard")} className="btn-primary">
                  Tüm Değerlemeleri Gör
                </button>
              ) : (
                <button onClick={() => navigate("/register")} className="btn-primary">
                  Kaydet &amp; Üye Ol
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
