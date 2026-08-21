# FintrixAi Finalized Risk Framework: MSME & NTC Feature Schema

## I. Proxy Pillars & Behavioral Discipline (NTC Core)
| Feature Name                    | Data Type | Description/Logic                                                             |
| :------------------------------ | :-------- | :---------------------------------------------------------------------------- |
| `utility_payment_consistency`   | Integer   | Longest consecutive streak of on-time payments (Electricity/Water/Broadband). |
| `avg_utility_dpd`               | Float     | Average Days Past Due across all utility bills (Lower = Higher Discipline).   |
| `rent_wallet_share`             | Float     | Monthly rent / Average monthly income (Measures financial burden).            |
| `subscription_commitment_ratio` | Float     | Total fixed monthly subscriptions / Average monthly income.                   |

## II. Liquidity & Spending Behavior (The Stress Layer)
| Feature Name                   | Data Type | Description/Logic                                                          |
| :----------------------------- | :-------- | :------------------------------------------------------------------------- |
| `emergency_buffer_months`      | Float     | Current balance / Average monthly essential outflow.                       |
| `min_balance_violation_count`  | Integer   | Count of drops below ₹500 in the last 6 months.                            |
| `eod_balance_volatility`       | Float     | Coefficient of Variation (Std Dev / Mean) of daily closing balances.       |
| `essential_vs_lifestyle_ratio` | Float     | Survival spending (Groceries/Medical) vs. Discretionary (Dining/Travel).   |
| `cash_withdrawal_dependency`   | Float     | Total cash withdrawals / Total monthly outflows (Flags off-book behavior). |
| `bounced_transaction_count`    | Integer   | Count of bounced transactions/penalty fees (Last 6 months).                |

## III. Alternative Data (Telecom & Identity)
| Feature Name                  | Data Type | Description/Logic                                                         |
| :---------------------------- | :-------- | :------------------------------------------------------------------------ |
| `telecom_number_vintage_days` | Integer   | Days since phone activation (Proxy for identity stability).               |
| `telecom_recharge_drop_ratio` | Float     | Current month recharge / 6-month average (Leading stress indicator).      |
| `academic_background_tier`    | Category  | Encoded value representing education level (Tier 1-4).                    |
| `purpose_of_loan_encoded`     | Category  | Target-encoded value of loan reason (e.g., Working Capital vs. Personal). |

## IV. MSME Operational Stability (AA & GST Data)
| Feature Name | Data Type | Description/Logic |
| :--- | :--- | :--- |
| `business_vintage_months` | Integer | Months since first banking transaction or GST registration. |
| `revenue_growth_trend` | Float | % MoM change in incoming business cashflow. |
| `revenue_seasonality_index` | Float | Statistical variance of revenue across quarters (Normalizes lumpy businesses). |
| `operating_cashflow_ratio` | Float | Monthly inflows / Monthly outflows (Survival threshold > 1.0). |
| `cashflow_volatility` | Float | Std Dev of monthly net cashflow (Measures revenue reliability). |
| `avg_invoice_payment_delay` | Float | Average days between invoice date and payment receipt (Working capital stress). |

## V. Network Risk & Compliance
| Feature Name | Data Type | Description/Logic |
| :--- | :--- | :--- |
| `customer_concentration_ratio` | Float | % of revenue from Top 3 clients (High ratio = High Fragility). |
| `repeat_customer_revenue_pct` | Float | % of revenue from repeat counterparties (Measures stickiness). |
| `vendor_payment_discipline` | Float | Average DPD when the MSME pays its own suppliers. |
| `gst_filing_consistency_score` | Integer | Longest streak of on-time GSTR-1/3B filings. |
| `gst_to_bank_variance` | Float | % difference between GST-reported revenue and actual bank inflows. |

## VI. Trust Intelligence & Forensic Flags (Layer 2)
| Feature Name               | Data Type | Description/Logic                                                       |
| :------------------------- | :-------- | :---------------------------------------------------------------------- |
| `p2p_circular_loop_flag`   | Boolean   | Binary (1/0) for A→B→A loops detected via Graph Theory.                 |
| `benford_anomaly_score`    | Float     | Deviation from Benford's Law (Flags synthetic/fake transaction values). |
| `round_number_spike_ratio` | Float     | % of transactions ending in '000' (Detects manual bookkeeping fraud).   |
| `turnover_inflation_spike` | Boolean   | Flags unnatural volume spikes 30–60 days before loan application.       |
| `identity_device_mismatch` | Boolean   | Flags if multiple accounts share the same Device IP/MAC address.        |
|                            |           |                                                                         |



### Implementation Note for PDR

For your **Data Engineering** phase, ensure you handle the **Boolean Flags** separately. In XGBoost, these flags should have a high **Feature Importance** weight because a `1` in `identity_device_mismatch` or `p2p_circular_loop_flag` should override even the best "Revenue Growth."

Would you like me to help you write the **Data Cleaning script** that handles the missing values for NTC users (who won't have the MSME features) so your model doesn't crash?





