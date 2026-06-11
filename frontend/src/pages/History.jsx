/**
 * AutoSense – AI-Based Vehicle Health Monitoring System
 * Page   : History
 * File   : History.jsx
 * Purpose: Displays past alerts and full report summaries from the
 *          SQLite database. Two tabs — Alerts and Reports.
 *          Supports clearing all records via DELETE endpoints.
 */

import { useEffect, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import "./History.css";


/* ─── Status badge helper ─── */
function StatusBadge({ status }) {
  const color =
    status === "Good"     ? "#2dff6e"
    : status === "Warning"  ? "#ffc107"
    : "#ff4444";
  const icon =
    status === "Good"     ? "✅"
    : status === "Warning"  ? "⚠️"
    : "🔴";
  return (
    <span className="hist-badge" style={{ color, borderColor: color }}>
      {icon} {status}
    </span>
  );
}


/* ─── Alerts Tab ─── */
function AlertsTab() {
  const [alerts, setAlerts]   = useState([]);
  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);

  // Fetch alerts and stats together on mount
  const fetchData = () => {
    setLoading(true);
    Promise.all([
      axios.get("http://localhost:5000/alerts"),
      axios.get("http://localhost:5000/alerts/stats"),
    ])
      .then(([alertsRes, statsRes]) => {
        setAlerts(alertsRes.data.alerts);
        setStats(statsRes.data);
      })
      .catch((err) => console.error("[History] Alerts fetch error:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchData(); }, []);

  // Clear all alerts
  const handleClear = () => {
    if (!window.confirm("Delete all saved alerts? This cannot be undone.")) return;
    setClearing(true);
    axios.delete("http://localhost:5000/alerts")
      .then(() => { setAlerts([]); setStats(null); })
      .catch((err) => console.error("[History] Delete alerts error:", err))
      .finally(() => setClearing(false));
  };

  if (loading) return <div className="hist-loading">Loading alerts...</div>;

  return (
    <div className="hist-tab-content">

      {/* ── Stats summary cards ── */}
      {stats && (
        <div className="hist-stats-row">
          <div className="hist-stat-card">
            <div className="hist-stat-value">{stats.total_alerts}</div>
            <div className="hist-stat-label">Total Alerts</div>
          </div>
          <div className="hist-stat-card hist-stat-warning">
            <div className="hist-stat-value">{stats.warning_count}</div>
            <div className="hist-stat-label">⚠️ Warnings</div>
          </div>
          <div className="hist-stat-card hist-stat-danger">
            <div className="hist-stat-value">{stats.critical_count}</div>
            <div className="hist-stat-label">🔴 Critical</div>
          </div>
          <div className="hist-stat-card">
            <div className="hist-stat-value">{stats.avg_health_score ?? "—"}</div>
            <div className="hist-stat-label">Avg Health Score</div>
          </div>
          <div className="hist-stat-card">
            <div className="hist-stat-value">{stats.avg_failure_prob ?? "—"}%</div>
            <div className="hist-stat-label">Avg Failure Prob</div>
          </div>
          <div className="hist-stat-card">
            <div className="hist-stat-value hist-stat-small">{stats.most_common_anomaly}</div>
            <div className="hist-stat-label">Most Common Anomaly</div>
          </div>
        </div>
      )}

      {/* ── Clear button ── */}
      <div className="hist-actions">
        <button
          className="hist-clear-btn"
          onClick={handleClear}
          disabled={clearing || alerts.length === 0}
        >
          {clearing ? "Clearing..." : "🗑️ Clear All Alerts"}
        </button>
        <span className="hist-count">{alerts.length} alert(s) shown</span>
      </div>

      {/* ── Alerts list ── */}
      {alerts.length === 0 ? (
        <div className="hist-empty">
          <p>No alerts saved yet.</p>
          <p className="hist-empty-sub">Alerts are recorded automatically when the vehicle status is Warning or Critical.</p>
        </div>
      ) : (
        <div className="hist-alert-list">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`hist-alert-card ${
                alert.status === "Critical" ? "hist-card-critical"
                : alert.status === "Warning" ? "hist-card-warning"
                : "hist-card-good"
              }`}
            >
              {/* Header row */}
              <div className="hist-alert-header">
                <StatusBadge status={alert.status} />
                <span className="hist-alert-time">🕐 {alert.timestamp}</span>
                <span className="hist-alert-id">#{alert.id}</span>
              </div>

              {/* Metrics row */}
              <div className="hist-alert-metrics">
                <span className="hist-metric">
                  <span className="hist-metric-label">Health Score</span>
                  <span className={`hist-metric-value ${
                    alert.health_score >= 75 ? "good"
                    : alert.health_score >= 40 ? "warning"
                    : "danger"
                  }`}>{alert.health_score}</span>
                </span>
                <span className="hist-metric">
                  <span className="hist-metric-label">Failure Prob</span>
                  <span className="hist-metric-value">{alert.failure_prob}%</span>
                </span>
                <span className="hist-metric">
                  <span className="hist-metric-label">ML Score</span>
                  <span className="hist-metric-value">{alert.ml_score}</span>
                </span>
              </div>

              {/* Anomalies */}
              {alert.anomalies && alert.anomalies.length > 0 && (
                <div className="hist-alert-anomalies">
                  {alert.anomalies.map((a, i) => (
                    <span key={i} className="hist-anomaly-tag">⚡ {a}</span>
                  ))}
                </div>
              )}

              {/* Faults injected */}
              {alert.faults && alert.faults.length > 0 && (
                <div className="hist-alert-faults">
                  <span className="hist-faults-label">Faults injected: </span>
                  {alert.faults.map((f, i) => (
                    <span key={i} className="hist-fault-tag">🔧 {f}</span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


/* ─── Reports Tab ─── */
function ReportsTab() {
  const [reports, setReports]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [clearing, setClearing] = useState(false);

  const fetchReports = () => {
    setLoading(true);
    axios.get("http://localhost:5000/reports")
      .then((res) => setReports(res.data.reports))
      .catch((err) => console.error("[History] Reports fetch error:", err))
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchReports(); }, []);

  const handleClear = () => {
    if (!window.confirm("Delete all saved report summaries? This cannot be undone.")) return;
    setClearing(true);
    axios.delete("http://localhost:5000/reports")
      .then(() => setReports([]))
      .catch((err) => console.error("[History] Delete reports error:", err))
      .finally(() => setClearing(false));
  };

  if (loading) return <div className="hist-loading">Loading reports...</div>;

  return (
    <div className="hist-tab-content">

      {/* ── Clear button ── */}
      <div className="hist-actions">
        <button
          className="hist-clear-btn"
          onClick={handleClear}
          disabled={clearing || reports.length === 0}
        >
          {clearing ? "Clearing..." : "🗑️ Clear All Reports"}
        </button>
        <span className="hist-count">{reports.length} report(s) saved</span>
      </div>

      {/* ── Reports list ── */}
      {reports.length === 0 ? (
        <div className="hist-empty">
          <p>No reports saved yet.</p>
          <p className="hist-empty-sub">Reports are saved automatically when you click "Generate Full Dataset Report".</p>
        </div>
      ) : (
        <div className="hist-report-list">
          {reports.map((report) => (
            <div key={report.id} className="hist-report-card">

              {/* Header */}
              <div className="hist-report-header">
                <span className="hist-report-title">📋 Full Scan Report #{report.id}</span>
                <span className="hist-alert-time">🕐 {report.timestamp}</span>
              </div>

              {/* Stat grid */}
              <div className="hist-report-grid">
                <div className="hist-report-stat">
                  <span className="hist-metric-label">Total Rows</span>
                  <span className="hist-metric-value">{report.total_rows}</span>
                </div>
                <div className="hist-report-stat">
                  <span className="hist-metric-label">Avg Health Score</span>
                  <span className={`hist-metric-value ${
                    report.avg_health_score >= 75 ? "good"
                    : report.avg_health_score >= 40 ? "warning"
                    : "danger"
                  }`}>{report.avg_health_score}</span>
                </div>
                <div className="hist-report-stat">
                  <span className="hist-metric-label">Avg Failure Prob</span>
                  <span className="hist-metric-value">{report.avg_failure_prob}%</span>
                </div>
                <div className="hist-report-stat">
                  <span className="hist-metric-label">Peak Failure Prob</span>
                  <span className="hist-metric-value danger">{report.peak_failure_prob}%</span>
                </div>
                <div className="hist-report-stat">
                  <span className="hist-metric-label">ML Anomalies</span>
                  <span className="hist-metric-value">{report.ml_anomaly_count} ({report.ml_anomaly_pct}%)</span>
                </div>
                <div className="hist-report-stat">
                  <span className="hist-metric-label">Fault Rate</span>
                  <span className="hist-metric-value">{report.fault_rate_percent}%</span>
                </div>
              </div>

              {/* Status distribution mini-bar */}
              <div className="hist-report-bar-wrapper">
                <div className="hist-report-bar">
                  {report.good_count > 0 && (
                    <div
                      className="fr-bar-segment fr-bar-good"
                      style={{ width: `${(report.good_count / report.total_rows) * 100}%` }}
                      title={`Good: ${report.good_count}`}
                    />
                  )}
                  {report.warning_count > 0 && (
                    <div
                      className="fr-bar-segment fr-bar-warning"
                      style={{ width: `${(report.warning_count / report.total_rows) * 100}%` }}
                      title={`Warning: ${report.warning_count}`}
                    />
                  )}
                  {report.critical_count > 0 && (
                    <div
                      className="fr-bar-segment fr-bar-critical"
                      style={{ width: `${(report.critical_count / report.total_rows) * 100}%` }}
                      title={`Critical: ${report.critical_count}`}
                    />
                  )}
                </div>
                <div className="hist-bar-labels">
                  <span className="fr-label-good">✅ {report.good_count} Good</span>
                  <span className="fr-label-warning">⚠️ {report.warning_count} Warning</span>
                  <span className="fr-label-critical">🔴 {report.critical_count} Critical</span>
                </div>
              </div>

              {/* Most common anomaly */}
              <div className="hist-report-footer">
                <span className="hist-faults-label">Most common anomaly: </span>
                <span className="hist-anomaly-tag">⚡ {report.most_common_anomaly}</span>
              </div>

            </div>
          ))}
        </div>
      )}
    </div>
  );
}


/* ═══════════════════════════════════════════════════════════════
   MAIN HISTORY PAGE
═══════════════════════════════════════════════════════════════ */
export default function History() {
  // "alerts" or "reports"
  const [activeTab, setActiveTab] = useState("alerts");
  const navigate = useNavigate();

  return (
    <div className="hist-page">

      <h1 className="hist-title">📂 Previous History</h1>
      <p className="hist-subtitle">
        All past alerts and full report summaries stored in the database.
      </p>

      {/* ── Tab switcher ── */}
      <div className="hist-tabs">
        <button
          className={`hist-tab-btn ${activeTab === "alerts" ? "hist-tab-active" : ""}`}
          onClick={() => setActiveTab("alerts")}
        >
          🚨 Alerts
        </button>
        <button
          className={`hist-tab-btn ${activeTab === "reports" ? "hist-tab-active" : ""}`}
          onClick={() => setActiveTab("reports")}
        >
          📋 Full Reports
        </button>
      </div>

      {/* ── Tab content ── */}
      {activeTab === "alerts"  && <AlertsTab />}
      {activeTab === "reports" && <ReportsTab />}

      {/* ── Back button ── */}
      <div className="back-button-wrapper">
        <button className="back-button" onClick={() => navigate("/analysis")}>
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