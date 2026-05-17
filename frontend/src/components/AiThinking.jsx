import { useEffect, useState } from "react";
import { Bot, Sparkles, Search, Calculator, FileText } from "lucide-react";

const STEPS = [
  { icon: Bot, label: "Yapay zeka görselleri analiz ediyor" },
  { icon: Search, label: "Benzer ilanlar piyasa veritabanından çekiliyor" },
  { icon: Calculator, label: "İstatistiksel model fiyat aralığını hesaplıyor" },
  { icon: Sparkles, label: "Görsel duruma göre ayarlamalar yapılıyor" },
  { icon: FileText, label: "Sonuç ve açıklama hazırlanıyor" },
];

/**
 * Animated "AI is thinking" overlay shown while a valuation request is in flight.
 * Cycles through fake-but-realistic pipeline steps so the user has something
 * to watch during the ~3-8 second backend call.
 */
export default function AiThinking() {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setIdx((i) => (i + 1) % STEPS.length), 1500);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="ai-thinking-overlay" role="status" aria-live="polite">
      <div className="ai-thinking-card">
        <div className="ai-robot-wrap">
          <Bot size={56} className="ai-robot" />
          <div className="ai-pulse" />
          <div className="ai-pulse ai-pulse-delay" />
        </div>

        <h3 className="ai-thinking-title">Yapay Zeka Değerlendiriyor</h3>

        <ul className="ai-step-list">
          {STEPS.map((step, i) => {
            const Icon = step.icon;
            const active = i === idx;
            const done = i < idx;
            return (
              <li
                key={i}
                className={`ai-step ${active ? "is-active" : ""} ${done ? "is-done" : ""}`}
              >
                <Icon size={16} className="ai-step-icon" />
                <span>{step.label}</span>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
