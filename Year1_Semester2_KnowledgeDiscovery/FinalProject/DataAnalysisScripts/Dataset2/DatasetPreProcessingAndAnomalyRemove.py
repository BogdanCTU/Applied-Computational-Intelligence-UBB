import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest


class IndustrialDataProcessor:
    """
    Preprocesses steel factory production logs, calculates Remaining Useful Life (RUL),
    performs feature binning and encoding, and removes extreme outliers using
    Isolation Forest.
    """

    def process_steel_data(
        self,
        input_csv_path: str,
        output_csv_path: str,
        target_outliers_count: int = 3
    ) -> pd.DataFrame:
        """
        Loads the raw dataset, performs preprocessing, removes outliers,
        and saves the cleaned dataset.

        Parameters
        ----------
        input_csv_path : str
            Path to the raw input CSV.

        output_csv_path : str
            Path to save the final cleaned CSV.

        target_outliers_count : int, default=3
            Number of extreme outliers to remove.

        Returns
        -------
        pd.DataFrame
            Fully processed and cleaned dataset.
        """

        # ---------------------------------------------------------------------
        # Load dataset
        # ---------------------------------------------------------------------
        df = pd.read_csv(input_csv_path, dtype={"sleeve": str})

        # ---------------------------------------------------------------------
        # Timeline reconstruction
        # ---------------------------------------------------------------------
        df["datetime_combined"] = pd.to_datetime(
            df["date"] + " " + df["sample_time_continuous_caster"]
        )

        df = (
            df.sort_values(["sleeve", "datetime_combined"])
            .reset_index(drop=True)
        )

        # ---------------------------------------------------------------------
        # Calculate Remaining Useful Life (RUL)
        # ---------------------------------------------------------------------
        df["steel_weight, tonn"] = df["steel_weight, tonn"].fillna(0.0)

        df["cumulative_tons"] = (
            df.groupby("sleeve")["steel_weight, tonn"]
            .cumsum()
        )

        max_tons_per_sleeve = (
            df.groupby("sleeve")["cumulative_tons"]
            .transform("max")
        )

        df["calculated_RUL_tons"] = (
            max_tons_per_sleeve - df["cumulative_tons"]
        )

        df["RUL_percentage"] = np.where(
            max_tons_per_sleeve > 0,
            (df["calculated_RUL_tons"] / max_tons_per_sleeve) * 100.0,
            0.0,
        )

        # ---------------------------------------------------------------------
        # Keep only required columns
        # ---------------------------------------------------------------------
        keep_columns = [
            "datetime_combined",
            "steel_type",
            "cast_in_row",
            "workpiece_slice_geometry",
            "alloy_type",
            "steel_weight, tonn",
            "steel_temperature_grab1, Celsius deg.",
            "resistance, tonn",
            "swing_frequency, amount/minute",
            "crystallizer_movement, mm",
            "alloy_speed, meter/minute",
            "water_consumption, liter/minute",
            "water_temperature_delta, Celsius deg.",
            "temperature_measurement1, Celsius deg.",
            "temperature_measurement2, Celsius deg.",
            "sleeve",
            "num_crystallizer",
            "num_stream",
            "calculated_RUL_tons",
            "RUL_percentage",
        ]

        valid_columns = [c for c in keep_columns if c in df.columns]
        df = df[valid_columns].copy()

        # ---------------------------------------------------------------------
        # FCA (Failure Classification Analysis) bins
        # ---------------------------------------------------------------------
        rul_bins = [-float("inf"), 25.0, 50.0, 75.0, float("inf")]
        rul_labels = ["Critical", "Low", "Medium", "Healthy"]

        df["FCA_BIN"] = pd.cut(
            df["RUL_percentage"],
            bins=rul_bins,
            labels=rul_labels,
        )

        rul_encoding = {
            "Critical": 0,
            "Low": 1,
            "Medium": 2,
            "Healthy": 3,
        }

        df["FCA_ENCODED"] = df["FCA_BIN"].map(rul_encoding)

        # ---------------------------------------------------------------------
        # Three-level binning for remaining numeric features
        # ---------------------------------------------------------------------
        exclude = [
            "datetime_combined",
            "steel_type",
            "workpiece_slice_geometry",
            "alloy_type",
            "sleeve",
            "calculated_RUL_tons",
            "RUL_percentage",
            "FCA_BIN",
            "FCA_ENCODED",
        ]

        for col in df.columns:

            if (
                col not in exclude
                and pd.api.types.is_numeric_dtype(df[col])
            ):

                if df[col].isna().all():
                    df[col] = 0.0
                else:
                    df[col] = df[col].fillna(df[col].mean())

                if df[col].nunique() > 1:

                    df[f"{col}_BIN"] = pd.cut(
                        df[col],
                        bins=3,
                        labels=["Low", "Medium", "High"],
                    )

                    df[f"{col}_ENCODED"] = (
                        df[f"{col}_BIN"]
                        .map({"Low": 0, "Medium": 1, "High": 2})
                    )

                else:

                    df[f"{col}_BIN"] = "Low"
                    df[f"{col}_ENCODED"] = 0

        # ---------------------------------------------------------------------
        # Outlier removal using Isolation Forest
        # ---------------------------------------------------------------------
        numeric_data = df.select_dtypes(include=["number"])

        contamination_rate = target_outliers_count / len(df)

        model = IsolationForest(
            contamination=contamination_rate,
            random_state=42,
        )

        predictions = model.fit_predict(numeric_data)

        inliers = predictions != -1

        removed_rows = (~inliers).sum()

        df = df[inliers].reset_index(drop=True)

        print(f"Removed {removed_rows} extreme outlier rows.")

        # ---------------------------------------------------------------------
        # Save final cleaned dataset
        # ---------------------------------------------------------------------
        df.to_csv(output_csv_path, index=False)

        print(f"Processed dataset saved to '{output_csv_path}'")

        return df


if __name__ == "__main__":

    processor = IndustrialDataProcessor()

    final_df = processor.process_steel_data(
        input_csv_path="Dataset.csv",
        output_csv_path="Final_Processed_Steel_Data_Clean.csv",
        target_outliers_count=3,
    )