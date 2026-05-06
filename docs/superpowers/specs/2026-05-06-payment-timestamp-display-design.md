# Design: Add Payment Timestamp Display to Web Interface

**Date:** 2026-05-06  
**Scope:** Add payment time (HH:MM) to the payment history table in the web frontend

## Overview

Currently, the web interface payment history table displays only the date of each payment (e.g., `06.05.2026`). Users cannot see what time the payment was made. This design adds the time component to show both date and time in format: `06.05.2026 18:30`.

## Architecture

**System Boundaries:**
- **Backend API** — Already returns `created_at` as ISO 8601 datetime (timezone-aware)
- **Web Frontend** — Displays payment history in a table using vanilla JavaScript
- **Data Flow:** Backend → Web API proxy → Frontend JavaScript → Browser rendering

## Feature: Display Payment Date and Time

### Component: Payment History Table (web/frontend/js/pages.js)

**Current Behavior (lines 514-520):**
```javascript
const date = new Date(p.created_at).toLocaleDateString('ru-RU');
// Output: "06.05.2026"
```

**New Behavior:**
```javascript
const dateTime = new Date(p.created_at).toLocaleString('ru-RU', {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false
});
// Output: "06.05.2026 18:30"
```

**Table Column:**
- Header: "Дата" (unchanged, already exists at line 508)
- Cell content: Date + time in format `DD.MM.YYYY HH:MM`

### Error Handling

If `p.created_at` is null or undefined:
- Display fallback text: `"—"` (em-dash)
- No error thrown; payment row renders normally

**Rationale:** Some older payments may not have created_at stored in the database. The UI should gracefully handle this without breaking the table.

## Data Contracts

**Input (from Backend API):**
```json
{
  "payment_id": "str",
  "tg_id": 123,
  "amount": 99.99,
  "status": "succeeded",
  "payment_type": "create_key",
  "created_at": "2026-05-06T18:30:00+00:00"
}
```

**Output (rendered in HTML):**
```html
<td style="padding:10px">06.05.2026 18:30</td>
```

## Testing Strategy

### Manual Testing (E2E)
1. Navigate to payment history page in web interface
2. Verify each payment row displays date and time
3. Check format is exactly `DD.MM.YYYY HH:MM` (e.g., `06.05.2026 18:30`)
4. Test with various times (morning, afternoon, night)
5. Test with payment having null `created_at` (should show "—")

### Code Coverage
- No unit tests needed (simple formatting logic)
- Relies on existing E2E test infrastructure for page rendering

## Scope & Constraints

**In Scope:**
- Modify frontend date formatting
- Handle null/undefined `created_at`

**Out of Scope:**
- Backend changes (already returns timestamps)
- Timezone conversion (use browser's local timezone)
- Internationalization beyond ru-RU locale

## Success Criteria

1. ✓ Payment history table displays both date and time
2. ✓ Format matches `DD.MM.YYYY HH:MM` exactly
3. ✓ Null timestamps display as "—" without errors
4. ✓ No performance degradation
5. ✓ Visual table layout remains unchanged

## Implementation Notes

- **File:** `web/frontend/js/pages.js`
- **Lines:** ~515 (date formatting logic)
- **Changes:** Replace `toLocaleDateString()` call with `toLocaleString()` + formatting options
- **Complexity:** Minimal (single-line change with fallback)
- **Risk:** Very low (isolated frontend change, no API/DB impact)
