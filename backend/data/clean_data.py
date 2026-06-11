"""
AutoSense – AI-Based Vehicle Health Monitoring System
Module  : Data Cleaning Script
File    : clean_data.py
Purpose : Cleans the raw OBD-II telemetry CSV dataset and saves the result.

Steps performed:
    1. Remove "()" characters from column names
    2. Replace spaces with underscores in column names
    3. Convert all column names to lowercase
    4. Fix typo: engine_run_tine → engine_run_time
    5. Replace negative values in engine_run_time with 0
    6. Save the cleaned dataset to a new CSV file
    7. Print first 5 rows and all column names
"""

import pandas as pd


# ─────────────────────────────────────────────
# STEP 1 – Load the raw dataset
# ─────────────────────────────────────────────
def load_dataset(filepath: str) -> pd.DataFrame:
    """
    Load the raw CSV file into a pandas DataFrame.

    Args:
        filepath (str): Full path to the raw CSV file.

    Returns:
        pd.DataFrame: Loaded DataFrame.
    """
    print(f"[INFO] Loading dataset from: {filepath}")
    df = pd.read_csv(filepath)
    print(f"[INFO] Dataset loaded successfully — {df.shape[0]} rows, {df.shape[1]} columns.\n")
    return df


# ─────────────────────────────────────────────
# STEP 2 – Clean column names
# ─────────────────────────────────────────────
def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean column names by:
        - Removing '(' and ')' characters
        - Replacing spaces with underscores
        - Converting to lowercase
        - Fixing the typo: engine_run_tine → engine_run_time

    Args:
        df (pd.DataFrame): DataFrame with raw column names.

    Returns:
        pd.DataFrame: DataFrame with cleaned column names.
    """
    print("[INFO] Cleaning column names...")

    # Remove parentheses characters
    df.columns = df.columns.str.replace(r"[()]", "", regex=True)

    # Replace spaces with underscores
    df.columns = df.columns.str.replace(" ", "_")

    # Convert to lowercase
    df.columns = df.columns.str.lower()

    # Fix known typo in column name
    df.columns = df.columns.str.replace("engine_run_tine", "engine_run_time")

    print("[INFO] Column names cleaned successfully.\n")
    return df


# ─────────────────────────────────────────────
# STEP 3 – Fix data values
# ─────────────────────────────────────────────
def fix_data_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fix invalid data values:
        - Replace negative values in 'engine_run_time' with 0
          (engine run time cannot be negative in real-world data)

    Args:
        df (pd.DataFrame): DataFrame after column name cleaning.

    Returns:
        pd.DataFrame: DataFrame with fixed values.
    """
    print("[INFO] Fixing data values...")

    if "engine_run_time" in df.columns:
        # Count how many negative values exist before fixing
        negative_count = (df["engine_run_time"] < 0).sum()
        print(f"  → Found {negative_count} negative value(s) in 'engine_run_time'. Replacing with 0.")

        # Replace negatives with 0
        df["engine_run_time"] = df["engine_run_time"].clip(lower=0)
    else:
        print("  → Column 'engine_run_time' not found. Skipping this step.")

    print("[INFO] Data values fixed successfully.\n")
    return df


# ─────────────────────────────────────────────
# STEP 4 – Save cleaned dataset
# ─────────────────────────────────────────────
def save_dataset(df: pd.DataFrame, output_path: str) -> None:
    """
    Save the cleaned DataFrame to a CSV file.

    Args:
        df (pd.DataFrame): Cleaned DataFrame.
        output_path (str): Full path for the output CSV file.
    """
    df.to_csv(output_path, index=False)
    print(f"[INFO] Cleaned dataset saved to: {output_path}\n")


# ─────────────────────────────────────────────
# STEP 5 – Print summary
# ─────────────────────────────────────────────
def print_summary(df: pd.DataFrame) -> None:
    """
    Print a summary of the cleaned dataset:
        - All column names
        - First 5 rows

    Args:
        df (pd.DataFrame): Cleaned DataFrame.
    """
    print("=" * 60)
    print("CLEANED COLUMN NAMES:")
    print("=" * 60)
    for i, col in enumerate(df.columns, start=1):
        print(f"  {i:>2}. {col}")

    print("\n" + "=" * 60)
    print("FIRST 5 ROWS OF CLEANED DATASET:")
    print("=" * 60)
    print(df.head().to_string(index=False))
    print("=" * 60)


# ─────────────────────────────────────────────
# MAIN – Orchestrates all steps
# ─────────────────────────────────────────────
def main():
    # File paths
    INPUT_PATH  = "C:/Users/hrish/AutoSense/backend/data/live2.csv"
    OUTPUT_PATH = "C:/Users/hrish/AutoSense/backend/data/cleaned_data.csv"

    # Run all cleaning steps in order
    df = load_dataset(INPUT_PATH)
    df = clean_column_names(df)
    df = fix_data_values(df)
    save_dataset(df, OUTPUT_PATH)
    print_summary(df)

    print("\n[DONE] Data cleaning complete.")


if __name__ == "__main__":
    main()
