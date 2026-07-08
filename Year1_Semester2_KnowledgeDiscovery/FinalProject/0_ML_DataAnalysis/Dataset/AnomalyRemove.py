import pandas as pd
from sklearn.ensemble import IsolationForest


class DataCleaner:
    """
    A class used to detect and remove extreme outliers from a dataset
    using the Isolation Forest algorithm.
    """

    def __init__(self, file_path: str):
        """
        Initializes the cleaner by loading the dataset from a CSV file.
        """
        self.data = pd.read_csv(file_path)
        self.cleaned_data = None

    def remove_outliers(self, target_outliers_count: int = 3) -> pd.DataFrame:
        """
        Identifies and removes a specific number of extreme outliers
        from the numeric columns of the dataset.
        """
        # Select only numeric columns for mathematical anomaly detection
        numeric_data = self.data.select_dtypes(include=['number'])

        # Calculate contamination rate based on the requested number of outliers
        contamination_rate = target_outliers_count / len(self.data)

        # Initialize and fit the Isolation Forest model
        model = IsolationForest(contamination=contamination_rate, random_state=42)
        outlier_predictions = model.fit_predict(numeric_data)

        # Filter rows where the prediction is not -1 (outliers are labeled as -1)
        is_inlier = outlier_predictions != -1
        self.cleaned_data = self.data[is_inlier]

        # Output the rows that were classified as extreme values
        outliers = self.data[~is_inlier]
        print(f"Removed {len(outliers)} extreme rows.")

        return self.cleaned_data


# This block executes when the file is run directly from the command line
if __name__ == "__main__":
    # Initialize the cleaner with the main steel dataset file
    cleaner = DataCleaner("Final_Processed_Steel_Data.csv")

    # Remove the 3 most extreme outlier rows
    cleaned_df = cleaner.remove_outliers(target_outliers_count=3)

    # Save the clean data to a brand new CSV file
    cleaned_df.to_csv("Final_Processed_Steel_Data_Clean.csv", index=False)
    print("Cleaned dataset saved as 'Final_Processed_Steel_Data_Clean.csv'")