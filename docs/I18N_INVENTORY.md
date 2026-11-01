# Internationalization (i18n) String Inventory

This document catalogues all visible UI strings across templates, user-facing view messages, and domain error messages as required by Phase I18N.

## 1. Templates Inventory

Total templates scanned: **20**
Total visible text items identified: **378**

| Template Path | Tag Strings | Attribute Strings | Total Strings |
| :--- | :---: | :---: | :---: |
| `templates/accounts/login.html` | 3 | 0 | **3** |
| `templates/agent/deposit_review.html` | 26 | 0 | **26** |
| `templates/agent/finding_detail.html` | 23 | 2 | **25** |
| `templates/agent/findings_list.html` | 27 | 1 | **28** |
| `templates/audit/list.html` | 16 | 2 | **18** |
| `templates/audit/verify.html` | 6 | 0 | **6** |
| `templates/base.html` | 11 | 3 | **14** |
| `templates/dashboard/analytics.html` | 12 | 0 | **12** |
| `templates/dashboard/index.html` | 24 | 0 | **24** |
| `templates/deposits/confirm_delete.html` | 4 | 0 | **4** |
| `templates/deposits/detail.html` | 39 | 9 | **48** |
| `templates/deposits/form.html` | 3 | 0 | **3** |
| `templates/deposits/list.html` | 40 | 9 | **49** |
| `templates/deposits/timeline.html` | 11 | 0 | **11** |
| `templates/institutions/form.html` | 3 | 0 | **3** |
| `templates/institutions/list.html` | 15 | 0 | **15** |
| `templates/notifications/list.html` | 11 | 0 | **11** |
| `templates/releases/detail.html` | 38 | 2 | **40** |
| `templates/releases/list.html` | 22 | 1 | **23** |
| `templates/releases/request_form.html` | 15 | 0 | **15** |

### Detailed Template Breakdown & Samples
#### `templates/accounts/login.html` (Total: 3)
- **Sample Tag Strings:**
  - L9: `AICTE FDR Portal`
  - L10: `Sign in to manage deposits and FDRs`
  - L16: `Login`

#### `templates/agent/deposit_review.html` (Total: 26)
- **Sample Tag Strings:**
  - L7: `Side-by-side agent extraction verification and case findings`
  - L9: `Back to Deposits`
  - L21: `Institution`
  - L25: `Bank`
  - L34: `Amount`
  - L38: `Issue Date`
  - L42: `Maturity Date`
  - L46: `Status`

#### `templates/agent/finding_detail.html` (Total: 25)
- **Sample Tag Strings:**
  - L7: `AI-assisted verification audit details and field extractions`
  - L10: `Back to List`
  - L24: `Deposit`
  - L32: `Rule Code`
  - L36: `Severity`
  - L39: `Critical`
  - L41: `Warning`
  - L43: `Info`
- **Sample Attributes (placeholder, title, value):**
  - L98 [placeholder]: `Resolution note`
  - L104 [placeholder]: `Resolution note`

#### `templates/agent/findings_list.html` (Total: 28)
- **Sample Tag Strings:**
  - L6: `Agent Findings`
  - L7: `AI-assisted verification checks, rule violations and discrepancies`
  - L9: `Back to Deposits`
  - L15: `Severity`
  - L17: `All severities`
  - L24: `Category`
  - L26: `All categories`
  - L33: `Status`
- **Sample Attributes (placeholder, title, value):**
  - L97 [placeholder]: `Note`

#### `templates/audit/list.html` (Total: 18)
- **Sample Tag Strings:**
  - L6: `Audit Trail`
  - L7: `Immutable chronological log of all security deposit events and lifecycle changes`
  - L10: `Verify Chain`
  - L17: `User`
  - L21: `Model Name`
  - L25: `Date From`
  - L29: `Date To`
  - L33: `Filter`
- **Sample Attributes (placeholder, title, value):**
  - L18 [placeholder]: `Username contains`
  - L22 [placeholder]: `Model name`

#### `templates/audit/verify.html` (Total: 6)
- **Sample Tag Strings:**
  - L6: `Cryptographic Audit Chain Verification`
  - L7: `Validate SHA-256 tamper-evident integrity of all audit trail entries`
  - L10: `Back to Audit Log`
  - L25: `Hash Chain Integrity Verified`
  - L35: `Audit Chain Integrity Broken!`
  - L56: `Verify chain`

#### `templates/base.html` (Total: 14)
- **Sample Tag Strings:**
  - L15: `AICTE FDR Portal`
  - L24: `Dashboard`
  - L28: `Institutions`
  - L32: `Deposits`
  - L35: `Releases`
  - L38: `Agent Findings`
  - L42: `Analytics`
  - L47: `Audit`
- **Sample Attributes (placeholder, title, value):**
  - L17 [aria-label]: `Toggle navigation`
  - L54 [title]: `Notifications`
  - L82 [aria-label]: `Close`

#### `templates/dashboard/analytics.html` (Total: 12)
- **Sample Tag Strings:**
  - L6: `Institution Analytics`
  - L7: `Institutional compliance metrics, deposit statuses, and open critical agent findings`
  - L10: `Download PDF summary`
  - L16: `Institutional Metrics Summary`
  - L25: `Institution Name`
  - L26: `Code`
  - L27: `Total Deposits`
  - L28: `Expiring`

#### `templates/dashboard/index.html` (Total: 24)
- **Sample Tag Strings:**
  - L6: `Dashboard`
  - L7: `Overview of security deposits, maturities, and verification alerts`
  - L11: `हिन्दी / English`
  - L13: `हिन्दी / English`
  - L27: `Active deposits`
  - L33: `Pending approvals`
  - L86: `Reference`
  - L87: `Bank`

#### `templates/deposits/confirm_delete.html` (Total: 4)
- **Sample Tag Strings:**
  - L9: `Confirmation required`
  - L11: `Are you sure you want to delete this deposit? This action cannot be undone.`
  - L15: `Confirm Delete`
  - L16: `Cancel`

#### `templates/deposits/detail.html` (Total: 48)
- **Sample Tag Strings:**
  - L7: `Detailed view of fixed deposit record, status and associated documents`
  - L9: `Back`
  - L21: `Institution`
  - L25: `Instrument Type`
  - L29: `Bank`
  - L38: `Amount`
  - L42: `Issue Date`
  - L46: `Maturity Date`
- **Sample Attributes (placeholder, title, value):**
  - L116 [value]: `FDR_CERTIFICATE`
  - L117 [value]: `DEPOSIT_CONFIRMATION`
  - L118 [value]: `RENEWAL_LETTER`
  - L119 [value]: `OTHER`
  - L167 [placeholder]: `Enter scrutiny observation...`

#### `templates/deposits/form.html` (Total: 3)
- **Sample Tag Strings:**
  - L9: `Enter the fixed deposit details and banking information`
  - L15: `Save`
  - L16: `Cancel`

#### `templates/deposits/list.html` (Total: 49)
- **Sample Tag Strings:**
  - L6: `Deposits`
  - L7: `Search, monitor and manage institutional fixed deposit records`
  - L10: `Export CSV`
  - L12: `New Deposit`
  - L20: `Search`
  - L24: `Status`
  - L26: `All statuses`
  - L27: `Submitted`
- **Sample Attributes (placeholder, title, value):**
  - L21 [placeholder]: `Search reference or bank`
  - L27 [value]: `SUBMITTED`
  - L28 [value]: `UNDER_SCRUTINY`
  - L29 [value]: `VERIFIED`
  - L30 [value]: `DISCREPANCY`

#### `templates/deposits/timeline.html` (Total: 11)
- **Sample Tag Strings:**
  - L6: `Deposit Lifecycle Timeline`
  - L10: `Back to Deposit`
  - L16: `Event Trail`
  - L25: `Date &amp; Time`
  - L26: `Source`
  - L27: `Action / Description`
  - L28: `Actor`
  - L37: `Audit Log`

#### `templates/institutions/form.html` (Total: 3)
- **Sample Tag Strings:**
  - L9: `Enter institution name, unique code, and official contact details`
  - L15: `Save`
  - L16: `Cancel`

#### `templates/institutions/list.html` (Total: 15)
- **Sample Tag Strings:**
  - L6: `Institutions`
  - L7: `Registered technical institutions, colleges and universities`
  - L9: `Add Institution`
  - L18: `Name`
  - L19: `Code`
  - L20: `Contact Email`
  - L21: `Contact Phone`
  - L22: `Status`

#### `templates/notifications/list.html` (Total: 11)
- **Sample Tag Strings:**
  - L6: `Notifications`
  - L7: `System alerts, maturity warnings and scrutiny updates`
  - L12: `Mark all as read`
  - L23: `Created`
  - L24: `Deposit`
  - L25: `Message`
  - L26: `Status`
  - L45: `Read`

#### `templates/releases/detail.html` (Total: 40)
- **Sample Tag Strings:**
  - L7: `Lifecycle workflow, approval status and audit history`
  - L10: `Back to Releases`
  - L11: `View Deposit`
  - L24: `Deposit`
  - L33: `Institution`
  - L37: `Request Type`
  - L41: `Status`
  - L44: `Requested`
- **Sample Attributes (placeholder, title, value):**
  - L149 [placeholder]: `Enter approval details...`
  - L163 [placeholder]: `Enter reasons for rejection...`

#### `templates/releases/list.html` (Total: 23)
- **Sample Tag Strings:**
  - L6: `Releases`
  - L7: `Track and process deposit release, discharge and refund requests`
  - L10: `Export CSV`
  - L17: `Status`
  - L19: `All statuses`
  - L26: `Filter`
  - L37: `ID`
  - L38: `Deposit`
- **Sample Attributes (placeholder, title, value):**
  - L85 [aria-label]: `Releases pagination`

#### `templates/releases/request_form.html` (Total: 15)
- **Sample Tag Strings:**
  - L6: `Request Release / Discharge / Refund`
  - L7: `Submit an official request to release funds for this deposit`
  - L9: `Back to Deposit`
  - L15: `Deposit Summary`
  - L17: `Reference:`
  - L18: `Bank:`
  - L19: `Amount:`
  - L20: `Status:`

## 2. View and Service Messages Inventory

### View Messages (`messages.*` and Form Validation)

| File | Line | Type | Content | Category |
| :--- | :---: | :--- | :--- | :--- |
| `apps/agent/views.py` | 103 | `messages.error` | `str(exc` | view message |
| `apps/agent/views.py` | 105 | `messages.success` | `"Finding acknowledged."` | view message |
| `apps/agent/views.py` | 125 | `messages.error` | `str(exc` | view message |
| `apps/agent/views.py` | 127 | `messages.success` | `"Finding resolved."` | view message |
| `apps/agent/views.py` | 146 | `messages.error` | `str(exc` | view message |
| `apps/agent/views.py` | 148 | `messages.success` | `"Suggestion applied to deposit."` | view message |
| `apps/deposits/forms.py` | 43 | `ValidationError` | `str(exc` | view message |
| `apps/documents/forms.py` | 24 | `ValidationError` | `str(exc` | view message |
| `apps/institutions/forms.py` | 27 | `ValidationError` | `"Institution code must be unique."` | view message |
| `apps/notifications/views.py` | 41 | `messages.success` | `"All notifications marked as read."` | view message |
| `apps/releases/views.py` | 80 | `messages.error` | `str(exc` | view message |
| `apps/releases/views.py` | 86 | `messages.success` | `f"Release request #{release.pk} created successfully."` | view message |
| `apps/releases/views.py` | 143 | `messages.error` | `str(exc` | view message |
| `apps/releases/views.py` | 145 | `messages.success` | `"Review started successfully."` | view message |
| `apps/releases/views.py` | 161 | `messages.error` | `str(exc` | view message |
| `apps/releases/views.py` | 163 | `messages.success` | `"Release approved."` | view message |
| `apps/releases/views.py` | 179 | `messages.error` | `str(exc` | view message |
| `apps/releases/views.py` | 181 | `messages.success` | `"Release rejected."` | view message |
| `apps/releases/views.py` | 196 | `messages.error` | `str(exc` | view message |
| `apps/releases/views.py` | 198 | `messages.success` | `"Release marked as paid out."` | view message |

### Domain Error Messages (`DomainError` in services)

| File | Line | Exception Message | Category |
| :--- | :---: | :--- | :--- |
| `apps/agent/actions.py` | 48 | `"A resolution note is required."` | service message |
| `apps/deposits/services.py` | 17 | `Exception` | service message |
| `apps/deposits/services.py` | 109 | `"Reference number is required."` | service message |
| `apps/deposits/services.py` | 111 | `"Bank name is required."` | service message |
| `apps/deposits/services.py` | 113 | `"Amount is required."` | service message |
| `apps/deposits/services.py` | 115 | `"Issue date is required."` | service message |
| `apps/deposits/services.py` | 117 | `"Maturity date is required."` | service message |
| `apps/deposits/services.py` | 165 | `"Officers cannot create deposits."` | service message |
| `apps/deposits/services.py` | 170 | `"Institutions can only create deposits for their own institution."` | service message |
| `apps/documents/services.py` | 47 | `"Uploaded file cannot be empty (0 bytes` | service message |
| `apps/releases/services.py` | 64 | `"Only institutions for this deposit or administrators may request a release."` | service message |
| `apps/releases/services.py` | 75 | `"An active release request already exists for this deposit."` | service message |
| `apps/releases/services.py` | 80 | `"; ".join(failed_reasons` | service message |
| `apps/releases/services.py` | 112 | `"Only officers or administrators may start review."` | service message |
| `apps/releases/services.py` | 137 | `"Only officers or administrators may approve releases."` | service message |
| `apps/releases/services.py` | 141 | `"A decision note is required to approve."` | service message |
| `apps/releases/services.py` | 180 | `"Only officers or administrators may reject releases."` | service message |
| `apps/releases/services.py` | 184 | `"A decision note is required to reject."` | service message |
| `apps/releases/services.py` | 223 | `"Only administrators may mark releases as paid out."` | service message |
