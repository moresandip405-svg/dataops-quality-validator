import duckdb
import pandas as pd
import numpy as np

class DataQualityValidator:
    def __init__(self, baseline_df: pd.DataFrame, current_df: pd.DataFrame):
        self.baseline_df = baseline_df
        self.current_df = current_df
        self.con = duckdb.connect(database=":memory:")
        self.con.register("baseline_table", baseline_df)
        self.con.register("current_table", current_df)

    def check_schema_drift(self) -> dict:
        baseline_cols = set(self.baseline_df.columns)
        current_cols = set(self.current_df.columns)

        missing_cols = list(baseline_cols - current_cols)
        added_cols = list(current_cols - baseline_cols)
        common_cols = list(baseline_cols.intersection(current_cols))

        type_mismatches = {}
        for col in common_cols:
            base_type = str(self.baseline_df[col].dtype)
            curr_type = str(self.current_df[col].dtype)
            if base_type != curr_type:
                type_mismatches[col] = {"expected": base_type, "actual": curr_type}

        return {
            "missing_columns": missing_cols,
            "new_columns": added_cols,
            "type_mismatches": type_mismatches,
            "has_drift": bool(missing_cols or added_cols or type_mismatches)
        }

    def check_null_spikes(self, threshold=0.10) -> list:
        null_issues = []
        for col in self.current_df.columns:
            curr_null_pct = self.current_df[col].isnull().mean()
            if col in self.baseline_df.columns:
                base_null_pct = self.baseline_df[col].isnull().mean()
                delta = curr_null_pct - base_null_pct
                if delta > threshold:
                    null_issues.append({
                        "column": col,
                        "baseline_null_pct": round(base_null_pct * 100, 2),
                        "current_null_pct": round(curr_null_pct * 100, 2),
                        "delta_pct": round(delta * 100, 2)
                    })
        return null_issues

    def check_volume_anomalies(self) -> dict:
        base_rows = len(self.baseline_df)
        curr_rows = len(self.current_df)
        pct_change = ((curr_rows - base_rows) / base_rows) * 100 if base_rows > 0 else 0

        return {
            "baseline_rows": base_rows,
            "current_rows": curr_rows,
            "pct_change": round(pct_change, 2),
            "is_anomaly": abs(pct_change) > 30.0
        }

    def compute_health_score(self) -> int:
        drift = self.check_schema_drift()
        nulls = self.check_null_spikes()
        vol = self.check_volume_anomalies()

        score = 100
        if drift["missing_columns"]:
            score -= 25
        if drift["type_mismatches"]:
            score -= 20
        if drift["new_columns"]:
            score -= 5
        score -= min(len(nulls) * 10, 30)
        if vol["is_anomaly"]:
            score -= 15

        return max(score, 0)