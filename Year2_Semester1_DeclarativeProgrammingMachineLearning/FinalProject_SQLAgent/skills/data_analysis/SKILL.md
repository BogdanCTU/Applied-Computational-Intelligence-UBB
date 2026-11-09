# Skill: E-Commerce Data Analysis & Metric Definitions

## Objective
Provide authoritative domain guidance, metric definitions, and aggregation grain rules for analyzing the synthetic e-commerce dataset without hallucination or double-counting.

---

## 1. Domain Truth: Metric Definitions
Never guess business formulas. Always apply the following standardized definitions on `data/ecommerce.db`:

1. **Total Revenue**:
   - Formula: `SUM(orders.total_amount)` (or `SUM(order_items.line_total)` when analyzing by product/category)
2. **Gross Sales (Subtotal before discounts/tax/shipping)**:
   - Formula: `SUM(orders.subtotal)`
3. **Average Order Value (AOV)**:
   - Formula: `ROUND(AVG(orders.total_amount), 2)` or `SUM(orders.total_amount) / COUNT(DISTINCT orders.order_id)`
   - Note: Always use `DISTINCT orders.order_id` in the denominator to avoid item line count inflation.
4. **Order Volume (`orders_count`)**:
   - Formula: `COUNT(DISTINCT orders.order_id)`
5. **Transactions Count (`transactions_count`)**:
   - Formula: `COUNT(DISTINCT payments.payment_id)` joined via `LEFT JOIN payments p ON o.order_id = p.order_id`
6. **Customer Count**:
   - Formula: `COUNT(DISTINCT orders.customer_id)`
7. **Units Sold**:
   - Formula: `SUM(order_items.quantity)`
8. **Return Rate**:
   - Formula: `COUNT(DISTINCT returns.order_id) * 100.0 / COUNT(DISTINCT orders.order_id)`

---

## 2. Preventing Multi-Table Join Double Counting
- **The Payment / Order Item Fan-Out**: Joining `orders` with `payments` AND `order_items` in a flat query creates an N:M Cartesian product that inflates `SUM(total_amount)` or `SUM(line_total)`.
- **Solution**: For order- and payment-level metrics (`orders_count`, `sales_amount`, `total_revenue`, `transactions_count`), query `orders o LEFT JOIN payments p ON o.order_id = p.order_id` (since payments are 1:1 or aggregate `COUNT(DISTINCT p.payment_id)`), or aggregate in separate CTEs before joining:
  ```sql
  WITH item_totals AS (
      SELECT order_id, SUM(line_total) AS items_revenue
      FROM order_items
      GROUP BY order_id
  ),
  payment_totals AS (
      SELECT order_id, COUNT(DISTINCT payment_id) AS transactions_count, SUM(amount) AS total_paid
      FROM payments
      GROUP BY order_id
  )
  SELECT o.order_id, o.subtotal, o.total_amount, i.items_revenue, p.transactions_count
  FROM orders o
  LEFT JOIN item_totals i ON o.order_id = i.order_id
  LEFT JOIN payment_totals p ON o.order_id = p.order_id;
  ```

---

## 3. Explicit Aggregation Grain
Every analytical result must specify its exact dimension grain:
- **Temporal Grain**: Daily (`o.order_date`), Monthly (`strftime('%Y-%m', o.order_date) AS month`), Quarterly, or Annual.
- **Entity Grain**: By Order Channel (`o.channel`), Order Status (`o.status`), Product Category (`products.category`), or Customer Country (`customers.country`).
- Ensure that summary totals equal the sum of grain partitions.

