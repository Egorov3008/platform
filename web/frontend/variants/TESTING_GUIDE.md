# Design Variants - Testing Guide

## Quick Test (30 seconds per variant)

### 1. Open Each Theme
To test each variant theme, temporarily replace the stylesheet in `index.html`:

```bash
# Current (original)
<link rel="stylesheet" href="/style.css">

# Test Swiss variant
<link rel="stylesheet" href="/variants/theme-swiss.css">

# Test Cyberpunk variant
<link rel="stylesheet" href="/variants/theme-cyberpunk.css">

# Test Organic variant
<link rel="stylesheet" href="/variants/theme-organic.css">
```

### 2. Visual Checklist (Per Theme)

#### Colors Look Right?
- [ ] Primary color visible and consistent
- [ ] Accent colors appear in buttons/links
- [ ] Text readable on backgrounds
- [ ] Badges/badges display correctly
- [ ] Status indicators (success/error) visible

#### Layout Unchanged?
- [ ] Header fixed at top
- [ ] Navigation works on mobile (hamburger)
- [ ] Main content centered and padded
- [ ] Cards/grids responsive
- [ ] Modal overlays dark but not black

#### Components Look Good?
- [ ] Buttons have proper contrast
- [ ] Form inputs show focus state
- [ ] Cards have proper depth/shadow
- [ ] Key value displays correctly
- [ ] Loading spinner visible

#### Hover States Work?
- [ ] Buttons change on hover
- [ ] Nav links highlight
- [ ] Cards lift/shadow on hover
- [ ] Links show underline or color change

#### Text Readable?
- [ ] Font size appropriate
- [ ] Line height comfortable
- [ ] Color contrast sufficient (WCAG AA)
- [ ] Headers bold and clear

---

## Detailed Test Plan

### Page: Authentication / Login

**Elements to Check:**
1. **Auth Card**
   - Background color correct
   - Border/shadow visible
   - Text readable

2. **Form Inputs**
   - Border color matches theme
   - Focus state has glow/shadow
   - Placeholder text visible

3. **Buttons**
   - Primary button color bright
   - Hover state obvious
   - Text readable on button

4. **Text**
   - Subtitle gray color correct
   - Error messages visible
   - Links colored properly

**Expected Result:** Auth flow feels welcoming, buttons are clear CTAs, form is easy to use.

---

### Page: Dashboard / Keys List

**Elements to Check:**
1. **Section Header**
   - "Your Keys" title visible
   - "Add Key" button prominent
   - Colors match theme

2. **Key Cards**
   - Background correct
   - Border visible or shadow present
   - Badges (Active/Expiring/Expired) colored correctly
   - Hover effect visible

3. **Key Display**
   - Gradient background correct
   - Text white and readable
   - Copy button visible and clickable
   - Shadow/glow around key area

4. **Actions**
   - Delete, Renew buttons properly styled
   - Danger button (delete) red/visible
   - Hover states clear

5. **Empty State** (if no keys)
   - Icon visible
   - Message readable
   - CTA button prominent

**Expected Result:** Keys are easy to scan and manage, key value stands out, actions are clear.

---

### Page: Tariffs

**Elements to Check:**
1. **Section Header**
   - "Select Tariff" or similar visible
   - Colors match theme

2. **Tariff Cards** (for each tariff)
   - Card border/shadow correct
   - Top accent bar visible (if design includes)
   - Card name readable
   - Price stands out and is readable
   - Features list formatted correctly
   - Feature check marks visible

3. **Buttons**
   - CTA button prominent
   - Hover/active states clear
   - Button text readable

4. **Grid Layout**
   - Cards responsive (3 cols → 2 cols → 1 col)
   - Spacing consistent
   - No overlaps on mobile

5. **Hover Effects**
   - Cards lift when hovered
   - Pricing color changes (if applicable)
   - Button highlights on hover

**Expected Result:** Tariffs are easy to compare, prices jump out, CTAs are obvious, mobile experience is clean.

---

### Page: Payment Modal

**Elements to Check:**
1. **Modal Overlay**
   - Background dark/visible
   - Modal centered and readable

2. **Modal Header**
   - Tariff name clearly displayed
   - Font/color correct

3. **Month Selector**
   - Plus/minus buttons visible
   - Disabled state (greyed out) when at limits
   - Month count displayed
   - Colors match theme

4. **Pricing Display**
   - Calculation shown clearly
   - Base price, discount, total visible
   - Green color for discount
   - Font sizes readable

5. **Action Buttons**
   - Cancel and Pay buttons visible
   - Pay button prominent color
   - Hover states work

**Expected Result:** Payment flow is clear, numbers are easy to read, month selection is intuitive.

---

### Page: Admin Dashboard

**Elements to Check:**
1. **Metrics Grid** (4 columns on desktop)
   - Cards have consistent spacing
   - Numbers large and readable
   - Labels visible
   - Colors match theme

2. **Tabs** (if present)
   - Tab buttons visible
   - Active tab highlighted
   - Border/underline visible

3. **Data Table**
   - Headers styled correctly
   - Text aligned properly
   - Row hover visible
   - Alternating row colors (if applicable)

4. **Action Buttons**
   - Delete/Edit buttons visible
   - Danger buttons red/visible
   - Hover states work

**Expected Result:** Admin can see metrics at a glance, table is scannable, actions are clear.

---

## Mobile Testing

### Viewport Sizes to Test:
- [ ] **360px** (small phone)
- [ ] **480px** (medium phone)
- [ ] **768px** (tablet)
- [ ] **1024px** (desktop)

### Mobile Checklist:
- [ ] **Hamburger Menu**: Visible on small screens, works smoothly
- [ ] **Touch Targets**: All buttons at least 44x44px (easy to tap)
- [ ] **Text Size**: Readable without zoom
- [ ] **Input Fields**: Large enough for typing
- [ ] **Grid Layout**: Cards stack properly, no overflow
- [ ] **Modals**: Fit on screen, scrollable if needed
- [ ] **Colors**: Same on both light and dark phone backgrounds

---

## Color Contrast Testing

### Use Tools:
- **WCAG Contrast Checker**: https://webaim.org/resources/contrastchecker/
- **Chrome DevTools**: Inspect → Accessibility tab
- **Lighthouse**: Chrome → Lighthouse report

### Check These Combinations:
- [ ] Primary text on primary button
- [ ] Secondary text on background
- [ ] Link color on background
- [ ] Badge colors (success/error/warning)
- [ ] Input text on input background
- [ ] Placeholder text on input background

**Target:** WCAG AA (4.5:1 for normal text, 3:1 for large text)

---

## Performance Testing

### Check Loading:
```bash
# Open browser DevTools
# Network tab → CSS file size
# Should be < 50KB
```

### Check Animations:
- [ ] Hover effects are smooth
- [ ] No lag on button clicks
- [ ] Animations don't cause layout shift
- [ ] Spinner animation smooth

### On Slow Devices:
- [ ] Use Chrome DevTools throttling
- [ ] Set to "Slow 4G"
- [ ] Verify page still responsive

---

## Feedback Questions

After testing, answer these for each variant:

### First Impression (0-3 seconds)
- [ ] What's the first thing you notice?
- [ ] What feeling does it evoke?
- [ ] Does it feel like a VPN app?

### Usability (3-10 seconds)
- [ ] Can you find the main action (add key, buy tariff)?
- [ ] Is the layout clear?
- [ ] Do colors feel natural or forced?

### After 1 Minute
- [ ] Do you remember the color scheme?
- [ ] Did anything stand out as weird?
- [ ] Would you recognize this app later?

### Comparison (After all 3)
- [ ] Which felt most professional?
- [ ] Which was most memorable?
- [ ] Which would you choose?

---

## Variant Summaries for Quick Reference

### Swiss 🇨🇭
- **Colors**: Teal + white + subtle grays
- **Feel**: Professional, refined, minimal
- **Vibe**: High-end, trustworthy
- **Font**: Helvetica Neue (clean, European)
- **Effect**: Micro-shadows, thin borders, generous spacing
- **Best For**: Enterprise/business users

### Cyberpunk 🚀
- **Colors**: Neon pink + cyan + dark black
- **Feel**: Bold, futuristic, intense
- **Vibe**: Tech-forward, high-energy, cutting-edge
- **Font**: Monospace (hacker aesthetic)
- **Effect**: Glows, shimmer, neon borders, animated elements
- **Best For**: Tech enthusiasts, gaming audience

### Organic 🌿
- **Colors**: Warm orange + soft purple + cream
- **Feel**: Friendly, approachable, warm
- **Vibe**: Human, welcoming, creative
- **Font**: Georgia/Trebuchet (humanistic)
- **Effect**: Soft shadows, playful animations, gradient overlays
- **Best For**: General consumers, accessibility-focused

---

## A/B Testing Setup

To show different users different themes:

```javascript
// In pages.js or auth.js
const theme = localStorage.getItem('selectedTheme') || 'original';
document.querySelector('link[rel="stylesheet"]').href = 
    theme === 'original' ? '/style.css' :
    theme === 'swiss' ? '/variants/theme-swiss.css' :
    theme === 'cyberpunk' ? '/variants/theme-cyberpunk.css' :
    '/variants/theme-organic.css';
```

Then track which theme users choose/stay with.

---

## Notes for Development

- All variants use CSS custom properties (CSS variables)
- No additional JavaScript needed for theme switching
- Animation performance depends on device
- Consider prefers-reduced-motion for accessibility
- All variants responsive and mobile-first

---

## Questions?

If something looks off:
1. Check the CSS file for typos
2. Clear browser cache (Ctrl+Shift+Delete)
3. Check color variables in `:root`
4. Verify font-family imports (if any)
5. Test in different browser

Ready to test! 🎨
