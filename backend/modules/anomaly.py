"""
AutoSense – AI-Based Vehicle Health Monitoring System
Module  : Anomaly Detector
File    : anomaly.py
Path    : C:/Users/hrish/AutoSense/backend/modules/anomaly.py
Purpose : Trains a StandardScaler + Isolation Forest pipeline on normal
          vehicle telemetry data and uses it to detect abnormal readings
          in real-time telemetry rows.

How Isolation Forest works (simple explanation):
    - It randomly partitions the data into trees.
    - Anomalous points are "isolated" faster (shorter path in the tree).
    - A low anomaly score means the point is unusual / suspicious.
    - contamination=0.03 tells the model to expect ~3% anomalies.

Why StandardScaler?
    - Vehicle features have very different ranges:
        engine_rpm_  → 0–6000+   vs   fuel_air_ratio → 0.6–1.5
    - Without scaling, high-range features dominate the model and
      cause false positives on normal low-range variation.
    - StandardScaler transforms each feature to mean=0, std=1 so
      all features contribute equally to anomaly detection.

Anomaly decision threshold:
    - score < -0.1  → anomaly  (stricter than sklearn's default of 0)
    - score >= -0.1 → normal
    - This tighter threshold reduces false positives on borderline rows.

Usage:
    from modules.anomaly import AnomalyDetector

    detector = AnomalyDetector()
    result   = detector.predict(telemetry_row)

    print(result["is_anomaly"])   # True or False
    print(result["score"])        # float, lower = more anomalous
"""

import sys
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

DATASET_PATH = "C:/Users/hrish/AutoSense/backend/data/cleaned_data.csv"

# Features the model will be trained on and will expect at prediction time.
# These must match the column names in cleaned_data.csv exactly.
FEATURES = [
    "engine_rpm_",
    "vehicle_speed_",
    "coolant_temperature_",
    "engine_load_",
    "control_module_voltage_",
    "intake_air_temp_",
    "fuel_air_commanded_equiv_ratio_",
]

# Score threshold for anomaly decision.
# Rows with a decision_function score below this value are flagged as anomalies.
# Using -0.1 (stricter than sklearn's default of 0) reduces false positives
# on rows that are slightly unusual but not genuinely faulty.
ANOMALY_THRESHOLD = -0.1


# ─────────────────────────────────────────────────────────────────
# CLASS: AnomalyDetector
# ─────────────────────────────────────────────────────────────────

class AnomalyDetector:
    """
    Detects anomalous vehicle telemetry using a StandardScaler +
    Isolation Forest pipeline.

    The scaler and model are both fitted once during __init__ on the
    cleaned dataset. Every prediction input is scaled with the same
    scaler before being passed to the model, ensuring consistent and
    accurate anomaly scoring.

    Attributes:
        model         (IsolationForest) : Trained anomaly detection model.
        scaler        (StandardScaler)  : Fitted scaler (mean=0, std=1).
        features      (list[str])       : Feature column names used for training.
        feature_means (dict)            : Per-feature mean — fallback for missing
                                          columns in live data.
    """

    def __init__(
        self,
        filepath     : str   = DATASET_PATH,
        features     : list  = None,
        contamination: float = 0.03,   # reduced from 0.05 → fewer false positives
        random_state : int   = 42,
    ):
        """
        Load the dataset, fit the StandardScaler, and train the Isolation Forest.

        Training pipeline:
            raw data  →  StandardScaler (fit + transform)  →  IsolationForest (fit)

        Args:
            filepath      (str)  : Path to cleaned_data.csv.
            features      (list) : Column names to train on. Defaults to FEATURES.
            contamination (float): Expected proportion of anomalies (0–0.5).
                                   0.03 = model expects ~3 % of rows to be abnormal.
                                   Lower value → fewer false positives.
            random_state  (int)  : Seed for reproducibility.

        Raises:
            SystemExit  : If the CSV file is not found.
            ValueError  : If none of the required feature columns exist in the dataset.
        """
        self.features = features if features is not None else FEATURES

        # ── 1. Load dataset ───────────────────────────────────────
        print(f"[AnomalyDetector] Loading dataset from: {filepath}")
        try:
            df = pd.read_csv(filepath)
        except FileNotFoundError:
            print(f"[AnomalyDetector] ERROR: File not found at '{filepath}'.")
            print("[AnomalyDetector] Run clean_data.py first to generate the dataset.")
            sys.exit(1)

        # ── 2. Select only the features that exist in the CSV ─────
        # Some columns might be named slightly differently — we keep
        # only the ones that are actually present and warn about the rest.
        available_features = self._filter_available_features(df)

        if not available_features:
            raise ValueError(
                "[AnomalyDetector] ERROR: None of the required feature columns "
                f"were found in the dataset.\nExpected: {self.features}\n"
                f"Found   : {list(df.columns)}"
            )

        # Update self.features to only the columns we can actually use
        self.features = available_features

        # ── 3. Prepare training data ──────────────────────────────
        # Drop rows where any feature value is NaN to keep training clean
        train_df = df[self.features].dropna()

        print(f"[AnomalyDetector] Training on {len(train_df)} rows "
              f"using {len(self.features)} feature(s): {self.features}")

        # Store per-feature means — used as safe fallback for missing live data
        self.feature_means = train_df.mean().to_dict()

        # ── 4. Fit StandardScaler on training data ────────────────
        # StandardScaler transforms each feature to have mean=0 and std=1.
        # This prevents high-range features (like engine_rpm_ 0–6000) from
        # dominating over low-range features (like fuel_air_ratio 0.6–1.5),
        # which would otherwise cause the model to miss anomalies in
        # low-range features entirely.
        self.scaler = StandardScaler()
        scaled_train = self.scaler.fit_transform(train_df)  # fit AND transform training data

        print(f"[AnomalyDetector] Feature scaling applied (StandardScaler).")

        # ── 5. Train the Isolation Forest on scaled data ──────────
        # n_estimators=100  → number of trees (default, good balance)
        # contamination     → expected fraction of outliers (reduced to 0.03)
        # random_state      → ensures same result on every run
        self.model = IsolationForest(
            n_estimators  = 100,
            contamination = contamination,
            random_state  = random_state,
        )
        self.model.fit(scaled_train)   # train on SCALED data, not raw

        print("[AnomalyDetector] Model trained successfully.\n")

    # ─────────────────────────────────────────────────────────────
    # PUBLIC METHOD: predict
    # ─────────────────────────────────────────────────────────────

    def predict(self, data: dict) -> dict:
        """
        Predict whether a single telemetry row is anomalous.

        Prediction pipeline:
            raw input dict  →  feature vector  →  StandardScaler.transform()
                            →  decision_function()  →  threshold check

        Anomaly decision (threshold-based):
            score < -0.1  → is_anomaly = True   (clearly abnormal)
            score >= -0.1 → is_anomaly = False  (normal or borderline)

        Using a threshold of -0.1 instead of sklearn's default (0) means
        borderline rows are treated as normal, reducing false positives.

        Args:
            data (dict): A single telemetry row, e.g. from VehicleSimulator
                         or after fault injection.

        Returns:
            dict: {
                "is_anomaly" : bool  – True if anomalous, False if normal,
                "score"      : float – anomaly score (lower = more anomalous)
            }
        """
        # ── Build raw feature vector from the input dictionary ────
        feature_vector = self._build_feature_vector(data)

        # Wrap in a DataFrame so the scaler gets the right column names
        input_df = pd.DataFrame([feature_vector], columns=self.features)

        # ── Scale the input using the SAME scaler fitted on training data ──
        # Critical: we use transform() only (NOT fit_transform) so the
        # same mean/std from training is applied to live data.
        scaled_input = self.scaler.transform(input_df)

        # ── Compute anomaly score via decision_function ────────────
        # Returns a float: negative = anomalous, positive = normal.
        # We use this raw score instead of model.predict() because it gives
        # us fine-grained control over the anomaly threshold.
        score = self.model.decision_function(scaled_input)[0]

        # ── Apply custom threshold to decide anomaly status ───────
        # -0.1 is stricter than sklearn's default of 0:
        #   only rows with a clearly negative score are flagged.
        is_anomaly = score < ANOMALY_THRESHOLD

        return {
            "is_anomaly": bool(is_anomaly),       # native Python bool (JSON-safe)
            "score"     : round(float(score), 6), # native Python float (JSON-safe)
        }

    # ─────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────

    def _build_feature_vector(self, data: dict) -> list:
        """
        Extract feature values from the input dict in the correct order.

        If a feature key is missing from the incoming data (e.g. the
        simulator row doesn't have that column), the training-time mean
        for that feature is used as a safe neutral fallback — this avoids
        crashing on incomplete live data.

        Args:
            data (dict): Incoming telemetry row.

        Returns:
            list: Ordered list of feature values matching self.features.
        """
        vector = []
        for feature in self.features:
            if feature in data and data[feature] is not None:
                vector.append(float(data[feature]))
            else:
                # Use the training mean as a neutral substitute
                fallback = self.feature_means.get(feature, 0.0)
                print(f"[AnomalyDetector] WARNING: '{feature}' missing in input. "
                      f"Using training mean ({fallback:.2f}) as fallback.")
                vector.append(float(fallback))
        return vector

    def _filter_available_features(self, df: pd.DataFrame) -> list:
        """
        Return only the feature names from self.features that actually
        exist as columns in the given DataFrame.

        Logs a warning for any requested feature that is absent so the
        developer can spot column name mismatches quickly.

        Args:
            df (pd.DataFrame): The loaded dataset.

        Returns:
            list: Feature names present in the DataFrame.
        """
        available = []
        for feature in self.features:
            if feature in df.columns:
                available.append(feature)
            else:
                print(f"[AnomalyDetector] WARNING: Feature '{feature}' not found "
                      "in dataset — skipping.")
        return available


# ─────────────────────────────────────────────────────────────────
# QUICK TEST – runs only when this file is executed directly
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  AutoSense — AnomalyDetector Quick Test")
    print("=" * 60)

    detector = AnomalyDetector()

    # ── Test 1: Normal telemetry row ──────────────────────────────
    normal_row = {
        "engine_rpm_"                     : 1400.0,
        "vehicle_speed_"                  : 55.0,
        "coolant_temperature_"            : 88.0,
        "engine_load_"                    : 42.0,
        "control_module_voltage_"         : 14.1,
        "intake_air_temp_"                : 34.0,
        "fuel_air_commanded_equiv_ratio_" : 1.0,
    }

    # ── Test 2: Anomalous row (overheating + engine stress) ────────
    anomalous_row = {
        "engine_rpm_"                     : 6800.0,   # very high RPM
        "vehicle_speed_"                  : 145.0,    # overspeed
        "coolant_temperature_"            : 130.0,    # overheating
        "engine_load_"                    : 98.0,     # extreme load
        "control_module_voltage_"         : 9.2,      # battery drop
        "intake_air_temp_"                : 72.0,     # intake issue
        "fuel_air_commanded_equiv_ratio_" : 0.65,     # lean mixture
    }

    print("\n--- Test 1: Normal Row ---")
    result_normal = detector.predict(normal_row)
    print(f"  is_anomaly : {result_normal['is_anomaly']}")
    print(f"  score      : {result_normal['score']}")

    print("\n--- Test 2: Anomalous Row ---")
    result_anomaly = detector.predict(anomalous_row)
    print(f"  is_anomaly : {result_anomaly['is_anomaly']}")
    print(f"  score      : {result_anomaly['score']}")

    print("\n[DONE] AnomalyDetector test complete.")
