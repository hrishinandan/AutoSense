"""
AutoSense – AI-Based Vehicle Health Monitoring System
Module  : Flask Backend API
File    : app.py
Purpose : Provides all API endpoints for the AutoSense system.

Endpoints:
    GET  /simulate       – raw telemetry + fault injection
    GET  /analyze        – live analysis (saves alerts to DB automatically)
    GET  /full-report    – full dataset scan (saves report summary to DB)

    GET  /alerts         – fetch all saved alerts
    GET  /alerts/stats   – alert count + stats
    DELETE /alerts       – clear all alerts

    GET  /reports        – fetch all saved report summaries
    DELETE /reports      – clear all report summaries
"""

from flask import Flask, jsonify
from flask_cors import CORS

from modules.simulator        import VehicleSimulator
from modules.fault_injector   import FaultInjector
from modules.analysis         import VehicleAnalyzer
from modules.report_generator import ReportGenerator
from modules.database         import DatabaseManager          # ← NEW


# ─────────────────────────────────────────────────────────────────
# APP INITIALIZATION
# ─────────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)


# ─────────────────────────────────────────────────────────────────
# MODULE INITIALIZATION
# ─────────────────────────────────────────────────────────────────

print("[App] Initializing AutoSense backend...")

simulator      = VehicleSimulator()
fault_injector = FaultInjector()
analyzer       = VehicleAnalyzer()
db             = DatabaseManager()               # ← NEW: single shared DB instance

# ReportGenerator is created fresh per /full-report call (see below)

print("[App] Initialization complete.\n")


# ─────────────────────────────────────────────────────────────────
# ROUTES — SIMULATION & ANALYSIS
# ─────────────────────────────────────────────────────────────────

@app.route("/simulate", methods=["GET"])
def simulate():
    """
    GET /simulate
    Returns raw simulated telemetry with injected faults.
    No analysis, no DB write.
    """
    try:
        data   = simulator.get_next_data()
        result = fault_injector.inject_fault(data)
        return jsonify({
            "data"  : result["data"],
            "faults": result["faults"]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/analyze", methods=["GET"])
def analyze():
    """
    GET /analyze
    Full live pipeline: simulate → fault inject → analyze.
    Automatically saves to alerts table if result is Warning/Critical
    or has anomalies or failure_probability > 50.

    Response:
        {
            "data"       : { ...telemetry... },
            "faults"     : [ ... ],
            "analysis"   : { health_score, anomalies, failure_probability,
                             status, ml_anomaly_score },
            "alert_saved": true/false
        }
    """
    try:
        raw_data     = simulator.get_next_data()
        fault_result = fault_injector.inject_fault(raw_data)
        faulted_data = fault_result["data"]
        faults       = fault_result["faults"]

        analysis_report = analyzer.analyze(faulted_data, faults)

        # ── Save to DB if alert conditions are met ────────────────
        alert_saved = db.save_alert(analysis_report, faults)

        return jsonify({
            "data"       : faulted_data,
            "faults"     : faults,
            "analysis"   : analysis_report,
            "alert_saved": alert_saved,      # frontend can use this to notify user
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/full-report", methods=["GET"])
def full_report():
    """
    GET /full-report
    Scans the entire dataset, returns a comprehensive health report,
    and saves a summary row to the reports table.

    A fresh ReportGenerator is created each call so the row index
    and trend history always start clean → reproducible report.
    """
    try:
        print("[App] /full-report called — starting full dataset scan...")

        rg     = ReportGenerator()
        report = rg.generate()

        # ── Save summary to the reports table ─────────────────────
        db.save_report(report)

        print("[App] /full-report complete. Summary saved to DB.")
        return jsonify(report)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────
# ROUTES — ALERTS
# ─────────────────────────────────────────────────────────────────

@app.route("/alerts", methods=["GET"])
def get_alerts():
    """
    GET /alerts
    Returns all saved alerts from the database, newest first.

    Optional query param: ?limit=50  (default 100)

    Response:
        {
            "count" : int,
            "alerts": [
                {
                    "id"          : int,
                    "timestamp"   : "2024-01-15T14:32:01",
                    "status"      : "Warning" | "Critical",
                    "health_score": int,
                    "failure_prob": int,
                    "anomalies"   : [ "Overheating detected...", ... ],
                    "faults"      : [ "Overheating", ... ],
                    "ml_score"    : float
                },
                ...
            ]
        }
    """
    try:
        from flask import request
        limit  = request.args.get("limit", 100, type=int)
        alerts = db.get_all_alerts(limit=limit)
        return jsonify({
            "count" : len(alerts),
            "alerts": alerts,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/alerts/stats", methods=["GET"])
def get_alert_stats():
    """
    GET /alerts/stats
    Returns summary statistics about all stored alerts.

    Response:
        {
            "total_alerts"        : int,
            "warning_count"       : int,
            "critical_count"      : int,
            "avg_health_score"    : float,
            "avg_failure_prob"    : float,
            "most_common_anomaly" : str
        }
    """
    try:
        stats = db.get_alert_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/alerts", methods=["DELETE"])
def delete_alerts():
    """
    DELETE /alerts
    Clears all alerts from the database.

    Response:
        { "deleted": int, "message": "All alerts cleared." }
    """
    try:
        deleted = db.delete_all_alerts()
        return jsonify({
            "deleted": deleted,
            "message": "All alerts cleared."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────
# ROUTES — REPORTS
# ─────────────────────────────────────────────────────────────────

@app.route("/reports", methods=["GET"])
def get_reports():
    """
    GET /reports
    Returns all saved full report summaries, newest first.

    Optional query param: ?limit=20  (default 50)

    Response:
        {
            "count"  : int,
            "reports": [
                {
                    "id"                  : int,
                    "timestamp"           : "2024-01-15T14:35:00",
                    "total_rows"          : int,
                    "avg_health_score"    : float,
                    "avg_failure_prob"    : float,
                    "peak_failure_prob"   : int,
                    "good_count"          : int,
                    "warning_count"       : int,
                    "critical_count"      : int,
                    "most_common_anomaly" : str,
                    "ml_anomaly_count"    : int,
                    "ml_anomaly_pct"      : float,
                    "fault_rate_percent"  : float
                },
                ...
            ]
        }
    """
    try:
        from flask import request
        limit   = request.args.get("limit", 50, type=int)
        reports = db.get_all_reports(limit=limit)
        return jsonify({
            "count"  : len(reports),
            "reports": reports,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reports", methods=["DELETE"])
def delete_reports():
    """
    DELETE /reports
    Clears all report summaries from the database.

    Response:
        { "deleted": int, "message": "All reports cleared." }
    """
    try:
        deleted = db.delete_all_reports()
        return jsonify({
            "deleted": deleted,
            "message": "All reports cleared."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("[App] Starting Flask server on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)