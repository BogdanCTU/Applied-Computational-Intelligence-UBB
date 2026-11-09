# Skill: E-Commerce Data Analysis & Metric Definitions

## Objective
Provide authoritative domain guidance, metric definitions, and aggregation grain rules for analyzing the synthetic e-commerce dataset without hallucination or double-counting.

---

## 1. Domain Truth: Metric Definitions
Never guess business formulas. Always apply the following standardized definitions:

1. **Total Revenue (Net Product Sales)**:
   - Formula: `SUM(order_items.price)`
   - Note: Excludes shipping freight (`freight_value`) and refunds.
2. **Gross Merchandise Value (GMV)**:
   - Formula: `SUM(order_items.price + order_items.freight_value)`
   - Note: Total transaction value including freight charges.
3. **Average Order Value (AOV)**:
   - Formula: `SUM(order_items.price) / COUNT(DISTINCT orders.order_id)`
   - Note: Always use `DISTINCT orders.order_id` in the denominator to avoid item line count inflation.
4. **Order Volume**:
   - Formula: `COUNT(DISTINCT orders.order_id)`
5. **Customer Count**:
   - Formula: `COUNT(DISTINCT orders.customer_id)`
6. **Units Sold**:
   - Formula: `COUNT(order_items.order_item_id)`
7. **Return Rate**:
   - Formula: `COUNT(DISTINCT returns.order_id) * 100.0 / COUNT(DISTINCT orders.order_id)`

---

## 2. Preventing Multi-Table Join Double Counting
- **The Payment / Order Fan-Out**: An order may have multiple payment installments or payment types (voucher + credit card). Joining `orders` with `payments` AND `order_items` creates an N:M Cartesian product:
  - If Order 1 has 2 items and 2 payment records, an unconstrained join produces 4 rows! Summing `price` on that result multiplies revenue by 2x!
- **Solution**: Aggregate payments and order items in separate CTEs before joining:
  ```sql
  WITH item_totals AS (
      SELECT order_id, SUM(price) AS items_revenue
      FROM order_items
      GROUP BY order_id
  ),
  payment_totals AS (
      SELECT order_id, SUM(payment_value) AS total_paid
      FROM payments
      GROUP BY order_id
  )
  SELECT o.order_id, i.items_revenue, p.total_paid
  FROM orders o
  JOIN item_totals i ON o.order_id = i.order_id
  LEFT JOIN payment_totals p ON o.order_id = p.order_id;
  ```

---

## 3. Explicit Aggregation Grain
Every analytical result must specify its exact dimension grain:
- **Temporal Grain**: Daily (`YYYY-MM-DD`), Monthly (`YYYY-MM`), Quarterly, or Annual.
- **Entity Grain**: By Product Category (`product_category_name`), Customer Geography (`customer_state`), or Seller.
- Ensure that summary totals equal the sum of grain partitions.

