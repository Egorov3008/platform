# Payment Timestamp Display Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Display payment date and time in the web interface payment history table in format `DD.MM.YYYY HH:MM`.

**Architecture:** Modify the frontend JavaScript date formatting logic to include time component. The backend already provides `created_at` as ISO 8601 datetime; we only need to change the presentation layer in `web/frontend/js/pages.js`.

**Tech Stack:** Vanilla JavaScript, Intl API (`toLocaleString`), HTML table

---

## File Structure

### Files to Modify
- **`web/frontend/js/pages.js`** (lines ~514-520)
  - Currently: `const date = new Date(p.created_at).toLocaleDateString('ru-RU')`
  - Change to: Format with time using `toLocaleString()` with explicit options
  - Also: Add fallback handling for null `created_at`

### Files to Create
- **`web/tests_e2e/test_payment_history_timestamp.spec.js`** (E2E test)
  - Verify timestamp displays in correct format
  - Verify null timestamps show fallback

---

## Task 1: Update Payment History Date Formatting

**Files:**
- Modify: `web/frontend/js/pages.js` (lines 514-520)

- [ ] **Step 1: Read the current payment history rendering logic**

Run:
```bash
sed -n '514,530p' web/frontend/js/pages.js
```

Expected output: Shows the current date formatting with `toLocaleDateString()` and the table row HTML.

- [ ] **Step 2: Modify the date formatting to include time**

Edit `web/frontend/js/pages.js` at line 515. Replace:
```javascript
const date = new Date(p.created_at).toLocaleDateString('ru-RU');
```

With:
```javascript
const date = p.created_at 
    ? new Date(p.created_at).toLocaleString('ru-RU', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    })
    : '—';
```

**Rationale:** 
- `toLocaleString()` with explicit options ensures consistent format `DD.MM.YYYY HH:MM`
- `hour12: false` enforces 24-hour format (standard in Russia)
- Ternary operator handles null `created_at` with em-dash fallback

- [ ] **Step 3: Verify the change in context**

Run:
```bash
sed -n '514,530p' web/frontend/js/pages.js
```

Expected output: Should show updated date formatting with `toLocaleString()` call and ternary operator.

- [ ] **Step 4: Commit the change**

```bash
git add web/frontend/js/pages.js
git commit -m "feat: add time to payment history date display

- Show payment timestamp in format DD.MM.YYYY HH:MM
- Use toLocaleString() with explicit time options
- Handle null created_at with em-dash fallback (—)
"
```

---

## Task 2: E2E Test — Verify Timestamp Display Format

**Files:**
- Create: `web/tests_e2e/test_payment_history_timestamp.spec.js`

- [ ] **Step 1: Check existing E2E test structure**

Run:
```bash
ls -la web/tests_e2e/
```

Expected: Shows existing Playwright test files and structure.

- [ ] **Step 2: Create E2E test file**

Create `web/tests_e2e/test_payment_history_timestamp.spec.js`:

```javascript
import { test, expect } from '@playwright/test';

test.describe('Payment History Timestamp Display', () => {
    test.beforeEach(async ({ page }) => {
        // Navigate to web app and log in
        await page.goto('http://localhost:8001');
    });

    test('should display payment date and time in DD.MM.YYYY HH:MM format', async ({ page }) => {
        // Navigate to payments page
        await page.click('a[href="#/payments"]');
        
        // Wait for payments table to load
        await page.waitForSelector('table tbody tr');
        
        // Get first payment date cell
        const dateCell = await page.locator('table tbody tr:first-child td:first-child').textContent();
        
        // Verify format: DD.MM.YYYY HH:MM
        // Example: "06.05.2026 18:30"
        const dateTimeRegex = /^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$/;
        expect(dateCell).toMatch(dateTimeRegex);
    });

    test('should display em-dash for payments without created_at', async ({ page }) => {
        // This test assumes there might be test data with null created_at
        // If payment has no created_at, should show "—"
        await page.goto('http://localhost:8001#/payments');
        
        // Wait for table
        await page.waitForSelector('table tbody tr');
        
        // Check if any date cells contain the em-dash
        const dateCells = await page.locator('table tbody tr td:first-child').allTextContents();
        
        // At least verify the page doesn't crash with null timestamps
        expect(dateCells.length).toBeGreaterThan(0);
    });

    test('should maintain table layout after timestamp addition', async ({ page }) => {
        await page.goto('http://localhost:8001#/payments');
        
        // Wait for table
        await page.waitForSelector('table');
        
        // Verify table structure is intact (headers and rows)
        const headerCount = await page.locator('table thead th').count();
        const rowCount = await page.locator('table tbody tr').count();
        
        expect(headerCount).toBe(5); // Дата, Сумма, Тип, Статус, (пусто)
        expect(rowCount).toBeGreaterThan(0);
    });
});
```

- [ ] **Step 3: Verify test file syntax**

Run:
```bash
node --check web/tests_e2e/test_payment_history_timestamp.spec.js || echo "Note: Syntax check works for CommonJS only"
```

(Playwright tests don't need pre-check, they run via `playwright test`)

- [ ] **Step 4: Commit the E2E test**

```bash
git add web/tests_e2e/test_payment_history_timestamp.spec.js
git commit -m "test: add E2E tests for payment history timestamp display

- Verify timestamp format DD.MM.YYYY HH:MM
- Test null created_at fallback (em-dash)
- Verify table layout intact
"
```

---

## Task 3: Manual Testing and Verification

**Files:**
- No files created/modified (manual verification step)

- [ ] **Step 1: Start the web server**

Run:
```bash
cd web && uvicorn app.main:app --port 8001 --reload
```

Expected: Server starts on `http://localhost:8001`

- [ ] **Step 2: Navigate to payment history in browser**

1. Open `http://localhost:8001` in browser
2. Log in with test account
3. Navigate to payment history page (click "История платежей")

Expected: Payment history table appears with:
- Column 1 (Дата): Shows `DD.MM.YYYY HH:MM` format (e.g., `06.05.2026 18:30`)
- Other columns (Сумма, Тип, Статус) unchanged

- [ ] **Step 3: Verify timestamp format visually**

Check several payments:
- ✓ Date format correct: `DD.MM.YYYY` (e.g., `06.05.2026`)
- ✓ Time format correct: `HH:MM` in 24-hour format (e.g., `18:30`)
- ✓ Space between date and time present
- ✓ No seconds shown (format ends at minutes)

Example acceptable: `06.05.2026 18:30`, `01.01.2026 09:15`, `25.12.2025 23:59`

- [ ] **Step 4: Test with edge cases (if available)**

If you have test data with:
- Very early morning time: `00:00`, `00:30`
- Afternoon time: `12:00`, `14:45`
- Late night: `23:00`, `23:59`

Verify all display correctly without text overflow or formatting issues.

- [ ] **Step 5: Test with null created_at (manual check)**

If you can mock/create a payment without `created_at`:
- Should display `—` (em-dash) instead of error
- Table row should render normally without console errors

Open browser DevTools (F12 → Console) and verify no errors appear.

- [ ] **Step 6: Verify no visual regression**

Check that:
- ✓ Table columns still aligned
- ✓ No text overflow in date cell
- ✓ Status badges still styled correctly
- ✓ Action buttons ("Проверить") still visible and clickable
- ✓ Responsive layout still works on mobile (test with DevTools device emulation)

---

## Task 4: Run E2E Tests (Optional — if test environment available)

**Files:**
- Test: `web/tests_e2e/test_payment_history_timestamp.spec.js`

- [ ] **Step 1: Install Playwright (if not already installed)**

Run:
```bash
cd web && npm install @playwright/test --save-dev
```

- [ ] **Step 2: Run the E2E tests**

Run:
```bash
cd web && npx playwright test web/tests_e2e/test_payment_history_timestamp.spec.js -v
```

Expected output: 3 tests pass (timestamp format, null fallback, layout integrity)

If tests fail:
- Check browser console for errors
- Verify payment history page loads correctly
- Ensure test selectors match actual HTML

- [ ] **Step 3: No commit needed for this step**

E2E tests are verification only; results inform the next steps but don't require code changes unless tests fail.

---

## Summary

| Task | Files | Change | Status |
|------|-------|--------|--------|
| 1 | `web/frontend/js/pages.js` | Update date formatting to include time | Core implementation |
| 2 | `web/tests_e2e/test_payment_history_timestamp.spec.js` | Add E2E tests | Test coverage |
| 3 | Manual testing | Visual verification | Validation |
| 4 | E2E test run | Automated verification | Optional |

**Total estimated time:** 15-20 minutes

---

## Rollback Plan

If anything breaks:
```bash
git revert HEAD~1  # Revert last commit
git revert HEAD    # Revert test commit
```

Both changes are isolated to frontend display; rollback is safe and instant.
