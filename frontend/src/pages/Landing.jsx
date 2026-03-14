import { useState, useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Upload, Link2, ArrowRight, Shield, Zap, TrendingUp, Info, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import carvalIcon from "../assets/carval-icon.png";

const FUEL_TYPES = ["Benzin", "Dizel", "LPG", "Hibrit", "Elektrik"];
const TRANSMISSIONS = ["Manuel", "Otomatik", "Yarı Otomatik"];

export default function Landing() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [imageUrl, setImageUrl] = useState("");
  const [previewFiles, setPreviewFiles] = useState([]);
  const [form, setForm] = useState({
    year: new Date().getFullYear(),
    mileage: "",
    fuel_type: "",
    transmission: "",
    damage_records: "",
  });

  const handleFiles = (files) => {
    const valid = Array.from(files)
      .filter((f) => f.type.startsWith("image/"))
      .slice(0, 5);
    const previews = valid.map((f) => ({ file: f, url: URL.createObjectURL(f) }));
    setPreviewFiles((prev) => [...prev, ...previews].slice(0, 5));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  const removePreview = (idx) => {
    setPreviewFiles((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: name === "year" || name === "mileage" ? Number(value) : value,
    }));
  };

  const handleEvaluate = () => {
    navigate("/valuation", {
      state: { files: previewFiles.map((p) => p.file), imageUrl, form },
    });
  };

  const hasInput = previewFiles.length > 0 || imageUrl.trim();

  return (
    <div className="landing-page">
      {/* Header */}
      <header className="landing-header">
        <div className="landing-header-inner">
          <Link to="/" className="landing-brand">
            <img src={carvalIcon} alt="Carval.ai" className="brand-icon" />
            <span>Carval<span className="brand-ai">.ai</span></span>
          </Link>
          <div className="landing-header-actions">
            {user ? (
              <Link to="/dashboard" className="btn-outline-sm">Dashboard</Link>
            ) : (
              <>
                <Link to="/login" className="btn-ghost-sm">Giriş Yap</Link>
                <Link to="/register" className="btn-solid-sm">Üye Ol</Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="hero-section">
        <div className="hero-left">
          <h1 className="hero-title">
            Aracınızın Gerçek<br />
            <span className="hero-highlight">Piyasa Değerini</span><br />
            Saniyeler İçinde Öğrenin
          </h1>
          <p className="hero-desc">
            Carval.ai, yapay zeka ile araç fotoğraflarını analiz ederek marka,
            model, hasar durumu ve daha fazlasını otomatik tespit eder.
            Siz sadece fotoğraf yükleyin, gerisini bize bırakın.
          </p>
          <div className="hero-stats">
            <div className="hero-stat">
              <span className="hero-stat-num">/10sn</span>
              <span className="hero-stat-label">Ortalama analiz süresi</span>
            </div>
            <div className="hero-stat">
              <span className="hero-stat-num">/%94</span>
              <span className="hero-stat-label">Fiyat tahmin doğruluğu</span>
            </div>
          </div>
        </div>

        <div className="hero-right">
          <div className="upload-card">
            <div className="upload-card-header">
              <span className="upload-beta-badge">BETA</span>
              <Info size={16} className="upload-info-icon" title="Daha iyi sonuçlar için net, iyi aydınlatılmış fotoğraflar kullanın." />
            </div>
            <h2 className="upload-card-title">Araç fotoğrafı ile değer tahmin et</h2>

            {/* Drop Zone */}
            <div
              className={`drop-zone ${dragOver ? "drag-over" : ""}`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => previewFiles.length === 0 && fileInputRef.current?.click()}
            >
              <input
                type="file"
                ref={fileInputRef}
                accept="image/*"
                multiple
                onChange={(e) => handleFiles(e.target.files)}
                style={{ display: "none" }}
              />
              {previewFiles.length === 0 ? (
                <div className="drop-zone-empty">
                  <div className="upload-icon-wrap">
                    <Upload size={28} />
                  </div>
                  <p className="drop-zone-text">
                    Fotoğrafları buraya sürükleyin veya{" "}
                    <span className="drop-zone-link">seçin</span>
                  </p>
                  <p className="drop-zone-hint">En fazla 5 görsel · Ekran görüntüsü kaliteyi düşürebilir</p>
                </div>
              ) : (
                <div className="preview-grid">
                  {previewFiles.map((p, i) => (
                    <div key={i} className="preview-item">
                      <img src={p.url} alt={`Görsel ${i + 1}`} />
                      <button
                        className="preview-remove"
                        onClick={(e) => { e.stopPropagation(); removePreview(i); }}
                      >
                        <X size={12} />
                      </button>
                    </div>
                  ))}
                  {previewFiles.length < 5 && (
                    <div
                      className="preview-add"
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
            <div className="url-divider"><span>VEYA</span></div>
            <div className="url-input-wrap">
              <Link2 size={16} className="url-icon" />
              <input
                type="url"
                placeholder="Görsel URL'si yapıştırın"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                className="url-input"
              />
            </div>

            {/* Car info fields */}
            <div className="landing-form-grid">
              <div className="landing-form-group">
                <label>Yıl</label>
                <input
                  type="number"
                  name="year"
                  value={form.year}
                  onChange={handleChange}
                  min={1990}
                  max={new Date().getFullYear()}
                />
              </div>
              <div className="landing-form-group">
                <label>Kilometre</label>
                <input
                  type="number"
                  name="mileage"
                  value={form.mileage}
                  onChange={handleChange}
                  placeholder="örn. 85000"
                  min={0}
                />
              </div>
              <div className="landing-form-group">
                <label>Yakıt</label>
                <select name="fuel_type" value={form.fuel_type} onChange={handleChange}>
                  <option value="">Seçin</option>
                  {FUEL_TYPES.map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
              </div>
              <div className="landing-form-group">
                <label>Vites</label>
                <select name="transmission" value={form.transmission} onChange={handleChange}>
                  <option value="">Seçin</option>
                  {TRANSMISSIONS.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>

            <div className="landing-form-group" style={{ marginTop: "0.4rem" }}>
              <label>Hasar / Değişen &amp; Boyalı Parçalar</label>
              <textarea
                name="damage_records"
                value={form.damage_records}
                onChange={handleChange}
                placeholder="örn. Ön tampon boyalı, sol ön kapı değişen..."
                rows={2}
              />
            </div>

            <button
              className={`btn-evaluate ${!hasInput ? "btn-evaluate-disabled" : ""}`}
              onClick={handleEvaluate}
              disabled={!hasInput}
            >
              Değeri Tahmin Et
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features-section">
        <div className="features-inner">
          <div className="feature-card">
            <div className="feature-icon-wrap feature-icon-blue"><Zap size={22} /></div>
            <h3>Anında Analiz</h3>
            <p>Yapay zeka görselden marka, model, renk ve hasar durumunu otomatik tespit eder.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon-wrap feature-icon-green"><TrendingUp size={22} /></div>
            <h3>Piyasa Verisi</h3>
            <p>Gerçek zamanlı ikinci el araç piyasası verileriyle desteklenen fiyat tahmini.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon-wrap feature-icon-purple"><Shield size={22} /></div>
            <h3>Güvenilir Sonuç</h3>
            <p>Min/maks fiyat aralığı ve durum skoru ile şeffaf ve güvenilir değerleme raporu.</p>
          </div>
        </div>
      </section>

      {/* Tips */}
      <section className="tips-section">
        <div className="tips-inner">
          <h2 className="tips-title">Daha iyi sonuçlar için ipuçları</h2>
          <div className="tips-grid">
            <div className="tip-item">
              <span className="tip-num">1</span>
              <p>Aracı iyi aydınlatılmış bir ortamda, önden ve yandan fotoğraflayın.</p>
            </div>
            <div className="tip-item">
              <span className="tip-num">2</span>
              <p>Varsa hasar, çizik veya boya bozulmalarını gösteren yakın çekim ekleyin.</p>
            </div>
            <div className="tip-item">
              <span className="tip-num">3</span>
              <p>Plaka görünmesinde sakınca yok; AI sadece görsel özelliklere odaklanır.</p>
            </div>
            <div className="tip-item">
              <span className="tip-num">4</span>
              <p>Birden fazla açıdan fotoğraf yüklemek tahmin doğruluğunu artırır.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="landing-footer-inner">
          <div className="landing-brand" style={{ pointerEvents: "none" }}>
            <img src={carvalIcon} alt="Carval.ai" className="brand-icon" />
            <span>Carval<span className="brand-ai">.ai</span></span>
          </div>
          <p className="footer-copy">© 2026 Carval.ai · Tüm hakları saklıdır.</p>
        </div>
      </footer>
    </div>
  );
}
