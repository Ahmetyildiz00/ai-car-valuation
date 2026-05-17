import { Loader, Play } from "lucide-react";

/**
 * Generic admin "long-running job" card.
 * Renders a section header, a trigger button, and a progress bar
 * that polls while `status.state === "running"`.
 */
export default function JobCard({
  title,
  description,
  status,
  starting,
  onStart,
  renderControls,
  renderProgress,
  startLabel = "Başlat",
  runningLabel = "Çalışıyor",
}) {
  const isRunning = status?.state === "running";

  return (
    <div className="admin-section">
      <div className="admin-section-header">
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>

      <div className="admin-controls">
        {renderControls && renderControls(isRunning)}
        <button
          className="btn-primary"
          onClick={onStart}
          disabled={starting || isRunning}
        >
          {starting ? (
            <>
              <Loader size={16} className="spin" />
              Başlatılıyor...
            </>
          ) : isRunning ? (
            <>
              <Loader size={16} className="spin" />
              {runningLabel}
            </>
          ) : (
            <>
              <Play size={16} />
              {startLabel}
            </>
          )}
        </button>
      </div>

      {renderProgress && renderProgress(status)}
    </div>
  );
}
