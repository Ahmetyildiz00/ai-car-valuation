import { Bot } from "lucide-react";

/**
 * Inline overlay shown while a valuation request is in flight.
 * Stays inside its positioned parent (e.g. the form container) so it
 * blocks just that area instead of the whole viewport.
 */
export default function AiThinking({ message = "Yapay zeka aracınızı değerlendiriyor" }) {
  return (
    <div className="ai-thinking" role="status" aria-live="polite">
      <div className="ai-thinking-inner">
        <div className="ai-robot-stage">
          <span className="ai-ring ai-ring-1" />
          <span className="ai-ring ai-ring-2" />
          <span className="ai-robot-bubble">
            <Bot size={32} />
          </span>
        </div>
        <p className="ai-thinking-text">
          {message}
          <span className="ai-dots">
            <span /><span /><span />
          </span>
        </p>
      </div>
    </div>
  );
}
