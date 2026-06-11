"""
AutoSense – AI-Based Vehicle Health Monitoring System
Module  : Anomaly Detector
File    : anomaly.py
Path    : C:/Users/hrish/AutoSense/backend/modules/anomaly.py
Purpose : Trains a StandardScaler + Isolation Forest pipeline on normal
          vehicle telemetry data and uses it to detect abnormal readings
          in real-time telemetry rows.
"""

import sys
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler



# CONSTANTS


DATASET_PATH = "C:/Users/hrish/AutoSense/backend/data/cleaned_data.csv"

FEATURES = [
    "engine_rpm_",
    "vehicle_speed_",
    "coolant_temperature_",
    "engine_load_",
    "control_module_voltage_",
    "intake_air_temp_",
    "fuel_air_commanded_equiv_ratio_",
]

ANOMALY_THRESHOLD = -0.1



# CLASS: AnomalyDetector


class AnomalyDetector:
    """
    Detects anomalous vehicle telemetry using a StandardScaler +
    Isolation Forest pipeline.

    Two prediction modes:
        predict()       – single row  (used by live /analyze endpoint)
        predict_batch() – all rows at once (used by /full-report for speed)

    Attributes:
        model         (IsolationForest) : Trained anomaly detection model.
        scaler        (StandardScaler)  : Fitted scaler (mean=0, std=1).
        features      (list[str])       : Feature column names used for training.
        feature_means (dict)            : Per-feature mean — fallback for missing columns.
    """

    def __init__(
        self,
        filepath     : str   = DATASET_PATH,
        features     : list  = None,
        contamination: float = 0.03,
        random_state : int   = 42,
    ):
        self.features = features if features is not None else FEATURES

        # ── 1. Load dataset ───────────────────────────────────────
        print(f"[AnomalyDetector] Loading dataset from: {filepath}")
        try:
            df = pd.read_csv(filepath)
        except FileNotFoundError:
            print(f"[AnomalyDetector] ERROR: File not found at '{filepath}'.")
            print("[AnomalyDetector] Run clean_data.py first to generate the dataset.")
            sys.exit(1)

        # ── 2. Select only features that exist in the CSV ─────────
        available_features = self._filter_available_features(df)

        if not available_features:
            raise ValueError(
                "[AnomalyDetector] ERROR: None of the required feature columns "
                f"were found in the dataset.\nExpected: {self.features}\n"
                f"Found   : {list(df.columns)}"
            )

        self.features = available_features

        # ── 3. Prepare training data ──────────────────────────────
        train_df = df[self.features].dropna()

        print(f"[AnomalyDetector] Training on {len(train_df)} rows "
              f"using {len(self.features)} feature(s): {self.features}")

        self.feature_means = train_df.mean().to_dict()

        # ── 4. Fit StandardScaler ─────────────────────────────────
        self.scaler = StandardScaler()
        scaled_train = self.scaler.fit_transform(train_df)

        print(f"[AnomalyDetector] Feature scaling applied (StandardScaler).")

        # ── 5. Train Isolation Forest ─────────────────────────────
        self.model = IsolationForest(
            n_estimators  = 100,
            contamination = contamination,
            random_state  = random_state,
        )
        self.model.fit(scaled_train)

        print("[AnomalyDetector] Model trained successfully.\n")

   
    # PUBLIC METHOD: predict  (single row — used by /analyze)
    

    def predict(self, data: dict) -> dict:
        """
        Predict whether a SINGLE telemetry row is anomalous.
        Used by the live dashboard (/analyze endpoint).

        Args:
            data (dict): A single telemetry row.

        Returns:
            dict: { "is_anomaly": bool, "score": float }
        """
        feature_vector = self._build_feature_vector(data)
        input_df       = pd.DataFrame([feature_vector], columns=self.features)
        scaled_input   = self.scaler.transform(input_df)
        score          = self.model.decision_function(scaled_input)[0]
        is_anomaly     = score < ANOMALY_THRESHOLD

        return {
            "is_anomaly": bool(is_anomaly),
            "score"     : round(float(score), 6),
        }

    
    # PUBLIC METHOD: predict_batch  (all rows at once — used by /full-report)
    
    def predict_batch(self, rows: list) -> list:
        """
        Predict anomaly scores for ALL rows in a single sklearn call.

        This is the key performance fix for the full report.
        Instead of calling predict() N times (very slow), we build one
        big DataFrame and score all rows at once (very fast — sklearn
        is vectorized and handles this in milliseconds).

        Args:
            rows (list): List of telemetry dicts — one dict per row.

        Returns:
            list: List of result dicts, one per input row.
                  Each dict: { "is_anomaly": bool, "score": float }

        Example:
            results = detector.predict_batch(all_rows)
            results[0]  →  { "is_anomaly": False, "score": 0.082 }
            results[99] →  { "is_anomaly": True,  "score": -0.134 }
        """
        if not rows:
            return []

        print(f"[AnomalyDetector] Running batch prediction on {len(rows)} rows...")

        # ── Build a feature matrix from all rows at once ──────────
        # Each row becomes one line in the DataFrame.
        # Missing columns are filled with the training mean (same as predict()).
        vectors = []
        for data in rows:
            vectors.append(self._build_feature_vector(data))

        # Shape: (N rows, M features)
        batch_df = pd.DataFrame(vectors, columns=self.features)

        # ── Scale ALL rows in one call ────────────────────────────
        scaled_batch = self.scaler.transform(batch_df)

        # ── Score ALL rows in one call ────────────────────────────
        # decision_function returns an array of N floats — one per row.
        # This is sklearn's vectorized operation — extremely fast.
        scores = self.model.decision_function(scaled_batch)

        # ── Convert scores array → list of result dicts ──────────
        results = []
        for score in scores:
            results.append({
                "is_anomaly": bool(score < ANOMALY_THRESHOLD),
                "score"     : round(float(score), 6),
            })

        print(f"[AnomalyDetector] Batch prediction complete.")
        return results

    
    # PRIVATE HELPERS
    

    def _build_feature_vector(self, data: dict) -> list:
        """
        Extract feature values from a single row dict in the correct order.
        Uses training mean as fallback for any missing column.
        """
        vector = []
        for feature in self.features:
            if feature in data and data[feature] is not None:
                vector.append(float(data[feature]))
            else:
                fallback = self.feature_means.get(feature, 0.0)
                vector.append(float(fallback))
        return vector

    def _filter_available_features(self, df: pd.DataFrame) -> list:
        """Return only the feature names that actually exist in the DataFrame."""
        available = []
        for feature in self.features:
            if feature in df.columns:
                available.append(feature)
            else:
                print(f"[AnomalyDetector] WARNING: Feature '{feature}' not found "
                      "in dataset — skipping.")
        return available



# QUICK TEST – runs only when this file is executed directly

if __name__ == "__main__":
    print("=" * 60)
    print("  AutoSense — AnomalyDetector Quick Test")
    print("=" * 60)

    detector = AnomalyDetector()

    normal_row = {
        "engine_rpm_"                     : 1400.0,
        "vehicle_speed_"                  : 55.0,
        "coolant_temperature_"            : 88.0,
        "engine_load_"                    : 42.0,
        "control_module_voltage_"         : 14.1,
        "intake_air_temp_"                : 34.0,
        "fuel_air_commanded_equiv_ratio_" : 1.0,
    }

    anomalous_row = {
        "engine_rpm_"                     : 6800.0,
        "vehicle_speed_"                  : 145.0,
        "coolant_temperature_"            : 130.0,
        "engine_load_"                    : 98.0,
        "control_module_voltage_"         : 9.2,
        "intake_air_temp_"                : 72.0,
        "fuel_air_commanded_equiv_ratio_" : 0.65,
    }

    print("\n--- Test 1: Single predict() ---")
    result_normal = detector.predict(normal_row)
    print(f"  Normal row    → is_anomaly: {result_normal['is_anomaly']}, score: {result_normal['score']}")

    print("\n--- Test 2: predict_batch() with 2 rows ---")
    batch_results = detector.predict_batch([normal_row, anomalous_row])
    print(f"  Row 1 (normal)    → is_anomaly: {batch_results[0]['is_anomaly']}, score: {batch_results[0]['score']}")
    print(f"  Row 2 (anomalous) → is_anomaly: {batch_results[1]['is_anomaly']}, score: {batch_results[1]['score']}")

    print("\n[DONE] AnomalyDetector test complete.")