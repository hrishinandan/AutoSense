"""
AutoSense – AI-Based Vehicle Health Monitoring System
Module  : Vehicle Data Simulator
File    : simulator.py
Path    : C:/Users/hrish/AutoSense/backend/modules/simulator.py
Purpose : Simulates real-time vehicle telemetry by reading one row at a time
          from the cleaned OBD-II CSV dataset, mimicking a live data stream.
"""

import sys
import time
import pandas as pd


# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

# Path to the cleaned dataset produced by clean_data.py
DATASET_PATH = "C:/Users/hrish/AutoSense/backend/data/cleaned_data.csv"


# ─────────────────────────────────────────────────────────────────
# CLASS: VehicleSimulator
# ─────────────────────────────────────────────────────────────────

class VehicleSimulator:
    """
    Simulates a real-time vehicle telemetry data stream.

    Reads the cleaned OBD-II CSV dataset row by row and returns
    each row as a plain Python dictionary. When the end of the
    dataset is reached, it automatically loops back to the start
    so the simulation runs continuously.

    Attributes:
        dataset (pd.DataFrame): The full telemetry dataset loaded from CSV.
        index   (int)          : Pointer to the current row being served.
    """

    def __init__(self, filepath: str = DATASET_PATH):
        """
        Initialize the simulator by loading the cleaned CSV dataset.

        Args:
            filepath (str): Path to the cleaned CSV file.
                            Defaults to the project-level constant DATASET_PATH.

        Raises:
            SystemExit  : If the CSV file is not found at the given path.
            ValueError  : If the loaded dataset contains no rows.
        """
        print(f"[Simulator] Loading dataset from: {filepath}")

        # ── Load CSV ──────────────────────────────────────────────
        try:
            self.dataset = pd.read_csv(filepath)
        except FileNotFoundError:
            # Cannot proceed without data — print a clear message and exit
            print(f"[Simulator] ERROR: Dataset file not found at '{filepath}'.")
            print("[Simulator] Please run clean_data.py first to generate the cleaned dataset.")
            sys.exit(1)

        # ── NOTE: No row filtering is applied here ────────────────
        # The full dataset is kept intact so every recorded telemetry
        # reading (including idle, low-speed, and stop events) is
        # streamed to the dashboard exactly as it was captured.
        # Filtering was removed because it silently dropped large
        # portions of real data, causing inaccurate dashboard readings.

        # ── Validate dataset is not empty ─────────────────────────
        if self.dataset.empty:
            raise ValueError(
                "[Simulator] ERROR: The dataset is empty. "
                "Check your CSV file and re-run the cleaning script."
            )

        # ── Initialize the row pointer ────────────────────────────
        self.index = 0

        print(f"[Simulator] Dataset loaded — {len(self.dataset)} rows, "
              f"{len(self.dataset.columns)} columns.")
        print(f"[Simulator] Columns: {list(self.dataset.columns)}\n")

    # ─────────────────────────────────────────────────────────────
    # METHOD: get_next_data
    # ─────────────────────────────────────────────────────────────

    def get_next_data(self) -> dict:
        """
        Return the next row of telemetry data as a plain Python dictionary.

        Behaviour:
            - Reads the row at the current index position.
            - Converts all numpy scalar types (e.g. np.int64, np.float64)
              to native Python types so the result is JSON-serializable.
            - Increments the index pointer after each call.
            - Automatically resets to row 0 when the end of the dataset
              is reached, creating a continuous loop.

        Returns:
            dict: A single row of vehicle telemetry data.
                  Example:
                  {
                      "engine_rpm_"          : 1200,
                      "vehicle_speed_"       : 45,
                      "coolant_temperature_" : 90,
                      ...
                  }
        """
        # ── Optional: uncomment the line below to add a 1-second
        #    delay between rows, simulating real-time data arrival.
        # time.sleep(1)

        # ── Loop back to start if we've passed the last row ───────
        if self.index >= len(self.dataset):
            print("[Simulator] End of dataset reached. Looping back to row 0.")
            self.index = 0

        # ── Extract the current row as a dictionary ───────────────
        raw_row = self.dataset.iloc[self.index].to_dict()

        # ── Convert numpy types → native Python types ─────────────
        # pandas/numpy uses its own scalar types (np.int64, np.float64, etc.)
        # which are NOT natively JSON-serializable. We convert each value
        # to int or float so Flask's jsonify() works without errors.
        clean_row = {}
        for key, value in raw_row.items():
            if hasattr(value, "item"):
                # .item() is a numpy method that returns the native Python scalar
                clean_row[key] = value.item()
            else:
                clean_row[key] = value

        # ── NOTE: No value capping is applied here ────────────────
        # Raw values are passed through unchanged so the fault injector
        # and analyzer receive accurate data. Speed limiting was removed
        # because it silently modified real sensor values before analysis,
        # masking genuine overspeed events on the dashboard.

        # ── Advance the pointer to the next row ───────────────────
        self.index += 1

        return clean_row

    # ─────────────────────────────────────────────────────────────
    # METHOD: reset_simulation
    # ─────────────────────────────────────────────────────────────

    def reset_simulation(self) -> None:
        """
        Reset the simulation back to the beginning of the dataset.

        Useful when you want to restart the telemetry stream without
        creating a new VehicleSimulator instance (e.g., via an API call).
        """
        self.index = 0
        print("[Simulator] Simulation reset. Starting from row 0.")

    # ─────────────────────────────────────────────────────────────
    # METHOD: get_current_index
    # ─────────────────────────────────────────────────────────────

    def get_current_index(self) -> int:
        """
        Return the current row index position.

        Useful for debugging or tracking simulation progress via the API.

        Returns:
            int: The index of the next row that will be returned
                 by get_next_data().
        """
        return self.index


# ─────────────────────────────────────────────────────────────────
# QUICK TEST – runs only when this file is executed directly
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  AutoSense — VehicleSimulator Quick Test")
    print("=" * 55)

    sim = VehicleSimulator()

    # Fetch and display 5 consecutive rows
    for i in range(1, 6):
        row = sim.get_next_data()
        print(f"\n[Row {i}] Index before fetch: {sim.get_current_index() - 1}")
        for key, value in row.items():
            print(f"    {key:<35} : {value}")

    # Test reset
    print("\n--- Testing reset_simulation() ---")
    sim.reset_simulation()
    print(f"Current index after reset: {sim.get_current_index()}")
