export default function ProgressBar({ current, total, label }) {
  const pct = total > 0 ? Math.min(100, Math.round((current / total) * 100)) : 0;
  return (
    <div className="admin-progress">
      <div className="admin-progress-header">
        <span>
          {label}: <strong>{current ?? 0} / {total ?? 0}</strong>
        </span>
        <span className="admin-progress-pct">{pct}%</span>
      </div>
      <div className="admin-progress-bar">
        <div className="admin-progress-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
