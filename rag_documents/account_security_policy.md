# AegisBank AI — Account Security Policy
Policy ID: ASP-2026-03
Category: Account Security
Version: 1.0

## 1. Purpose
This policy protects customer accounts from unauthorised access and account takeover.

## 2. Device Management
Customers register trusted devices. A transaction from a device not previously associated with the account is a new device event and adds risk. A new device combined with a new location is a primary account takeover signature.

## 3. Account Takeover Indicators
Account takeover is suspected when a new device, an unusual city, a large transfer to a new beneficiary and a night-time timestamp occur together. These cases should be recommended for blocking and investigation.

## 4. Credential and Session Controls
Passwords are stored only as salted hashes. Sessions use short-lived signed tokens. Repeated failed login attempts trigger rate limiting and are recorded in the audit log.

## 5. Customer Contact
When account takeover is suspected, the analyst contacts the customer through a previously verified channel, never through details supplied in the suspicious transaction.
