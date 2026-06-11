"""
AutoSense – AI-Based Vehicle Health Monitoring System
Module  : Full Dataset Report Generator
File    : report_generator.py
Path    : C:/Users/hrish/AutoSense/backend/modules/report_generator.py
Purpose : Scans the entire cleaned dataset, applies controlled fault injection
          at a fixed rate, runs the full analysis pipeline, and produces a
          comprehensive vehicle health report.

Performance fix:
    OLD: predict() called once per row → N separate sklearn calls → very slow
    NEW: predict_batch() called once for ALL rows → 1 sklearn call → very fast

    Two-pass approach:
        Pass 1 — Collect all rows + apply fault injection → build full data list
                  + run predict_batch() once for all ML scores
        Pass 2 — Loop rows with ML scores pre-computed → run only rule-based
                  checks + trend analysis (no ML call per row)

    Result: full report goes from 5-8 minutes → under 10 seconds.
"""

import sys
import pandas as pd
from collections import defaultdict

from modules.simulator      import VehicleSimulator
from modules.fault_injector import FaultInjector
from modules.analysis       import VehicleAnalyzer


# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

# Inject a fault on every Nth row (1-based).
# Default 5 → 20% fault rate. Change to 10 for 10%, 3 for 33%.
FAULT_EVERY_N_ROWS = 5

# How many worst rows to include in the report
TOP_WORST_ROWS = 5


# ─────────────────────────────────────────────────────────────────
# CLASS: ReportGenerator
# ─────────────────────────────────────────────────────────────────

class ReportGenerator:
    """
    Scans the entire dataset and produces a full vehicle health report.

    Performance approach:
        - Pass 1: collect all rows + fault injection + batch ML scoring
        - Pass 2: rule-based checks + trend analysis per row
                  (uses pre-computed ML scores — no per-row ML call)
    """

    def __init__(self):
        print("[ReportGenerator] Initialising pipeline modules...")

        self.simulator     = VehicleSimulator()
        self.fault_injector = FaultInjector()

        # VehicleAnalyzer contains AnomalyDetector — we use it for
        # rule-based checks and trend analysis only during the full report.
        # ML scoring is done separately via predict_batch() for speed.
        self.analyzer = VehicleAnalyzer()

        print("[ReportGenerator] All modules ready. Call generate() to start.\n")

    # ─────────────────────────────────────────────────────────────
    # PUBLIC METHOD: generate
    # ─────────────────────────────────────────────────────────────

    def generate(self) -> dict:
        """
        Full two-pass scan of the dataset.

        Pass 1: Collect all rows + apply fault injection.
                Then call predict_batch() ONCE for all ML scores.

        Pass 2: Loop through rows using pre-computed ML scores.
                Run rule-based checks + trend analysis per row.
                No ML call inside the loop — already done in Pass 1.

        Returns:
            dict: Complete vehicle health report.
        """
        total_rows = len(self.simulator.dataset)
        print(f"[ReportGenerator] Starting full scan — {total_rows} rows...")

        # ══════════════════════════════════════════════════════════
        # PASS 1 — Collect all rows + controlled fault injection
        # ══════════════════════════════════════════════════════════
        print("[ReportGenerator] Pass 1: Collecting rows + fault injection...")

        all_rows        = []   # final data for each row (post-injection if applicable)
        all_faults      = []   # list of fault lists, one per row
        fault_type_counts      = defaultdict(int)
        total_rows_with_faults = 0

        for row_number in range(1, total_rows + 1):
            raw_data = self.simulator.get_next_data()

            # Controlled fault injection — every Nth row only
            if row_number % FAULT_EVERY_N_ROWS == 0:
                fault_result = self.fault_injector.inject_fault(raw_data)
                data   = fault_result["data"]
                faults = fault_result["faults"]

                if faults:
                    total_rows_with_faults += 1
                    for fault_name in faults:
                        fault_type_counts[fault_name] += 1
            else:
                data   = raw_data
                faults = []

            all_rows.append(data)
            all_faults.append(faults)

        # ── Run ML batch prediction ONCE for all rows ─────────────
        # This replaces N individual predict() calls with a single
        # vectorized sklearn operation — the key speed improvement.
        print("[ReportGenerator] Running batch ML prediction (single call)...")
        ml_results = self.analyzer.anomaly_detector.predict_batch(all_rows)
        print(f"[ReportGenerator] Batch ML done — {len(ml_results)} scores computed.")

        # ══════════════════════════════════════════════════════════
        # PASS 2 — Rule-based + trend analysis using pre-computed ML scores
        # ══════════════════════════════════════════════════════════
        print("[ReportGenerator] Pass 2: Running rule-based + trend analysis...")

        all_health_scores = []
        all_failure_probs = []
        status_counts     = {"Good": 0, "Warning": 0, "Critical": 0}
        anomaly_counts    = defaultdict(int)
        ml_anomaly_count  = 0
        lowest_ml_score   = float("inf")
        worst_rows        = []

        for row_number, (data, faults, ml_result) in enumerate(
            zip(all_rows, all_faults, ml_results), start=1
        ):
            # ── Run rule-based checks + trend (NO ML call inside) ──
            # We pass the pre-computed ml_result directly to a modified
            # analyze call so the analyzer skips its internal ML prediction.
            report = self._analyze_with_ml(data, faults, ml_result)

            # ── Collect results ────────────────────────────────────
            all_health_scores.append(report["health_score"])
            all_failure_probs.append(report["failure_probability"])

            status = report["status"]
            if status in status_counts:
                status_counts[status] += 1

            for anomaly_msg in report["anomalies"]:
                label = self._extract_anomaly_label(anomaly_msg)
                anomaly_counts[label] += 1

            ml_score = report["ml_anomaly_score"]
            if ml_score < lowest_ml_score:
                lowest_ml_score = ml_score
            if ml_score < -0.1:
                ml_anomaly_count += 1

            worst_rows.append({
                "row_number"         : row_number,
                "health_score"       : report["health_score"],
                "status"             : report["status"],
                "failure_probability": report["failure_probability"],
                "anomalies"          : report["anomalies"],
                "faults_injected"    : faults,
                "ml_anomaly_score"   : ml_score,
            })

            # Progress log every 500 rows
            if row_number % 500 == 0 or row_number == total_rows:
                print(f"[ReportGenerator] Pass 2: {row_number}/{total_rows} rows done...")

        # ── Build final summary ───────────────────────────────────
        print("[ReportGenerator] Scan complete. Building summary...\n")
        return self._summarize(
            total_rows             = total_rows,
            all_health_scores      = all_health_scores,
            all_failure_probs      = all_failure_probs,
            status_counts          = status_counts,
            anomaly_counts         = dict(anomaly_counts),
            fault_type_counts      = dict(fault_type_counts),
            total_rows_with_faults = total_rows_with_faults,
            ml_anomaly_count       = ml_anomaly_count,
            lowest_ml_score        = lowest_ml_score,
            worst_rows             = worst_rows,
        )

    # ─────────────────────────────────────────────────────────────
    # PRIVATE METHOD: _analyze_with_ml
    # ─────────────────────────────────────────────────────────────

    def _analyze_with_ml(self, data: dict, faults: list, ml_result: dict) -> dict:
        """
        Run rule-based checks + trend analysis using a PRE-COMPUTED ML result.

        This is identical to VehicleAnalyzer.analyze() EXCEPT it skips the
        internal AnomalyDetector.predict() call and uses the ml_result we
        already computed in batch during Pass 1.

        This is what eliminates the per-row ML overhead.

        Args:
            data      (dict): Telemetry row.
            faults    (list): Injected fault names.
            ml_result (dict): Pre-computed { "is_anomaly": bool, "score": float }

        Returns:
            dict: Health report identical in format to VehicleAnalyzer.analyze()
        """
        from modules.analysis import (
            PENALTY_PER_RULE, PENALTY_PER_FAULT,
            STATUS_GOOD_MIN, STATUS_WARNING_MIN,
        )

        health_score = 100
        anomalies    = []

        # ── 1. Rule-based checks (same as VehicleAnalyzer) ────────
        for rule in self.analyzer._rules:
            triggered, message = rule["check"](data)
            if triggered:
                anomalies.append(message)
                health_score -= PENALTY_PER_RULE

        # ── 2. Fault penalty ───────────────────────────────────────
        health_score -= len(faults) * PENALTY_PER_FAULT

        # ── 3. Use PRE-COMPUTED ML result (no predict() call) ──────
        if ml_result["is_anomaly"]:
            anomalies.append("ML Anomaly Detected")
            health_score -= 15

        # ── 4. Trend analysis (same sliding window as VehicleAnalyzer) ─
        temp = data.get("coolant_temperature_") or data.get("coolant_temp_") or 0
        rpm  = data.get("engine_rpm_", 0)

        self.analyzer.temp_history.append(temp)
        self.analyzer.rpm_history.append(rpm)
        self.analyzer.temp_history = self.analyzer.temp_history[-5:]
        self.analyzer.rpm_history  = self.analyzer.rpm_history[-5:]

        if (len(self.analyzer.temp_history) == 5 and
                all(x < y for x, y in zip(self.analyzer.temp_history,
                                          self.analyzer.temp_history[1:]))):
            anomalies.append("Rising Temperature Trend")
            health_score -= 10

        if (len(self.analyzer.rpm_history) == 5 and
                all(x < y for x, y in zip(self.analyzer.rpm_history,
                                          self.analyzer.rpm_history[1:]))):
            anomalies.append("Increasing Engine Stress Trend")
            health_score -= 10

        # ── 5. Clamp + derive metrics ──────────────────────────────
        health_score = max(0, min(100, health_score))

        base  = 100 - health_score
        bonus = len(anomalies) * 5
        failure_probability = max(0, min(100, base + bonus))

        if health_score >= STATUS_GOOD_MIN:
            status = "Good"
        elif health_score >= STATUS_WARNING_MIN:
            status = "Warning"
        else:
            status = "Critical"

        return {
            "health_score"        : health_score,
            "anomalies"           : anomalies,
            "failure_probability" : failure_probability,
            "status"              : status,
            "ml_anomaly_score"    : ml_result["score"],
        }

    # ─────────────────────────────────────────────────────────────
    # PRIVATE METHOD: _summarize  (unchanged from original)
    # ─────────────────────────────────────────────────────────────

    def _summarize(
        self,
        total_rows            : int,
        all_health_scores     : list,
        all_failure_probs     : list,
        status_counts         : dict,
        anomaly_counts        : dict,
        fault_type_counts     : dict,
        total_rows_with_faults: int,
        ml_anomaly_count      : int,
        lowest_ml_score       : float,
        worst_rows            : list,
    ) -> dict:

        avg_health   = round(sum(all_health_scores) / total_rows, 2)
        avg_failure  = round(sum(all_failure_probs) / total_rows, 2)
        peak_failure = max(all_failure_probs)

        status_percentages = {
            status: round((count / total_rows) * 100, 2)
            for status, count in status_counts.items()
        }

        most_common_anomaly = max(anomaly_counts, key=anomaly_counts.get) \
                              if anomaly_counts else "None"

        sorted_anomaly_counts = dict(
            sorted(anomaly_counts.items(), key=lambda x: x[1], reverse=True)
        )

        ml_anomaly_pct  = round((ml_anomaly_count / total_rows) * 100, 2)
        top_worst       = sorted(worst_rows, key=lambda r: r["health_score"])[:TOP_WORST_ROWS]
        final_lowest_ml = round(lowest_ml_score, 6) if lowest_ml_score != float("inf") else 0.0

        return {
            "total_rows_scanned"          : total_rows,
            "average_health_score"        : avg_health,
            "average_failure_probability" : avg_failure,
            "peak_failure_probability"    : peak_failure,
            "status_distribution"         : status_counts,
            "status_percentages"          : status_percentages,
            "anomaly_counts"              : sorted_anomaly_counts,
            "most_common_anomaly"         : most_common_anomaly,
            "fault_injection_summary"     : fault_type_counts,
            "total_rows_with_faults"      : total_rows_with_faults,
            "fault_rate_percent"          : round(
                (total_rows_with_faults / total_rows) * 100, 2
            ),
            "ml_anomaly_count"            : ml_anomaly_count,
            "ml_anomaly_percentage"       : ml_anomaly_pct,
            "lowest_ml_score"             : final_lowest_ml,
            "worst_rows"                  : top_worst,
        }

    # ─────────────────────────────────────────────────────────────
    # PRIVATE METHOD: _extract_anomaly_label  (unchanged)
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _extract_anomaly_label(anomaly_msg: str) -> str:
        exact_labels = [
            "ML Anomaly Detected",
            "Rising Temperature Trend",
            "Increasing Engine Stress Trend",
        ]
        for label in exact_labels:
            if label in anomaly_msg:
                return label

        for separator in [" detected", " —", " Issue"]:
            if separator in anomaly_msg:
                label = anomaly_msg.split(separator)[0].strip()
                if separator == " Issue":
                    label = label + " Issue"
                return label

        return anomaly_msg[:40]


# ─────────────────────────────────────────────────────────────────
# QUICK TEST – runs only when this file is executed directly
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  AutoSense — ReportGenerator Quick Test")
    print("=" * 60)

    rg     = ReportGenerator()
    report = rg.generate()

    print("\n" + "=" * 60)
    print("  FULL REPORT SUMMARY")
    print("=" * 60)
    print(f"\n  Total Rows Scanned        : {report['total_rows_scanned']}")
    print(f"  Average Health Score      : {report['average_health_score']}")
    print(f"  Average Failure Prob      : {report['average_failure_probability']}%")
    print(f"  Peak Failure Probability  : {report['peak_failure_probability']}%")

    print(f"\n  Status Distribution:")
    for status, count in report["status_distribution"].items():
        pct = report["status_percentages"][status]
        print(f"    {status:<10} : {count:>5} rows  ({pct}%)")

    print(f"\n  Top Anomalies:")
    for anomaly, count in list(report["anomaly_counts"].items())[:5]:
        print(f"    {anomaly:<40} : {count}")

    print(f"\n  ML Anomaly Count          : {report['ml_anomaly_count']}")
    print(f"  ML Anomaly Percentage     : {report['ml_anomaly_percentage']}%")
    print(f"  Lowest ML Score           : {report['lowest_ml_score']}")

    print(f"\n  Worst {len(report['worst_rows'])} Rows:")
    for row in report["worst_rows"]:
        print(f"    Row {row['row_number']:<6} | "
              f"Score: {row['health_score']:<4} | "
              f"Status: {row['status']:<9} | "
              f"Anomalies: {len(row['anomalies'])}")

    print("\n[DONE] Report generation complete.")