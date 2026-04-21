"""
AutoSense – AI-Based Vehicle Health Monitoring System
Module  : Flask Backend API
File    : app.py
Purpose : Provides API endpoints to stream simulated vehicle data
          with injected faults and full health analysis.
"""

from flask import Flask, jsonify
from flask_cors import CORS

# Import modules
from modules.simulator import VehicleSimulator
from modules.fault_injector import FaultInjector
from modules.analysis import VehicleAnalyzer       # ← NEW


# ─────────────────────────────────────────────
# APP INITIALIZATION
# ─────────────────────────────────────────────

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for React frontend


# ─────────────────────────────────────────────
# MODULE INITIALIZATION
# ─────────────────────────────────────────────

print("[App] Initializing AutoSense backend...")

simulator     = VehicleSimulator()
fault_injector = FaultInjector()
analyzer      = VehicleAnalyzer()               # ← NEW: init once, reuse across requests
                                                #   (keeps trend history alive between calls)

print("[App] Initialization complete.\n")


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.route("/simulate", methods=["GET"])
def simulate():
    """
    Endpoint: GET /simulate

    Returns raw simulated telemetry with injected faults.
    No analysis is performed here — use /analyze for the full pipeline.

    Workflow:
        1. Get next row of simulated vehicle data
        2. Inject random faults
        3. Return JSON response

    Response:
        {
            "data"  : { ...telemetry fields... },
            "faults": [ "FaultName", ... ]
        }
    """
    try:
        # Step 1: Get next simulated telemetry row
        data = simulator.get_next_data()

        # Step 2: Inject random faults into the row
        result = fault_injector.inject_fault(data)

        # Step 3: Return raw data + fault list
        return jsonify({
            "data"  : result["data"],
            "faults": result["faults"]
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/analyze", methods=["GET"])
def analyze():
    """
    Endpoint: GET /analyze

    Full AutoSense pipeline — simulation → fault injection → health analysis.

    Workflow:
        1. Get next row from VehicleSimulator
        2. Pass data through FaultInjector
        3. Pass faulted data to VehicleAnalyzer
        4. Return combined response

    Response:
        {
            "data"  : { ...telemetry fields... },
            "faults": [ "FaultName", ... ],
            "analysis": {
                "health_score"        : 0–100,
                "anomalies"           : [ "description", ... ],
                "failure_probability" : 0–100,
                "status"              : "Good" | "Warning" | "Critical",
                "ml_anomaly_score"    : float
            }
        }
    """
    try:
        # Step 1: Simulate — get next telemetry row from the dataset
        raw_data = simulator.get_next_data()

        # Step 2: Inject — randomly introduce faults into the telemetry
        fault_result = fault_injector.inject_fault(raw_data)
        faulted_data = fault_result["data"]
        faults       = fault_result["faults"]

        # Step 3: Analyze — run rule-based checks + ML + trend analysis
        # NOTE: analyzer is a module-level instance so trend history
        #       (temp_history, rpm_history) persists across API calls.
        analysis_report = analyzer.analyze(faulted_data, faults)

        # Step 4: Return the full combined response
        return jsonify({
            "data"    : faulted_data,
            "faults"  : faults,
            "analysis": analysis_report
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# MAIN ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("[App] Starting Flask server on http://127.0.0.1:5000")
    app.run(debug=True, port=5000)
