# Appendix C — Database Schema Reference

## 1. Primary Analytical Database (`data/ecommerce.db`)

- **File Path**: `data/ecommerce.db` (Read-only at runtime)
- **SHA-256 Checksum**: `c5a5965e000becdb75d0802897cb047dc2f827d1fdc7bacdf9d53ef7a46b6934`
- **Total Tables**: `7`
- **Total Records**: `499,385`
- **Temporal Coverage (`orders.order_date`)**: `2024-01-01 00:08:26` to `2026-09-29 23:22:24`

---

### Table 1: `customers` (`26,000` rows)

| Column Name | Declared Type | Affinity | NOT NULL | Primary Key | Foreign Key | Domain / Sample Values |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `customer_id` | `INTEGER` | `INTEGER` | Yes | **PK (1)** | — | `1` .. `26000` |
| `first_name` | `TEXT` | `TEXT` | Yes | No | — | Customer given name |
| `last_name` | `TEXT` | `TEXT` | Yes | No | — | Customer family name |
| `email` | `TEXT` | `TEXT` | Yes | No | — | Customer email address |
| `phone` | `TEXT` | `TEXT` | No | No | — | Nullable phone string |
| `country` | `TEXT` | `TEXT` | Yes | No | — | `Australia`, `Canada`, `France`, `Germany`, `Ireland`, `Italy`, `Netherlands`, `New Zealand`, `Spain`, `Sweden`, `United Kingdom`, `United States` |
| `city` | `TEXT` | `TEXT` | Yes | No | — | City name |
| `signup_date` | `TEXT` | `TEXT` | Yes | No | — | ISO date (`YYYY-MM-DD`) |
| `loyalty_tier` | `TEXT` | `TEXT` | Yes | No | — | `'none'`, `'silver'`, `'gold'`, `'platinum'` |
| `marketing_opt_in` | `INTEGER` | `INTEGER` | Yes | No | — | `0` or `1` |

- **Indexes**: `idx_customers_country(country)`, `idx_customers_signup_date(signup_date)`, `idx_customers_loyalty_tier(loyalty_tier)`

---

### Table 2: `products` (`1,500` rows)

| Column Name | Declared Type | Affinity | NOT NULL | Primary Key | Foreign Key | Domain / Sample Values |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `product_id` | `INTEGER` | `INTEGER` | Yes | **PK (1)** | — | `1` .. `1500` |
| `sku` | `TEXT` | `TEXT` | Yes | No | — | Stock keeping unit code |
| `product_name` | `TEXT` | `TEXT` | Yes | No | — | Product display title |
| `category` | `TEXT` | `TEXT` | Yes | No | — | `'Accessories'`, `'Apparel'`, `'Backpacks'`, `'Climbing'`, `'Cooking'`, `'Footwear'`, `'Lighting'`, `'Navigation'`, `'Sleeping Bags'`, `'Tents'` |
| `brand` | `TEXT` | `TEXT` | Yes | No | — | Brand name |
| `unit_price` | `NUMERIC` | `NUMERIC` | Yes | No | — | List unit price ($) |
| `unit_cost` | `NUMERIC` | `NUMERIC` | Yes | No | — | Wholesale unit cost ($) |
| `weight_kg` | `NUMERIC` | `NUMERIC` | No | No | — | Nullable product weight in kg |
| `is_active` | `INTEGER` | `INTEGER` | Yes | No | — | `0` or `1` |
| `created_at` | `TEXT` | `TEXT` | Yes | No | — | ISO timestamp |

- **Indexes**: `idx_products_category(category)`, `idx_products_brand(brand)`, `idx_products_created_at(created_at)`

---

### Table 3: `orders` (`90,000` rows)

| Column Name | Declared Type | Affinity | NOT NULL | Primary Key | Foreign Key | Domain / Sample Values |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `order_id` | `INTEGER` | `INTEGER` | Yes | **PK (1)** | — | `1` .. `90000` |
| `customer_id` | `INTEGER` | `INTEGER` | Yes | No | `customers.customer_id` | Customer foreign key |
| `order_date` | `TEXT` | `TEXT` | Yes | No | — | `2024-01-01 00:08:26` .. `2026-09-29 23:22:24` |
| `status` | `TEXT` | `TEXT` | Yes | No | — | `'cancelled'`, `'delivered'`, `'processing'`, `'returned'`, `'shipped'` |
| `channel` | `TEXT` | `TEXT` | Yes | No | — | `'app'`, `'marketplace'`, `'store'`, `'web'` |
| `subtotal` | `NUMERIC` | `NUMERIC` | Yes | No | — | Pre-discount order subtotal ($) |
| `discount_amount` | `NUMERIC` | `NUMERIC` | Yes | No | — | Order-level discount ($) |
| `shipping_fee` | `NUMERIC` | `NUMERIC` | Yes | No | — | Order shipping fee ($) |
| `tax_amount` | `NUMERIC` | `NUMERIC` | Yes | No | — | Order tax ($) |
| `total_amount` | `NUMERIC` | `NUMERIC` | Yes | No | — | Final order total (`subtotal - discount + shipping + tax`) |
| `currency` | `TEXT` | `TEXT` | Yes | No | — | `'USD'` |

- **Indexes**: `idx_orders_customer_id(customer_id)`, `idx_orders_order_date(order_date)`, `idx_orders_status(status)`, `idx_orders_channel(channel)`

---

### Table 4: `order_items` (`200,000` rows)

| Column Name | Declared Type | Affinity | NOT NULL | Primary Key | Foreign Key | Domain / Sample Values |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `order_item_id` | `INTEGER` | `INTEGER` | Yes | **PK (1)** | — | `1` .. `200000` |
| `order_id` | `INTEGER` | `INTEGER` | Yes | No | `orders.order_id` | Parent order ID |
| `product_id` | `INTEGER` | `INTEGER` | Yes | No | `products.product_id` | Purchased product ID |
| `quantity` | `INTEGER` | `INTEGER` | Yes | No | — | Units purchased (`>= 1`) |
| `unit_price` | `NUMERIC` | `NUMERIC` | Yes | No | — | Unit price at time of purchase ($) |
| `line_total` | `NUMERIC` | `NUMERIC` | Yes | No | — | `quantity * unit_price` ($) |

- **Indexes**: `idx_order_items_order_id(order_id)`, `idx_order_items_product_id(product_id)`

---

### Table 5: `payments` (`90,000` rows)

| Column Name | Declared Type | Affinity | NOT NULL | Primary Key | Foreign Key | Domain / Sample Values |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `payment_id` | `INTEGER` | `INTEGER` | Yes | **PK (1)** | — | `1` .. `90000` |
| `order_id` | `INTEGER` | `INTEGER` | Yes | No | `orders.order_id` | Associated order ID |
| `method` | `TEXT` | `TEXT` | Yes | No | — | `'apple_pay'`, `'bank_transfer'`, `'card'`, `'google_pay'`, `'klarna'`, `'paypal'` |
| `amount` | `NUMERIC` | `NUMERIC` | Yes | No | — | Payment transaction amount ($) |
| `paid_at` | `TEXT` | `TEXT` | Yes | No | — | ISO timestamp |
| `status` | `TEXT` | `TEXT` | Yes | No | — | `'captured'`, `'failed'`, `'refunded'` |

- **Indexes**: `idx_payments_order_id(order_id)`, `idx_payments_method(method)`, `idx_payments_paid_at(paid_at)`, `idx_payments_status(status)`

---

### Table 6: `shipments` (`83,885` rows)

| Column Name | Declared Type | Affinity | NOT NULL | Primary Key | Foreign Key | Domain / Sample Values |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `shipment_id` | `INTEGER` | `INTEGER` | Yes | **PK (1)** | — | `1` .. `83885` |
| `order_id` | `INTEGER` | `INTEGER` | Yes | No | `orders.order_id` | Associated order ID |
| `carrier` | `TEXT` | `TEXT` | Yes | No | — | `'Canada Post'`, `'DHL'`, `'DPD'`, `'FedEx'`, `'Royal Mail'`, `'UPS'`, `'USPS'` |
| `tracking_number` | `TEXT` | `TEXT` | Yes | No | — | Carrier tracking code |
| `shipped_at` | `TEXT` | `TEXT` | Yes | No | — | ISO timestamp |
| `delivered_at` | `TEXT` | `TEXT` | No | No | — | Nullable delivery ISO timestamp (`NULL` when `in_transit`) |
| `status` | `TEXT` | `TEXT` | Yes | No | — | `'delivered'`, `'in_transit'` |

- **Indexes**: `idx_shipments_order_id(order_id)`, `idx_shipments_carrier(carrier)`, `idx_shipments_shipped_at(shipped_at)`, `idx_shipments_delivered_at(delivered_at)`, `idx_shipments_status(status)`

---

### Table 7: `returns` (`8,000` rows)

| Column Name | Declared Type | Affinity | NOT NULL | Primary Key | Foreign Key | Domain / Sample Values |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `return_id` | `INTEGER` | `INTEGER` | Yes | **PK (1)** | — | `1` .. `8000` |
| `order_item_id` | `INTEGER` | `INTEGER` | Yes | No | `order_items.order_item_id` | Returned line item ID |
| `reason` | `TEXT` | `TEXT` | Yes | No | — | `'arrived_late'`, `'changed_mind'`, `'damaged'`, `'not_as_described'`, `'wrong_size'` |
| `refund_amount` | `NUMERIC` | `NUMERIC` | Yes | No | — | Requested/approved refund ($) |
| `requested_at` | `TEXT` | `TEXT` | Yes | No | — | ISO timestamp |
| `status` | `TEXT` | `TEXT` | Yes | No | — | `'approved'`, `'refunded'`, `'rejected'`, `'requested'` |

- **Indexes**: `idx_returns_order_item_id(order_item_id)`, `idx_returns_reason(reason)`, `idx_returns_requested_at(requested_at)`, `idx_returns_status(status)`

