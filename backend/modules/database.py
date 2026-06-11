"""
AutoSense – AI-Based Vehicle Health Monitoring System
Module  : Database Manager
File    : database.py
Path    : C:/Users/hrish/AutoSense/backend/modules/database.py
Purpose : Manages the SQLite database for storing:
            1. alerts  – anomaly alerts from live /analyze calls
            2. reports – full dataset health summaries from /full-report calls

Database file:
    C:/Users/hrish/AutoSense/backend/database/autosense.db

Tables:
    alerts  (id, timestamp, status, health_score, failure_prob,
             anomalies, faults, ml_score)

    reports (id, timestamp, total_rows, avg_health_score,
             avg_failure_prob, peak_failure_prob,
             good_count, warning_count, critical_count,
             most_common_anomaly, ml_anomaly_count, fault_rate_percent)

Usage:
    from modules.database import DatabaseManager

    db = DatabaseManager()

    # Alerts
    db.save_alert(analysis_report, faults)
    db.get_all_alerts()
    db.get_alert_stats()
    db.delete_all_alerts()

    # Reports
    db.save_report(full_report_dict)
    db.get_all_reports()
    db.delete_all_reports()
"""

import sqlite3
import json
import os
from datetime import datetime


# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

DB_PATH = "C:/Users/hrish/AutoSense/backend/database/autosense.db"


# ─────────────────────────────────────────────────────────────────
# CLASS: DatabaseManager
# ─────────────────────────────────────────────────────────────────

class DatabaseManager:
    """
    Handles all SQLite operations for AutoSense.

    Two tables:
        alerts  — one row per anomaly alert (from /analyze)
        reports — one row per full dataset scan (from /full-report)
    """

    def __init__(self, db_path: str = DB_PATH):
        """
        Initialise the database — creates directory and both tables
        if they don't already exist. Safe to call on every startup.

        Args:
            db_path (str): Full path to the SQLite .db file.
        """
        self.db_path = db_path

        # Create the /database directory if it doesn't exist yet
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            print(f"[Database] Created directory: {db_dir}")

        self._create_tables()
        print(f"[Database] Ready — using: {self.db_path}")

    # ─────────────────────────────────────────────────────────────
    # PRIVATE: _create_tables
    # ─────────────────────────────────────────────────────────────

    def _create_tables(self) -> None:
        """Create both tables if they do not already exist."""

        alerts_sql = """
            CREATE TABLE IF NOT EXISTS alerts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp    TEXT    NOT NULL,
                status       TEXT    NOT NULL,
                health_score INTEGER NOT NULL,
                failure_prob INTEGER NOT NULL,
                anomalies    TEXT    NOT NULL,
                faults       TEXT    NOT NULL,
                ml_score     REAL    NOT NULL
            );
        """

        # Stores one summary row per full dataset scan.
        # Counts for Good/Warning/Critical rows come from status_distribution.
        reports_sql = """
            CREATE TABLE IF NOT EXISTS reports (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp            TEXT    NOT NULL,
                total_rows           INTEGER NOT NULL,
                avg_health_score     REAL    NOT NULL,
                avg_failure_prob     REAL    NOT NULL,
                peak_failure_prob    INTEGER NOT NULL,
                good_count           INTEGER NOT NULL,
                warning_count        INTEGER NOT NULL,
                critical_count       INTEGER NOT NULL,
                most_common_anomaly  TEXT    NOT NULL,
                ml_anomaly_count     INTEGER NOT NULL,
                ml_anomaly_pct       REAL    NOT NULL,
                fault_rate_percent   REAL    NOT NULL
            );
        """

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(alerts_sql)
            conn.execute(reports_sql)
            conn.commit()

    # ═════════════════════════════════════════════════════════════
    # ALERTS — save / get / stats / delete
    # ═════════════════════════════════════════════════════════════

    @staticmethod
    def _should_save_alert(analysis: dict) -> bool:
        """
        Return True if this analysis result qualifies as an alert.

        Trigger conditions (ANY one is enough):
            1. Status is "Warning" or "Critical"
            2. At least one anomaly was detected
            3. Failure probability > 50 %
        """
        return (
            analysis.get("status") in ("Warning", "Critical")
            or len(analysis.get("anomalies", [])) > 0
            or analysis.get("failure_probability", 0) > 50
        )

    def save_alert(self, analysis: dict, faults: list) -> bool:
        """
        Save a live analysis result as an alert if it meets trigger conditions.

        Called automatically inside the /analyze endpoint.
        Returns False silently if the result is normal (no alert saved).

        Args:
            analysis (dict): Output from VehicleAnalyzer.analyze()
            faults   (list): Fault names from FaultInjector

        Returns:
            bool: True if saved, False if conditions not met.
        """
        if not self._should_save_alert(analysis):
            return False

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO alerts
                    (timestamp, status, health_score, failure_prob,
                     anomalies, faults, ml_score)
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    analysis.get("status", "Unknown"),
                    analysis.get("health_score", 0),
                    analysis.get("failure_probability", 0),
                    json.dumps(analysis.get("anomalies", [])),
                    json.dumps(faults or []),
                    analysis.get("ml_anomaly_score", 0.0),
                )
            )
            conn.commit()

        return True

    def get_all_alerts(self, limit: int = 100) -> list:
        """
        Return all alerts from the database, newest first.

        Args:
            limit (int): Max rows to return (default 100).

        Returns:
            list of dicts: Each dict has id, timestamp, status,
                           health_score, failure_prob, anomalies,
                           faults, ml_score.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, timestamp, status, health_score,
                       failure_prob, anomalies, faults, ml_score
                FROM   alerts
                ORDER  BY id DESC
                LIMIT  ?;
                """,
                (limit,)
            ).fetchall()

        return [
            {
                "id"          : r["id"],
                "timestamp"   : r["timestamp"],
                "status"      : r["status"],
                "health_score": r["health_score"],
                "failure_prob": r["failure_prob"],
                "anomalies"   : json.loads(r["anomalies"]),
                "faults"      : json.loads(r["faults"]),
                "ml_score"    : r["ml_score"],
            }
            for r in rows
        ]

    def get_alert_stats(self) -> dict:
        """
        Return summary statistics across all stored alerts.

        Returns:
            dict: {
                total_alerts, warning_count, critical_count,
                avg_health_score, avg_failure_prob, most_common_anomaly
            }
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            summary = conn.execute("""
                SELECT
                    COUNT(*)                                             AS total_alerts,
                    SUM(CASE WHEN status = 'Warning'  THEN 1 ELSE 0 END) AS warning_count,
                    SUM(CASE WHEN status = 'Critical' THEN 1 ELSE 0 END) AS critical_count,
                    ROUND(AVG(health_score), 2)                          AS avg_health_score,
                    ROUND(AVG(failure_prob), 2)                          AS avg_failure_prob
                FROM alerts;
            """).fetchone()

            anomaly_rows = conn.execute(
                "SELECT anomalies FROM alerts;"
            ).fetchall()

        # Count individual anomaly occurrences to find the most common
        anomaly_counter: dict = {}
        for row in anomaly_rows:
            try:
                for msg in json.loads(row["anomalies"]):
                    label = msg.split(" —")[0].split(" detected")[0].strip()
                    anomaly_counter[label] = anomaly_counter.get(label, 0) + 1
            except (json.JSONDecodeError, TypeError):
                continue

        most_common = (
            max(anomaly_counter, key=anomaly_counter.get)
            if anomaly_counter else "None"
        )

        return {
            "total_alerts"        : summary["total_alerts"]     or 0,
            "warning_count"       : summary["warning_count"]    or 0,
            "critical_count"      : summary["critical_count"]   or 0,
            "avg_health_score"    : summary["avg_health_score"] or 0.0,
            "avg_failure_prob"    : summary["avg_failure_prob"] or 0.0,
            "most_common_anomaly" : most_common,
        }

    def delete_all_alerts(self) -> int:
        """
        Delete all alerts and reset the auto-increment counter.

        Returns:
            int: Number of rows deleted.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM alerts;")
            conn.execute(
                "DELETE FROM sqlite_sequence WHERE name = 'alerts';"
            )
            conn.commit()
        print(f"[Database] Deleted {cursor.rowcount} alert(s).")
        return cursor.rowcount

    # ═════════════════════════════════════════════════════════════
    # REPORTS — save / get / delete
    # ═════════════════════════════════════════════════════════════

    def save_report(self, report: dict) -> bool:
        """
        Save a full dataset health report summary to the reports table.

        Called automatically inside the /full-report endpoint after
        generate() completes. Extracts key summary fields from the
        full report dict and stores them as a single flat row.

        Args:
            report (dict): The complete dict returned by ReportGenerator.generate()

        Returns:
            bool: True if saved successfully.
        """
        # Extract status distribution counts safely
        status_dist    = report.get("status_distribution", {})
        good_count     = status_dist.get("Good",     0)
        warning_count  = status_dist.get("Warning",  0)
        critical_count = status_dist.get("Critical", 0)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO reports
                    (timestamp, total_rows, avg_health_score, avg_failure_prob,
                     peak_failure_prob, good_count, warning_count, critical_count,
                     most_common_anomaly, ml_anomaly_count, ml_anomaly_pct,
                     fault_rate_percent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    datetime.now().isoformat(timespec="seconds"),
                    report.get("total_rows_scanned",          0),
                    report.get("average_health_score",        0.0),
                    report.get("average_failure_probability", 0.0),
                    report.get("peak_failure_probability",    0),
                    good_count,
                    warning_count,
                    critical_count,
                    report.get("most_common_anomaly",         "None"),
                    report.get("ml_anomaly_count",            0),
                    report.get("ml_anomaly_percentage",       0.0),
                    report.get("fault_rate_percent",          0.0),
                )
            )
            conn.commit()

        print(f"[Database] Full report summary saved.")
        return True

    def get_all_reports(self, limit: int = 50) -> list:
        """
        Return all saved full report summaries, newest first.

        Args:
            limit (int): Max rows to return (default 50).

        Returns:
            list of dicts: Each dict has all report summary fields
                           plus id and timestamp.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, timestamp, total_rows, avg_health_score,
                       avg_failure_prob, peak_failure_prob,
                       good_count, warning_count, critical_count,
                       most_common_anomaly, ml_anomaly_count,
                       ml_anomaly_pct, fault_rate_percent
                FROM   reports
                ORDER  BY id DESC
                LIMIT  ?;
                """,
                (limit,)
            ).fetchall()

        return [
            {
                "id"                  : r["id"],
                "timestamp"           : r["timestamp"],
                "total_rows"          : r["total_rows"],
                "avg_health_score"    : r["avg_health_score"],
                "avg_failure_prob"    : r["avg_failure_prob"],
                "peak_failure_prob"   : r["peak_failure_prob"],
                "good_count"          : r["good_count"],
                "warning_count"       : r["warning_count"],
                "critical_count"      : r["critical_count"],
                "most_common_anomaly" : r["most_common_anomaly"],
                "ml_anomaly_count"    : r["ml_anomaly_count"],
                "ml_anomaly_pct"      : r["ml_anomaly_pct"],
                "fault_rate_percent"  : r["fault_rate_percent"],
            }
            for r in rows
        ]

    def delete_all_reports(self) -> int:
        """
        Delete all report summaries and reset the auto-increment counter.

        Returns:
            int: Number of rows deleted.
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM reports;")
            conn.execute(
                "DELETE FROM sqlite_sequence WHERE name = 'reports';"
            )
            conn.commit()
        print(f"[Database] Deleted {cursor.rowcount} report(s).")
        return cursor.rowcount


# ─────────────────────────────────────────────────────────────────
# QUICK TEST – runs only when this file is executed directly
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  AutoSense — DatabaseManager Quick Test")
    print("=" * 55)

    db = DatabaseManager()

    # ── Test alerts ───────────────────────────────────────────────
    print("\n--- Testing Alerts ---")
    saved1 = db.save_alert({
        "health_score": 65, "status": "Warning",
        "failure_probability": 35,
        "anomalies": ["Overheating detected — 115.2°C"],
        "ml_anomaly_score": -0.12,
    }, ["Overheating"])

    saved2 = db.save_alert({
        "health_score": 20, "status": "Critical",
        "failure_probability": 80,
        "anomalies": ["Engine Stress detected", "Battery Issue detected"],
        "ml_anomaly_score": -0.35,
    }, ["Engine Stress", "Battery Drop"])

    saved3 = db.save_alert({   # should NOT be saved — all good
        "health_score": 95, "status": "Good",
        "failure_probability": 5,
        "anomalies": [], "ml_anomaly_score": 0.08,
    }, [])

    print(f"  Warning saved  : {saved1}")
    print(f"  Critical saved : {saved2}")
    print(f"  Good saved     : {saved3}  ← should be False")

    alerts = db.get_all_alerts()
    print(f"  Alerts in DB   : {len(alerts)}")

    stats = db.get_alert_stats()
    print(f"  Stats          : {stats}")

    # ── Test reports ──────────────────────────────────────────────
    print("\n--- Testing Reports ---")
    sample_report = {
        "total_rows_scanned"          : 984,
        "average_health_score"        : 78.4,
        "average_failure_probability" : 22.1,
        "peak_failure_probability"    : 100,
        "status_distribution"         : {"Good": 720, "Warning": 180, "Critical": 84},
        "most_common_anomaly"         : "Overheating",
        "ml_anomaly_count"            : 42,
        "ml_anomaly_percentage"       : 4.27,
        "fault_rate_percent"          : 20.0,
    }

    db.save_report(sample_report)
    reports = db.get_all_reports()
    print(f"  Reports in DB  : {len(reports)}")
    for r in reports:
        print(f"    [{r['id']}] {r['timestamp']} | "
              f"Avg Health: {r['avg_health_score']} | "
              f"Rows: {r['total_rows']}")

    # ── Cleanup ───────────────────────────────────────────────────
    print("\n--- Cleanup ---")
    db.delete_all_alerts()
    db.delete_all_reports()
    print(f"  Alerts remaining  : {len(db.get_all_alerts())}")
    print(f"  Reports remaining : {len(db.get_all_reports())}")

    print("\n[DONE] DatabaseManager test complete.")