# Skill: Executive Report Design & Visualization

## Objective
Guide the agent in structuring, formatting, and generating professional PDF and CSV reports while maintaining strict numerical synchronization between text, tables, and vector charts.

---

## 1. Single Source of Truth (`CanonicalSQLDataset`)
- All numbers, summary metrics, tables, and charts in a generated report must derive strictly from the exact same `CanonicalSQLDataset` instance.
- **Forbidden Inconsistencies**:
  - Never query two different datasets with diverging date filters for table vs chart.
  - Never fabricate or extrapolate missing numbers.
  - Never silently drop non-zero categories to make a chart look cleaner.

---

## 2. Visual Hierarchy & Report Structure
1. **Header Block**: Document title, subtitle, authoring timestamp, and data scope boundaries.
2. **Executive Summary**: 2-4 sentences summarizing findings, highest performing segment, and key changes.
3. **Key Performance Indicators (KPIs)**:
   - Primary metric (e.g. Total Revenue: `$1,245,600.00`).
   - Secondary comparison metric (e.g. Total Orders, AOV).
4. **Visual Chart Section**: A vector chart directly illustrating the table breakdown.
5. **Detailed Data Table**: Explicit column headers, formatted numbers, right-aligned monetary values, and a bold reconciliation `Total` row.

---

## 3. Chart Selection & Eligibility Criteria
- **Historical Bar / Line Charts**:
  - Exclusively for chronological time-series trends (`month`, `date`, `quarter`).
  - Must contain **at least 2 distinct time periods** (`>= 2` months/dates). Never generate a historical trend chart with only 1 month.
- **Bar Charts (Horizontal / Vertical)**:
  - Best for comparing discrete categories (e.g. Revenue by Channel, Payment Method, Order Status, Product Category).
  - Use vertical bars for few categories (< 8), horizontal bars for long category names.
- **Pie / Donut Charts**:
  - Strictly limited to parts-of-a-whole categorical distributions (e.g. Share by Channel, Payment Method, or Order Status).
  - Must contain **at least 2 positive categories** (`2..8` slices). Never generate a single-slice (`100.0%`) pie chart or a pie chart over a single month.
- **Performance Matrices / Heatmaps**:
  - Must contain **at least 2 rows** (or two categorical dimensions such as `Channel x Order Status`). Never render a 1-row matrix.
- **Dataset & Table Hygiene**:
  - Always pass `rows` as a list of row lists (`list[list[Any]]`) or row dicts (`list[dict[str, Any]]`) matching `columns` — never pass a list of column-name strings as `rows`.
  - Exclude intermediate metadata probes (`MIN/MAX(order_date)`), empty intermediate query attempts, and duplicate datasets from the final PDF.
  - Never horizontally sum heterogeneous columns (e.g. `Order Count + Sales + Revenue`) into a row `"Total"` column.

---

## 4. Number & Currency Formatting Standards
- **Currency**: Prefix with currency symbol and format with thousand separators and 2 decimal places: `$1,420,500.50`.
- **Counts / Volumes**: Format with thousand separators and 0 decimal places: `12,450 orders`.
- **Percentages**: Format with 1 or 2 decimals: `14.2%`.
- **Dates**: Use unambiguous ISO or short text: `2023-10-15` or `Oct 2023`.
- **Missing Data**: Display explicitly as `N/A` or `-`, never as empty blank space or fabricated zero.

