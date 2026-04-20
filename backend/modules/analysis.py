"""
AutoSense – AI-Based Vehicle Health Monitoring System
Module  : Vehicle Health Analyzer
File    : analysis.py
Path    : C:/Users/hrish/AutoSense/backend/modules/analysis.py
Purpose : Analyses a single telemetry row and produces a complete
          vehicle health report using rule-based threshold checks,
          ML anomaly detection (Isolation Forest), and trend analysis.

Output format:
    {
        "health_score"        : int   (0 – 100),
        "anomalies"           : list  (human-readable issue descriptions),
        "failure_probability" : int   (0 – 100),
        "status"              : str   ("Good" | "Warning" | "Critical"),
        "ml_anomaly_score"    : float (raw Isolation Forest score)
    }

Usage:
    from modules.analysis import VehicleAnalyzer

    analyzer = VehicleAnalyzer()
    report   = analyzer.analyze(telemetry_row, faults_list)
    print(report)
"""

from modules.anomaly import AnomalyDetector


# ─────────────────────────────────────────────────────────────────
# THRESHOLDS  –  single source of truth for all limit values
# Adjust these constants to tune sensitivity without touching logic.
# ─────────────────────────────────────────────────────────────────

THRESHOLD_COOLANT_TEMP_HIGH     = 110.0   # °C   – overheating danger zone
THRESHOLD_ENGINE_RPM_HIGH       = 5000.0  # RPM  – engine stress
THRESHOLD_ENGINE_LOAD_HIGH      = 85.0    # %    – engine stress
THRESHOLD_VEHICLE_SPEED_HIGH    = 120.0   # km/h – overspeed
THRESHOLD_VOLTAGE_LOW           = 12.0    # V    – weak battery / alternator
THRESHOLD_INTAKE_TEMP_HIGH      = 50.0    # °C   – intake air issue
THRESHOLD_FUEL_RATIO_LOW        = 0.8     # λ    – lean mixture
THRESHOLD_FUEL_RATIO_HIGH       = 1.2     # λ    – rich mixture

# Score penalty applied for each rule that fires
PENALTY_PER_RULE  = 15   # points deducted per triggered rule
PENALTY_PER_FAULT = 5    # extra points deducted per injected fault

# Status band boundaries
STATUS_GOOD_MIN     = 75   # health_score ≥ 75  → Good
STATUS_WARNING_MIN  = 40   # health_score ≥ 40  → Warning  (else Critical)


# ─────────────────────────────────────────────────────────────────
# CLASS: VehicleAnalyzer
# ─────────────────────────────────────────────────────────────────

class VehicleAnalyzer:
    """
    Analyses vehicle telemetry data using:
        1. Rule-based threshold checks  (deterministic, explainable)
        2. ML anomaly detection         (Isolation Forest via AnomalyDetector)
        3. Simple trend analysis        (last-5-readings window)

    Each check reduces the health score when violated. The final
    status is derived from the resulting score.
    """

    def __init__(self):
        """
        Build the ordered list of rule checkers and initialize
        the ML anomaly detector and trend history buffers.
        """
        # Register all rules in one place — easy to add/remove rules here
        self._rules = [
            {"name": "Overheating",       "check": self._check_overheating},
            {"name": "Engine Stress",     "check": self._check_engine_stress},
            {"name": "Overspeed",         "check": self._check_overspeed},
            {"name": "Battery Issue",     "check": self._check_battery},
            {"name": "Intake Issue",      "check": self._check_intake},
            {"name": "Fuel Mixture Issue","check": self._check_fuel_mixture},
        ]

        # ML anomaly detector — trains on cleaned_data.csv at startup
        self.anomaly_detector = AnomalyDetector()

        # Trend history buffers — persist across analyze() calls so the
        # sliding window builds up naturally as the simulator streams data.
        self.temp_history = []
        self.rpm_history  = []

        print(f"[Analyzer] Initialised with {len(self._rules)} rule(s) loaded.")


    # ─────────────────────────────────────────────────────────────
    # PUBLIC METHOD: analyze
    # ─────────────────────────────────────────────────────────────

    def analyze(self, data: dict, faults: list) -> dict:
        """
        Run all checks on a telemetry row and return a structured
        health report.

        Scoring pipeline:
            1. Start at 100.
            2. Deduct PENALTY_PER_RULE  for every rule violation.
            3. Deduct PENALTY_PER_FAULT for every injected fault.
            4. Deduct 15 pts if the ML model flags an anomaly.
            5. Deduct 10 pts for a rising coolant temperature trend.
            6. Deduct 10 pts for a continuously increasing RPM trend.
            7. Clamp to [0, 100].

        Args:
            data   (dict): Single telemetry row (post fault injection).
            faults (list): Fault names injected by FaultInjector.

        Returns:
            dict: {
                "health_score"        : int,
                "anomalies"           : list[str],
                "failure_probability" : int,
                "status"              : str,
                "ml_anomaly_score"    : float
            }
        """
        health_score = 100
        anomalies    = []

        # ── 1. Rule-based checks ──────────────────────────────────
        for rule in self._rules:
            triggered, message = rule["check"](data)
            if triggered:
                anomalies.append(message)
                health_score -= PENALTY_PER_RULE

        # ── 2. Injected fault penalty ─────────────────────────────
        # Captures faults that haven't yet crossed a hard threshold.
        health_score -= len(faults) * PENALTY_PER_FAULT

        # ── 3. ML anomaly detection ───────────────────────────────
        ml_result = self.anomaly_detector.predict(data)
        if ml_result["is_anomaly"]:
            anomalies.append("ML Anomaly Detected")
            health_score -= 15

        # ── 4. Trend analysis (sliding window of 5) ───────────────
        # Extract sensor values safely — handle both column name variants
        temp = data.get("coolant_temperature_") or data.get("coolant_temp_") or 0
        rpm  = data.get("engine_rpm_", 0)

        # Append and keep only the most recent 5 readings
        self.temp_history.append(temp)
        self.rpm_history.append(rpm)
        self.temp_history = self.temp_history[-5:]
        self.rpm_history  = self.rpm_history[-5:]

        # Flag a strictly increasing sequence as a warning trend
        if (len(self.temp_history) == 5 and
                all(x < y for x, y in zip(self.temp_history,
                                          self.temp_history[1:]))):
            anomalies.append("Rising Temperature Trend")
            health_score -= 10

        if (len(self.rpm_history) == 5 and
                all(x < y for x, y in zip(self.rpm_history,
                                          self.rpm_history[1:]))):
            anomalies.append("Increasing Engine Stress Trend")
            health_score -= 10

        # ── 5. Final clamp ────────────────────────────────────────
        health_score = max(0, min(100, health_score))

        # ── 6. Derived metrics ────────────────────────────────────
        failure_probability = self._calculate_failure_probability(
            health_score, len(anomalies)
        )
        status = self._determine_status(health_score)

        return {
            "health_score"        : health_score,
            "anomalies"           : anomalies,
            "failure_probability" : failure_probability,
            "status"              : status,
            "ml_anomaly_score"    : ml_result["score"],
        }


    # ─────────────────────────────────────────────────────────────
    # PRIVATE RULE CHECKERS
    # Each returns (triggered: bool, detail_message: str)
    # ─────────────────────────────────────────────────────────────

    def _check_overheating(self, data: dict) -> tuple:
        """Rule: Coolant temperature above safe operating limit (>110 °C)."""
        key   = self._find_key(data, ["coolant_temp_", "coolant_temperature_"])
        value = data.get(key) if key else None
        if value is not None and value > THRESHOLD_COOLANT_TEMP_HIGH:
            return True, (f"Overheating detected — coolant temperature is "
                          f"{value:.1f}°C (limit: {THRESHOLD_COOLANT_TEMP_HIGH}°C)")
        return False, ""

    def _check_engine_stress(self, data: dict) -> tuple:
        """Rule: RPM > 5000 OR engine load > 85 %."""
        key_rpm  = self._find_key(data, ["engine_rpm_", "engine_rpm"])
        key_load = self._find_key(data, ["engine_load_", "engine_load",
                                         "calculated_engine_load_"])
        rpm  = data.get(key_rpm)  if key_rpm  else None
        load = data.get(key_load) if key_load else None

        rpm_triggered  = rpm  is not None and rpm  > THRESHOLD_ENGINE_RPM_HIGH
        load_triggered = load is not None and load > THRESHOLD_ENGINE_LOAD_HIGH

        if rpm_triggered or load_triggered:
            parts = []
            if rpm_triggered:
                parts.append(f"RPM {rpm:.0f} (limit: {THRESHOLD_ENGINE_RPM_HIGH:.0f})")
            if load_triggered:
                parts.append(f"load {load:.1f}% (limit: {THRESHOLD_ENGINE_LOAD_HIGH}%)")
            return True, "Engine Stress detected — " + ", ".join(parts)
        return False, ""

    def _check_overspeed(self, data: dict) -> tuple:
        """Rule: Vehicle speed > 120 km/h."""
        key   = self._find_key(data, ["vehicle_speed_", "vehicle_speed"])
        value = data.get(key) if key else None
        if value is not None and value > THRESHOLD_VEHICLE_SPEED_HIGH:
            return True, (f"Overspeed detected — vehicle speed is "
                          f"{value:.1f} km/h (limit: {THRESHOLD_VEHICLE_SPEED_HIGH} km/h)")
        return False, ""

    def _check_battery(self, data: dict) -> tuple:
        """Rule: Control module voltage < 12 V."""
        key   = self._find_key(data, ["control_module_voltage_",
                                      "control_module_voltage"])
        value = data.get(key) if key else None
        if value is not None and value < THRESHOLD_VOLTAGE_LOW:
            return True, (f"Battery Issue detected — control module voltage is "
                          f"{value:.2f}V (minimum: {THRESHOLD_VOLTAGE_LOW}V)")
        return False, ""

    def _check_intake(self, data: dict) -> tuple:
        """Rule: Intake air temperature > 50 °C."""
        key   = self._find_key(data, ["intake_air_temp_",
                                      "intake_air_temperature_",
                                      "intake_air_temp"])
        value = data.get(key) if key else None
        if value is not None and value > THRESHOLD_INTAKE_TEMP_HIGH:
            return True, (f"Intake Issue detected — intake air temperature is "
                          f"{value:.1f}°C (limit: {THRESHOLD_INTAKE_TEMP_HIGH}°C)")
        return False, ""

    def _check_fuel_mixture(self, data: dict) -> tuple:
        """Rule: Fuel-air ratio < 0.8 (lean) OR > 1.2 (rich)."""
        key   = self._find_key(data, ["fuel_air_commanded_equiv_ratio_",
                                      "commanded_equiv_ratio_",
                                      "fuel_air_commanded_equiv_ratio"])
        value = data.get(key) if key else None
        if value is not None and value > 0.1:
            if value < THRESHOLD_FUEL_RATIO_LOW:
                return True, (f"Fuel Mixture Issue — lean mixture detected "
                              f"(ratio: {value:.3f}, minimum: {THRESHOLD_FUEL_RATIO_LOW})")
            if value > THRESHOLD_FUEL_RATIO_HIGH:
                return True, (f"Fuel Mixture Issue — rich mixture detected "
                              f"(ratio: {value:.3f}, maximum: {THRESHOLD_FUEL_RATIO_HIGH})")
        return False, ""


    # ─────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _calculate_failure_probability(health_score: int,
                                       anomaly_count: int) -> int:
        """
        Derive failure probability from health score and anomaly count.

        Formula:
            base        = 100 - health_score
            bonus       = anomaly_count * 5
            probability = clamp(base + bonus, 0, 100)
        """
        base  = 100 - health_score
        bonus = anomaly_count * 5
        return max(0, min(100, base + bonus))

    @staticmethod
    def _determine_status(health_score: int) -> str:
        """
        Map health score to a status label.

            ≥ 75  → "Good"
            ≥ 40  → "Warning"
            < 40  → "Critical"
        """
        if health_score >= STATUS_GOOD_MIN:
            return "Good"
        elif health_score >= STATUS_WARNING_MIN:
            return "Warning"
        else:
            return "Critical"

    @staticmethod
    def _find_key(data: dict, candidates: list) -> str | None:
        """
        Return the first key from `candidates` that exists in `data`.
        Returns None if no candidate is found — callers handle this gracefully.
        """
        for key in candidates:
            if key in data:
                return key
        return None


# ─────────────────────────────────────────────────────────────────
# QUICK TEST – runs only when this file is executed directly
# ─────────────────────────────────────────────────────────────────

def _print_report(report: dict) -> None:
    """Pretty-print an analysis report."""
    print(f"  Health Score       : {report['health_score']}")
    print(f"  Status             : {report['status']}")
    print(f"  Failure Probability: {report['failure_probability']}%")
    print(f"  ML Anomaly Score   : {report['ml_anomaly_score']}")
    print(f"  Anomalies ({len(report['anomalies'])}):")
    if report["anomalies"]:
        for a in report["anomalies"]:
            print(f"      ⚠  {a}")
    else:
        print("      ✓  None")


if __name__ == "__main__":
    # Imports inside the guard — do NOT execute at import time
    from modules.simulator import VehicleSimulator
    from modules.fault_injector import FaultInjector

    simulator = VehicleSimulator()
    injector  = FaultInjector()
    analyzer  = VehicleAnalyzer()

    print("\n" + "=" * 60)
    print("  AutoSense — Live Simulation Test (10 cycles)")
    print("=" * 60)

    for i in range(10):
        print(f"\n--- Cycle {i + 1} ---")
        data   = simulator.get_next_data()
        result = injector.inject_fault(data)
        report = analyzer.analyze(result["data"], result["faults"])
        _print_report(report)
