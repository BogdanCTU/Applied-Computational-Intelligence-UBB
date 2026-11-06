# Skill: Canonical Dataset & Numerical Integrity Validation

## Objective
Provide an exhaustive pre-reporting verification checklist to ensure all datasets, aggregations, and visual elements are structurally and numerically sound before producing artifacts.

---

## 1. Pre-Report Verification Checklist
Before passing any data to the PDF or CSV reporting pipelines, verify every item:

1. **Row Count & Empty State**:
   - Verify `row_count > 0`. If a query returns 0 rows, check whether date filters were too narrow or table join keys mismatched.
   - Never generate an empty table or chart with 0 values without an explicit "No matching records found" message.
2. **Schema & Column Typing**:
   - Ensure numeric columns (e.g. `price`, `revenue`, `quantity`) contain numerical types (`int` or `float`), not string-encoded text.
   - Ensure categorical labels are non-null strings.
3. **Null Check & Fallbacks**:
   - Verify that critical dimension columns (e.g. `order_id`, `product_category_name`, `order_purchase_timestamp`) do not contain unexpected `NULL` values.
4. **Sum Reconciliation**:
   - Compute `SUM(column)` over individual rows and verify it matches the grand total displayed on executive summary cards or table footers.
5. **Percentage Bounding**:
   - Every individual percentage must satisfy: $0\% \le p \le 100\%$.
   - The sum of percentages across exhaustive categories must equal $100.0\% \pm 0.1\%$ (allowing for minor floating-point rounding).
6. **Date Range Sanity**:
   - Ensure all dates fall within the known dataset timeline (e.g. 2016 to 2018 for the e-commerce store).
   - Ensure `end_date >= start_date`.
7. **Chart and Table Parity**:
   - Confirm that the number of chart bars/slices matches the number of rows in the summary table.

---

## 2. Integrity Violations & Self-Correction
- **No Silent Manipulation**: If numbers fail reconciliation, NEVER alter row values in Python memory to force an artificial match.
- **Remediation Protocol**:
  1. Diagnose whether the issue was an unhandled join Cartesian product or incorrect `WHERE` filter.
  2. Regenerate the SQL query with appropriate `DISTINCT` or CTE aggregation.
  3. Re-run validation on the fresh dataset.

