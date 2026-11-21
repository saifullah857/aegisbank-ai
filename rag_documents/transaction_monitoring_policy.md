# AegisBank AI — Transaction Monitoring Policy
Policy ID: TMP-2026-01
Category: Transaction Monitoring
Version: 1.0

## 1. Purpose and Scope
This policy defines how every customer transaction is monitored for fraud. All transactions are scored automatically by the rule engine and the machine-learning anomaly model before an analyst ever sees them.

## 2. Risk Indicators
The rule engine awards points for: new device (20), unusual location (20), unusual amount above five times the customer's average (20), high transaction velocity of three or more transactions within fifteen minutes (15), new beneficiary (15), unusual merchant category (10) and recent failed attempts (10). Scores are capped at 100.

## 3. Risk Bands
A score of 0 to 30 is LOW, 31 to 60 is MEDIUM, 61 to 80 is HIGH and 81 to 100 is CRITICAL. LOW transactions complete normally. MEDIUM transactions are flagged for sampling review. HIGH and CRITICAL transactions automatically open a fraud case.

## 4. Velocity Monitoring
Rapid repeated transactions in a short time window, especially from a new device or new city, are a strong indicator of account takeover or card testing. Velocity alerts must be reviewed on the same business day.

## 5. High-Value and Night-Time Activity
Transfers far above a customer's normal spending, particularly between 00:00 and 05:00 local time, require enhanced review. Large first-time transfers to a new beneficiary are treated as high risk regardless of channel.
