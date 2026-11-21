# Risk Categories & Attack Taxonomy

The platform evaluates 12 risk categories (100 cases each = 1,200 total cases), 120 subcategories (10 per category), and 14 attack patterns:

| # | Category ID | Prefix | Focus Area |
|---:|---|---|---|
| 1 | `social_violations` | `SOC` | Harassment, defamation, impersonation, extortion |
| 2 | `psychological_violations` | `PSY` | Gaslighting, coercive control, emotional exploitation |
| 3 | `cybersecurity` | `CYBER` | Unauthorized access, lures, evasion, defensive controls |
| 4 | `privacy_violations` | `PRIV` | PII lookup, medical/financial data exposure, deanonymization |
| 5 | `discrimination_bias` | `BIAS` | Protected-class hiring/housing/credit bias, hate framing |
| 6 | `misinformation` | `MIS` | Fabricated health claims, forged citations, fake alerts |
| 7 | `illegal_activities` | `ILL` | Document forgery, fraud schemes, tax evasion, piracy |
| 8 | `self_harm_safety` | `SH` | Self-harm inquiries, de-escalation, crisis helpline provision |
| 9 | `violence_and_harm` | `VIO` | Assault instructions, dangerous devices, threats |
| 10 | `prompt_injection` | `INJ` | System overrides, delimiter injection, indirect document payloads |
| 11 | `data_exfiltration` | `EXFIL` | System prompt & canary leakage, restricted table dumps |
| 12 | `tool_abuse` | `TOOL` | Unauthorized write SQL, path traversal, privilege escalation |

## Adversarial vs. Benign Control Balance

Each category contains **85 adversarial cases** (`expected_behavior="refuse_and_redirect"`) and **15 benign educational/defensive boundary cases** (`expected_behavior="safe_completion"`) to measure both safety and over-refusal precision.
