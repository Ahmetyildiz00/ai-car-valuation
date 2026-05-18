import { useEffect, useState } from "react";
import { Bot, Sparkles } from "lucide-react";

const STAGES = [
  "Görseller analiz ediliyor",
  "Marka, model ve durum tespit ediliyor",
  "Piyasadaki benzer ilanlar taranıyor",
  "Fiyat aralığı hesaplanıyor",
  "Sonuç hazırlanıyor",
];

/**
 * Inline overlay shown while a valuation request is in flight.
 * Renders a glassy gradient backdrop over its positioned parent
 * (the form container), with an animated mascot card in the centre.
 */
export default function AiThinking() {
  const [stageIdx, setStageIdx] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setStageIdx((i) => Math.min(i + 1, STAGES.length - 1));
    }, 1400);
    return () => clearInterval(id);
  }, []);

  const progressPct = ((stageIdx + 1) / STAGES.length) * 100;

  return (
    <div className="ai-thinking" role="status" aria-live="polite">
      <div className="ai-thinking-card">
        <div className="ai-robot-stage">
          <span className="ai-ring ai-ring-1" />
          <span className="ai-ring ai-ring-2" />
          <span className="ai-ring ai-ring-3" />
          <span className="ai-robot-bubble">
            <Bot size={42} strokeWidth={1.6} />
            <Sparkles size={16} className="ai-spark ai-spark-1" />
            <Sparkles size={12} className="ai-spark ai-spark-2" />
          </span>
        </div>

        <div className="ai-thinking-headline">
          <span className="ai-badge">AI</span>
          <h3>Yapay zeka çalışıyor</h3>
        </div>

        <p className="ai-thinking-stage" key={stageIdx}>
          {STAGES[stageIdx]}
          <span className="ai-dots"><span /><span /><span /></span>
        </p>

        <div className="ai-progress-track">
          <div className="ai-progress-fill" style={{ width: `${progressPct}%` }} />
        </div>

        <p className="ai-thinking-hint">
          Bu işlem genellikle 5–10 saniye sürer. Lütfen sekmeyi kapatmayın.
        </p>
      </div>
    </div>
  );
}
