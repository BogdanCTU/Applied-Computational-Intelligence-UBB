import pandas as pd
import re
import math

TABLE_NAME = "PreProcessedDataset"

# -----------------------------
# 1. DOMAIN TYPE CONTRACT
# -----------------------------
INT_COLUMNS = {
    "cast_in_row",
    "steel_weight_tonn",
    "steel_temperature_grab1_celsius_deg",
    "resistance_tonn",
    "swing_frequency_amount_minute",
    "crystallizer_movement_mm",
    "alloy_speed_meter_minute",
    "water_consumption_liter_minute",
    "water_temperature_delta_celsius_deg",
    "temperature_measurement1_celsius_deg",
    "temperature_measurement2_celsius_deg",
    "sleeve",
    "num_crystallizer",
    "num_stream",
    "calculated_rul_tons",
    "rul_percentage",
    "rul_class_encoded",
    "cast_in_row_encoded",
    "steel_weight_tonn_encoded",
    "steel_temperature_grab1_celsius_deg_encoded",
    "resistance_tonn_encoded",
    "swing_frequency_amount_minute_encoded",
    "crystallizer_movement_mm_encoded",
    "alloy_speed_meter_minute_encoded",
    "water_consumption_liter_minute_encoded",
    "water_temperature_delta_celsius_deg_encoded",
    "temperature_measurement1_celsius_deg_encoded",
    "temperature_measurement2_celsius_deg_encoded",
    "num_crystallizer_encoded",
    "num_stream_encoded"
}

DATETIME_COLUMNS = {"datetime_combined"}

# -----------------------------
# 2. UTILITIES
# -----------------------------
def sanitize_column(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^\w]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")

def sql_escape(value):
    if value is None:
        return "NULL"
    if isinstance(value, float) and math.isnan(value):
        return "NULL"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)

def format_datetime(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "NULL"
    dt = pd.to_datetime(value, errors="coerce")
    if pd.isna(dt):
        return "NULL"
    return f"'{dt.strftime('%Y-%m-%d %H:%M:%S')}'"

def cast_value(col, value):
    col = col.lower()

    if col in DATETIME_COLUMNS:
        return format_datetime(value)

    if col in INT_COLUMNS:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return "NULL"
        try:
            return str(int(float(value)))
        except:
            return "NULL"

    return sql_escape(value)

# -----------------------------
# 3. MAIN PIPELINE
# -----------------------------
def main():
    csv_file = "Final_Processed_Steel_Data_Clean.csv"
    df = pd.read_csv(csv_file)

    df.columns = [sanitize_column(c) for c in df.columns]

    output_sql = csv_file.replace(".csv", "_Full.sql")

    with open(output_sql, "w", encoding="utf-8") as f:

        # -------------------------
        # TABLE DDL (controlled schema)
        # -------------------------
        f.write(f"CREATE TABLE {TABLE_NAME} (\n")

        schema_lines = []

        for col in df.columns:
            col_l = col.lower()

            if col_l in DATETIME_COLUMNS:
                dtype = "DATETIME"
            elif col_l in INT_COLUMNS:
                dtype = "INT"
            else:
                dtype = "VARCHAR(255)"

            schema_lines.append(f"    {col} {dtype}")

        f.write(",\n".join(schema_lines))
        f.write("\n);\n\n")

        # -------------------------
        # DATA INSERTS
        # -------------------------
        for _, row in df.iterrows():
            values = ", ".join(
                cast_value(col, val) for col, val in zip(df.columns, row.values)
            )
            f.write(f"INSERT INTO {TABLE_NAME} VALUES ({values});\n")

    print(f"Generated SQL file: {output_sql}")


if __name__ == "__main__":
    main()