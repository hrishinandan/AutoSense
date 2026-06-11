import { useEffect, useState, useMemo } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "./Analysis.css";

/* ─── Semicircular Health Gauge (SVG) ─── */
function HealthGauge({ score }) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const cx = 120, cy = 120, r = 95;
  const startAngle = Math.PI;
  const endAngle   = 0;
  const sweepAngle = Math.PI;
  const fraction   = clampedScore / 100;

  const pt = (angle) => ({
    x: cx + r * Math.cos(angle),
    y: cy - r * Math.sin(angle),
  });

  const bgStart = pt(startAngle);
  const bgEnd   = pt(endAngle);
  const bgPath  = `M ${bgStart.x} ${bgStart.y} A ${r} ${r} 0 1 1 ${bgEnd.x} ${bgEnd.y}`;

  const segments = useMemo(() => {
    const segs = [];
    const steps = 60;
    for (let i = 0; i < steps; i++) {
      const t1 = i / steps;
      const t2 = (i + 1) / steps;
      if (t2 > fraction) break;
      const a1 = startAngle - sweepAngle * t1;
      const a2 = startAngle - sweepAngle * t2;
      const p1 = pt(a1);
      const p2 = pt(a2);
      let color;
      const mid = (t1 + t2) / 2;
      if (mid < 0.35) {
        const f = mid / 0.35;
        color = `rgb(255,${Math.round(80 * f)},0)`;
      } else if (mid < 0.55) {
        const f = (mid - 0.35) / 0.2;
        color = `rgb(255,${Math.round(80 + 175 * f)},0)`;
      } else {
        const f = (mid - 0.55) / 0.45;
        color = `rgb(${Math.round(255 * (1 - f))},${Math.round(200 + 55 * f)},${Math.round(30 * f)})`;
      }
      segs.push(<line key={i} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke={color} strokeWidth="14" strokeLinecap="round" />);
    }
    return segs;
  }, [fraction]);

  const ticks = useMemo(() => {
    const tickElements = [];
    for (let i = 0; i <= 10; i++) {
      const t     = i / 10;
      const angle = startAngle - sweepAngle * t;
      const isMajor = i % 5 === 0;
      const innerR  = isMajor ? r - 24 : r - 18;
      const outerR  = r - 12;
      const p1 = { x: cx + innerR * Math.cos(angle), y: cy - innerR * Math.sin(angle) };
      const p2 = { x: cx + outerR * Math.cos(angle), y: cy - outerR * Math.sin(angle) };
      tickElements.push(<line key={`tick-${i}`} x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} className={isMajor ? "gauge-tick-major" : "gauge-tick"} />);
    }
    return tickElements;
  }, []);

  const needleAngle = startAngle - sweepAngle * fraction;
  const needleTip   = { x: cx + (r - 18) * Math.cos(needleAngle), y: cy - (r - 18) * Math.sin(needleAngle) };
  const needleBase1 = { x: cx + 5 * Math.cos(needleAngle + Math.PI / 2), y: cy - 5 * Math.sin(needleAngle + Math.PI / 2) };
  const needleBase2 = { x: cx + 5 * Math.cos(needleAngle - Math.PI / 2), y: cy - 5 * Math.sin(needleAngle - Math.PI / 2) };

  return (
    <div className="gauge-container">
      <svg className="gauge-svg" viewBox="0 0 240 140">
        <path d={bgPath} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="14" strokeLinecap="round" />
        {segments}
        <path d={bgPath} fill="none" stroke="rgba(0,200,100,0.03)" strokeWidth="24" strokeLinecap="round" />
        {ticks}
        <polygon points={`${needleTip.x},${needleTip.y} ${needleBase1.x},${needleBase1.y} ${needleBase2.x},${needleBase2.y}`} fill="rgba(255,255,255,0.85)" filter="drop-shadow(0 0 4px rgba(255,255,255,0.5))" />
        <circle cx={cx} cy={cy} r="6" fill="#0a1628" stroke="rgba(0,200,255,0.5)" strokeWidth="2" />
      </svg>
      <span className="gauge-score-value">{Math.round(clampedScore)}</span>
    </div>
  );
}

function BrainIcon() {
  return (
    <div className="brain-icon-wrapper">
      <div className="brain-ring"></div>
      <div className="brain-ring brain-ring-outer"></div>
      <svg className="brain-svg" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 2C9.5 2 7.5 3.5 7 5.5C5.5 5.8 4 7.2 4 9c0 1.5.8 2.8 2 3.5v.5c0 2 1 3.5 2.5 4.5L10 22h4l1.5-4.5C17 16.5 18 15 18 13v-.5c1.2-.7 2-2 2-3.5 0-1.8-1.5-3.2-3-3.5C16.5 3.5 14.5 2 12 2z" />
        <path d="M12 2v20" strokeDasharray="2 2" />
        <path d="M8 8c1.5 0 2.5 1 3 2" /><path d="M16 8c-1.5 0-2.5 1-3 2" />
        <path d="M7 12c1.5.5 3 .5 5 0" /><path d="M17 12c-1.5.5-3 .5-5 0" />
        <path d="M9 16c1 .5 2 .5 3 0" /><path d="M15 16c-1 .5-2 .5-3 0" />
      </svg>
    </div>
  );
}

function StatusIcon({ status }) {
  if (status === "Good")    return <span className="info-icon" style={{ color: "#2dff6e" }}>✅</span>;
  if (status === "Warning") return <span className="info-icon" style={{ color: "#ffc107" }}>⚠️</span>;
  return <span className="info-icon" style={{ color: "#ff4444" }}>🔴</span>;
}

function StatusBar({ distribution, percentages }) {
  return (
    <div className="fr-status-bar-wrapper">
      <div className="fr-status-bar">
        {percentages.Good > 0 && <div className="fr-bar-segment fr-bar-good" style={{ width: `${percentages.Good}%` }} title={`Good: ${percentages.Good}%`} />}
        {percentages.Warning > 0 && <div className="fr-bar-segment fr-bar-warning" style={{ width: `${percentages.Warning}%` }} title={`Warning: ${percentages.Warning}%`} />}
        {percentages.Critical > 0 && <div className="fr-bar-segment fr-bar-critical" style={{ width: `${percentages.Critical}%` }} title={`Critical: ${percentages.Critical}%`} />}
      </div>
      <div className="fr-status-labels">
        <span className="fr-label-good">✅ Good — {distribution.Good} rows ({percentages.Good}%)</span>
        <span className="fr-label-warning">⚠️ Warning — {distribution.Warning} rows ({percentages.Warning}%)</span>
        <span className="fr-label-critical">🔴 Critical — {distribution.Critical} rows ({percentages.Critical}%)</span>
      </div>
    </div>
  );
}

function AnomalyCountList({ anomalyCounts }) {
  const entries = Object.entries(anomalyCounts);
  if (entries.length === 0) return <p className="fr-empty">No anomalies detected.</p>;
  const maxCount = Math.max(...entries.map(([, v]) => v));
  return (
    <div className="fr-anomaly-list">
      {entries.map(([label, count]) => (
        <div key={label} className="fr-anomaly-row">
          <span className="fr-anomaly-label">{label}</span>
          <div className="fr-anomaly-bar-track">
            <div className="fr-anomaly-bar-fill" style={{ width: `${(count / maxCount) * 100}%` }} />
          </div>
          <span className="fr-anomaly-count">{count}</span>
        </div>
      ))}
    </div>
  );
}

function WorstRowsTable({ worstRows }) {
  if (!worstRows || worstRows.length === 0) return <p className="fr-empty">No data available.</p>;
  return (
    <div className="fr-table-wrapper">
      <table className="fr-table">
        <thead>
          <tr><th>Row</th><th>Health Score</th><th>Status</th><th>Failure Prob.</th><th>ML Score</th><th>Anomalies</th></tr>
        </thead>
        <tbody>
          {worstRows.map((row) => {
            const sc = row.status === "Good" ? "good" : row.status === "Warning" ? "warning" : "danger";
            return (
              <tr key={row.row_number}>
                <td>#{row.row_number}</td>
                <td className={sc}>{row.health_score}</td>
                <td className={sc}><StatusIcon status={row.status} /> {row.status}</td>
                <td>{row.failure_probability}%</td>
                <td>{row.ml_anomaly_score}</td>
                <td className="fr-anomaly-cell">
                  {row.anomalies.length > 0
                    ? row.anomalies.map((a, i) => <span key={i} className="fr-anomaly-tag">⚡ {a}</span>)
                    : <span className="fr-empty">None</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function StatCard({ label, value, sub, highlight }) {
  return (
    <div className={`fr-stat-card ${highlight || ""}`}>
      <div className="fr-stat-value">{value}</div>
      <div className="fr-stat-label">{label}</div>
      {sub && <div className="fr-stat-sub">{sub}</div>}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   MAIN ANALYSIS COMPONENT
═══════════════════════════════════════════════════════════════ */
export default function Analysis() {
  const [data, setData]                       = useState(null);
  const [fullReport, setFullReport]           = useState(null);
  const [reportLoading, setReportLoading]     = useState(false);
  const [reportError, setReportError]         = useState(null);
  const [reportGenerated, setReportGenerated] = useState(false);

  const navigate = useNavigate();

  // ── Real-time polling ─────────────────────────────────────────
  useEffect(() => {
    const fetchData = () => {
      axios.get("http://localhost:5000/analyze")
        .then(res => setData(res.data))
        .catch(err => console.error(err));
    };
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  // ── Full report fetch ─────────────────────────────────────────
  const handleGenerateReport = () => {
    if (reportGenerated) return;
    setReportLoading(true);
    setReportError(null);
    axios.get("http://localhost:5000/full-report")
      .then((res) => {
        setFullReport(res.data);
        setReportGenerated(true);
        setReportLoading(false);
      })
      .catch((err) => {
        console.error("[FullReport] Error:", err);
        setReportError("Failed to generate report. Make sure the backend is running.");
        setReportLoading(false);
      });
  };

  if (!data) {
    return (
      <div className="analysis-loading">
        <div className="loading-spinner"></div>
        LOADING...
      </div>
    );
  }

  const analysis    = data.analysis;
  const statusClass = analysis.status === "Good" ? "good" : analysis.status === "Warning" ? "warning" : "danger";

  return (
    <div className="analysis-page">
      <h1 className="analysis-title">Real Time Analysis Report</h1>

      {/* ══════════════════════════════════════════════════
          SECTION 1: REAL-TIME ANALYSIS CARD (unchanged)
      ══════════════════════════════════════════════════ */}
      <div className="analysis-card">
        <div className="gauge-section">
          <HealthGauge score={analysis.health_score} />
          <span className="gauge-label">Health Score</span>
          <span className={`gauge-badge ${statusClass}`}>{analysis.status.toUpperCase()}</span>
          <div className="gauge-legend">
            <span className="legend-item legend-good">Good</span>
            <span className="legend-item legend-warning">Warning</span>
            <span className="legend-item legend-danger">Danger</span>
          </div>
        </div>

        <div className="info-section">
          <div className="info-top-row">
            <div className="info-block">
              <div className="info-label">Status</div>
              <div className={`info-value ${statusClass}`}><StatusIcon status={analysis.status} />{analysis.status}</div>
            </div>
            <div className="info-block">
              <div className="info-label">Failure Probability</div>
              <div className={`info-value ${analysis.failure_probability > 50 ? "danger" : analysis.failure_probability > 20 ? "warning" : "good"}`}>
                <span className="info-icon">⚠️</span>{analysis.failure_probability}%
              </div>
            </div>
          </div>
          <div className="info-divider"></div>
          <div className="anomaly-section">
            <div className="anomaly-block">
              <div className="info-label">ML Anomaly Score</div>
              <div className="anomaly-value">{analysis.ml_anomaly_score}</div>
            </div>
            <BrainIcon />
          </div>
          {analysis.anomalies && analysis.anomalies.length > 0 && (
            <>
              <div className="info-divider"></div>
              <ul className="anomalies-list">
                {analysis.anomalies.map((a, i) => (
                  <li key={i} className="anomaly-item"><span className="anomaly-item-icon">⚡</span>{a}</li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>

      {/* ══════════════════════════════════════════════════
          SECTION 2: GENERATE FULL REPORT BUTTON
          (always visible — history button hidden until report loads)
      ══════════════════════════════════════════════════ */}
      <div className="fr-trigger-wrapper">
        {!reportGenerated ? (
          <button
            className="fr-generate-btn"
            onClick={handleGenerateReport}
            disabled={reportLoading}
          >
            {reportLoading ? "⏳ Scanning dataset... this may take a few seconds" : "📊 Generate Full Dataset Report"}
          </button>
        ) : (
          <button
            className="fr-generate-btn fr-regenerate-btn"
            onClick={() => { setReportGenerated(false); setFullReport(null); }}
          >
            🔄 Re-generate Report
          </button>
        )}
        {reportError && <p className="fr-error">{reportError}</p>}
      </div>

      {/* ══════════════════════════════════════════════════
          SECTION 3: FULL REPORT + HISTORY BUTTON
          Both only appear after report is generated
      ══════════════════════════════════════════════════ */}
      {fullReport && (
        <div
          className="fr-report-wrapper"
          data-timestamp={new Date().toLocaleString()}
        >
          <h2 className="fr-report-title">Full Analysis Report</h2>
          <p className="fr-report-subtitle">
            Complete scan of {fullReport.total_rows_scanned} telemetry rows
            with {fullReport.fault_rate_percent}% controlled fault injection rate
          </p>

          {/* ── Stat Cards ── */}
          <div className="fr-stats-grid">
            <StatCard label="Average Health Score" value={fullReport.average_health_score} sub="out of 100"
              highlight={fullReport.average_health_score >= 75 ? "fr-stat-good" : fullReport.average_health_score >= 40 ? "fr-stat-warning" : "fr-stat-danger"} />
            <StatCard label="Avg Failure Probability" value={`${fullReport.average_failure_probability}%`} sub="across all rows"
              highlight={fullReport.average_failure_probability > 50 ? "fr-stat-danger" : fullReport.average_failure_probability > 20 ? "fr-stat-warning" : "fr-stat-good"} />
            <StatCard label="Peak Failure Probability" value={`${fullReport.peak_failure_probability}%`} sub="worst single row" highlight="fr-stat-danger" />
            <StatCard label="ML Anomalies Detected" value={fullReport.ml_anomaly_count} sub={`${fullReport.ml_anomaly_percentage}% of rows`} highlight="fr-stat-warning" />
            <StatCard label="Rows With Faults" value={fullReport.total_rows_with_faults} sub={`${fullReport.fault_rate_percent}% fault rate`} />
            <StatCard label="Worst ML Score" value={fullReport.lowest_ml_score} sub="lower = more anomalous" highlight="fr-stat-danger" />
          </div>

          {/* ── Status Distribution ── */}
          <div className="fr-section">
            <h3 className="fr-section-title">🚦 Status Distribution</h3>
            <StatusBar distribution={fullReport.status_distribution} percentages={fullReport.status_percentages} />
          </div>

          {/* ── Anomaly Breakdown ── */}
          <div className="fr-section">
            <h3 className="fr-section-title">🔍 Anomaly Breakdown</h3>
            <p className="fr-most-common">Most common anomaly: <strong>{fullReport.most_common_anomaly}</strong></p>
            <AnomalyCountList anomalyCounts={fullReport.anomaly_counts} />
          </div>

          {/* ── Fault Injection Summary ── */}
          <div className="fr-section">
            <h3 className="fr-section-title">⚙️ Fault Injection Summary</h3>
            <AnomalyCountList anomalyCounts={fullReport.fault_injection_summary} />
          </div>

          {/* ── Worst Rows Table ── */}
          <div className="fr-section">
            <h3 className="fr-section-title">💀 Worst Performing Rows</h3>
            <WorstRowsTable worstRows={fullReport.worst_rows} />
          </div>

          {/* ══════════════════════════════════════════════
              ACTION BUTTONS — only visible after report loads
          ══════════════════════════════════════════════ */}
          <div className="fr-action-btns-row">

            {/* ── Download as PDF ── */}
            <button
              className="fr-pdf-btn"
              onClick={() => {
                // Set document title so the PDF filename is meaningful
                const original = document.title;
                document.title = "AutoSense_Full_Report";
                window.print();
                document.title = original;
              }}
            >
              <span className="btn-corner btn-corner--tl"></span>
              <span className="btn-corner btn-corner--tr"></span>
              <span className="btn-corner btn-corner--bl"></span>
              <span className="btn-corner btn-corner--br"></span>
              ⬇ DOWNLOAD AS PDF
            </button>

            {/* ── Check Previous History ── */}
            <button
              className="fr-history-btn"
              onClick={() => navigate("/history")}
            >
              <span className="btn-corner btn-corner--tl"></span>
              <span className="btn-corner btn-corner--tr"></span>
              <span className="btn-corner btn-corner--bl"></span>
              <span className="btn-corner btn-corner--br"></span>
              📂 CHECK PREVIOUS HISTORY
            </button>

          </div>

        </div>
      )}

      {/* ── Back Button ── */}
      <div className="back-button-wrapper">
        <button className="back-button" onClick={() => navigate("/dashboard")}>
          <span className="btn-corner btn-corner--tl"></span>
          <span className="btn-corner btn-corner--tr"></span>
          <span className="btn-corner btn-corner--bl"></span>
          <span className="btn-corner btn-corner--br"></span>
          Back
        </button>
      </div>
    </div>
  );
}