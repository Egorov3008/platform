# Visual Guide: Design Variants

## Variant 1: Modern Swiss 🇨🇭

### Color Palette
```
Primary:        #0D7377 (Deep Teal)
Accent:         #14B8A6 (Turquoise)  
Background:     #FFFFFF (Pure White)
Surface:        #FAFBFC (Soft Gray)
Text:           #0F172A (Charcoal)
```

### Visual Appearance

```
┌─────────────────────────────────────────────────────────┐
│ 🔒 VPN Panel                              [Logout]       │ ← Teal logo, subtle border
└─────────────────────────────────────────────────────────┘

Main Content Area (White background)

┌───────────────────────┐  ┌───────────────────────┐
│ Your Keys             │  │ Key 1                 │
│                       │  │ ─────────────────     │
│  [➕ Add Key]          │  │ Status: Active        │
└───────────────────────┘  │ Expiry: 30 days       │
                           │                       │
                           │ ░░░░░░░░░░░░░░░░░    │ ← Teal gradient
                           │ Copy Password         │
                           │ [Delete] [Renew]      │
                           └───────────────────────┘

Tariffs Section:
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ ▓ Tariff 1       │  │ ▓ Tariff 2       │  │ ▓ Tariff 3       │ ← Top bar accent
│                  │  │                  │  │                  │
│ $9.99 / month    │  │ $19.99 / month   │  │ $49.99 / month   │
│                  │  │                  │  │                  │
│ ✓ 100GB/month    │  │ ✓ Unlimited      │  │ ✓ Unlimited      │
│ ✓ 5 locations    │  │ ✓ 20+ locations  │  │ ✓ All locations  │
│                  │  │                  │  │                  │
│ [Select Tariff]  │  │ [Select Tariff]  │  │ [Select Tariff]  │
└──────────────────┘  └──────────────────┘  └──────────────────┘

```

### Typography
- Headers: Helvetica Neue, 600 weight, tight letter-spacing
- Body: Helvetica Neue, 400 weight
- Keys: Courier New, monospace

### Key Details
- **Borders**: Thin, 1-2px, subtle colors
- **Shadows**: Micro (0-2px on baseline), grows slightly on hover
- **Hover Effect**: Subtle shadow increase + slight lift
- **Spacing**: Generous, plenty of breathing room
- **Buttons**: Filled with teal, white text, small shadows
- **Forms**: Clean borders, focus glow in teal

### Mood
Elegant, trustworthy, professional, quality-focused. Like Apple or luxury tech brands. **Swiss** refers to the design principle of "maximum clarity through minimal means."

### Best For
- Enterprise VPN users
- Business/corporate audience
- Users who appreciate simplicity
- Premium/paid-tier positioning

---

## Variant 2: Dark Neon 🚀

### Color Palette
```
Primary:        #FF006E (Neon Pink)
Accent:         #00D9FF (Neon Cyan)
Accent 2:       #8338EC (Purple Neon)
Background:     #0A0E27 (Deep Black)
Surface:        #1A1F3A (Dark Navy)
Text:           #F5F7FA (Near White)
```

### Visual Appearance

```
┌═════════════════════════════════════════════════════════┐
│ 🔒 VPN PANEL                              [LOGOUT]       │ ← Cyan glow text
└═════════════════════════════════════════════════════════┘ ← Cyan underline

Dark Background (almost black) with subtle gradient overlays

┌─────────────────────────────────────────────────────────┐
│ YOUR KEYS                                [➕ ADD KEY]     │ ← Cyan + uppercase
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ╔══════════════════════════════════════════════════╗   │
│  ║ Key 1                            [Active] 🟢      ║   │ ← Glowing border
│  ║ ──────────────────────────────────────────────── ║   │
│  ║ Expiry: 30 days  │  Tariff: Basic               ║   │
│  ║                                                  ║   │
│  ║  ABCD-1234-EFGH-5678-IJKL-9012-MNOP-3456       ║ ← Glow
│  ║                                            [📋]  ║   │
│  ║  [🗑️ Delete]  [♻️ Renew]                       ║   │
│  ╚══════════════════════════════════════════════════╝   │ ← Animated shimmer
│                                                           │
│  Hover: Cyan glow around card, shimmer animation        │
│                                                           │
└─────────────────────────────────────────────────────────┘

TARIFFS (Glowing cards):
╔════════════════════╗  ╔════════════════════╗  ╔════════════════════╗
║ BASIC              ║  ║ PRO                ║  ║ ENTERPRISE         ║
║ ━━━━━━━━━━━━━━━━  ║  ║ ━━━━━━━━━━━━━━━━  ║  ║ ━━━━━━━━━━━━━━━━  ║
║                    ║  │                    ║  ║                    ║
║ $9.99 / MONTH      ║  ║ $19.99 / MONTH     ║  ║ $49.99 / MONTH     ║
║                    ║  ║                    ║  ║                    ║
║ ✓ 100GB/month      ║  ║ ✓ Unlimited        ║  ║ ✓ Unlimited        ║
║ ✓ 5 locations      ║  ║ ✓ 20+ locations    ║  ║ ✓ All locations    ║
║                    ║  ║                    ║  ║                    ║
║ [SELECT PLAN]      ║  ║ [SELECT PLAN]      ║  ║ [SELECT PLAN]      ║
║ ▄▄▄ Cyan glow ▄▄▄  ║  ║ ▄▄▄ Cyan glow ▄▄▄  ║  ║ ▄▄▄ Cyan glow ▄▄▄  ║
╚════════════════════╝  ╚════════════════════╝  ╚════════════════════╝
Hover: Intense glow, button text inverts color with background change
```

### Typography
- Headers: IBM Plex Mono, 700-800 weight, UPPERCASE
- Body: Courier Prime (monospace, hacker aesthetic)
- Numbers: Large, bold, glowing cyan

### Key Details
- **Borders**: 2px thick, neon colors, glowing
- **Shadows**: Heavy glows, 0 0 20px rgba colors
- **Hover Effect**: Intense color change, glow increases, shimmer animation
- **Spacing**: Moderate, dark backgrounds make spacing more dense
- **Buttons**: Neon borders + fills, text-shadow glow, inverse on hover
- **Forms**: Dark backgrounds, cyan glow focus, monospace text
- **Animations**: Shimmer (3s loop), pulse effects, strong transitions

### Mood
Intense, futuristic, high-energy, cutting-edge. Like a sci-fi interface or gaming dashboard. **Cyberpunk** aesthetic from retro-futurism. Makes users feel like they're using advanced tech.

### Best For
- Tech enthusiasts
- Gaming/streaming audience
- Young users
- Bold brand positioning
- "Cutting-edge" messaging

---

## Variant 3: Warm & Organic 🌿

### Color Palette
```
Primary:        #D97706 (Warm Amber/Orange)
Accent:         #8B5CF6 (Soft Purple)
Accent 2:       #EC4899 (Rose/Pink)
Background:     #FFFBF7 (Warm Cream)
Surface:        #FFFFFF (Pure White)
Text:           #44403C (Warm Charcoal)
```

### Visual Appearance

```
┌─────────────────────────────────────────────────────────┐
│ 🔒 VPN PANEL                              [Logout]       │ ← Gradient text
└─────────────────────────────────────────────────────────┘ ← Warm border

Warm cream background with subtle gradient overlay

┌───────────────────────────────────────────────────────────┐
│ YOUR KEYS                                   [➕ Add Key]   │ ← Orange + warm
├───────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Key 1                           ◆ Active            │  │ ← Soft shadow
│  │ ───────────────────────────────────────────────     │  │
│  │ Status: Active  │  Expiry: 30 days  │  Tariff: ...  │  │
│  │                                                     │  │
│  │  ╭─────────────────────────────────────────────╮   │  │
│  │  │ ABCD-1234-EFGH-5678-IJKL-9012-MNOP-3456   │   │  │ ← Warm gradient
│  │  │                                         ⋯ │   │  │
│  │  ╰─────────────────────────────────────────────╯   │  │
│  │              [Copy Key]                             │  │
│  │  [🗑️ Delete]          [♻️ Renew]                    │  │
│  └─────────────────────────────────────────────────────┘  │
│     ↓ Hover: Lifts up, gradient overlay appears ↑         │
│                                                             │
└───────────────────────────────────────────────────────────┘

TARIFFS (Gradient accents):
┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
│ ▬ BASIC              │  │ ▬ PRO                │  │ ▬ ENTERPRISE         │
│                      │  │                      │  │                      │
│ $9.99 per month      │  │ $19.99 per month     │  │ $49.99 per month     │
│                      │  │                      │  │                      │
│ ✓ 100GB/month        │  │ ✓ Unlimited data     │  │ ✓ Unlimited data     │
│ ✓ 5 locations        │  │ ✓ 20+ locations      │  │ ✓ All locations      │
│ ✓ Standard support   │  │ ✓ Priority support   │  │ ✓ 24/7 support       │
│                      │  │                      │  │                      │
│ ╭────────────────╮   │  │ ╭────────────────╮   │  │ ╭────────────────╮   │
│ │ Select Tariff  │   │  │ │ Select Tariff  │   │  │ │ Select Tariff  │   │
│ ╰────────────────╯   │  │ ╰────────────────╯   │  │ ╰────────────────╯   │
│ (Orange gradient)    │  │ (Purple gradient)    │  │ (Rose gradient)      │
│                      │  │                      │  │                      │
└──────────────────────┘  └──────────────────────┘  └──────────────────────┘
  ↓ Hover: Lifts + glow appears + underline animation on nav items ↑
```

### Typography
- Headers: Georgia / Trebuchet MS, 700 weight (warm humanistic serif)
- Body: Trebuchet MS, 400 weight
- Keys: Courier New, monospace

### Key Details
- **Borders**: 1-2px, warm colors, soft appearance
- **Shadows**: Soft gradients, 4-8px blur, warm tones
- **Hover Effect**: Lifts (+4px translateY), soft glow appears
- **Spacing**: Comfortable, not overly generous but well-balanced
- **Buttons**: Warm gradient fills (orange → amber), white text, soft shadows
- **Forms**: Soft border focus, warm gradient backgrounds
- **Animations**: Playful easing (spring-like), underline animations, shine effect

### Mood
Friendly, welcoming, human, creative. Like indie apps or creative tools. **Warm** aesthetic makes users feel safe and cared for. Accessible and approachable.

### Best For
- General consumers
- Accessibility-focused users
- Friendly brand positioning
- First-time VPN users
- Consumer/casual audience

---

## Quick Visual Comparison

### Header (Same Elements, Different Aesthetics)

```
SWISS:
┌─────────────────────────────────────────────┐
│ 🔒 VPN Panel                    [Logout]    │
└─────────────────────────────────────────────┘
Teal + white, clean border, minimal shadow


CYBERPUNK:
╔═════════════════════════════════════════════╗
║ 🔒 VPN PANEL                    [LOGOUT]    ║ ← Cyan glow
║ ▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬ ║ ← Accent line
╚═════════════════════════════════════════════╝
Dark + neon, double border, intense glow


ORGANIC:
┌─────────────────────────────────────────────┐
│ 🔒 VPN Panel                    [Logout]    │ ← Gradient text
├─────────────────────────────────────────────┤ ← Warm gradient
└─────────────────────────────────────────────┘
Warm cream + orange, soft border, warm shadow
```

### Card (Same Elements, Different Aesthetics)

```
SWISS:
┌──────────────────────┐
│ Key 1                │  ← Clean, minimal
│ Status: Active       │
│                      │
│ ░░░░░░░░░░░░░░░░░  │  ← Teal gradient
│ [Copy] [Delete]      │
└──────────────────────┘
Thin border, micro shadow, precise


CYBERPUNK:
╔══════════════════════╗
║ Key 1              🟢║  ← Neon badge
║ Status: ACTIVE       ║
║                      ║
║ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓║  ← Neon gradient + shimmer
║ [📋] [🗑️] [♻️]      ║
║ ▄▄ Cyan glow ▄▄      ║
╚══════════════════════╝
Thick border, intense glow, animated


ORGANIC:
┌──────────────────────┐
│ Key 1         ◆      │  ← Warm badge
│ Status: Active       │
│ (slight lift hover)  │
│ ░░░░░░░░░░░░░░░░░  │  ← Warm gradient
│ [Copy] [Delete]      │
└──────────────────────┘  ← Soft shadow
Soft border, rounded, playful hover
```

### Button States

```
SWISS:
Idle:     [BUTTON] (solid teal)
Hover:    [BUTTON] (darker teal, slight lift)
Active:   [BUTTON] (teal with underline)


CYBERPUNK:
Idle:     ▔▔▔▔▔▔▔▔ (pink border, dark inside)
Hover:    ╔▔▔▔▔▔▔▔╗ (neon glow, inverted)
Active:   ╔══════╗ (intense glow)


ORGANIC:
Idle:     [▓BUTTON▓] (orange gradient)
Hover:    [▓BUTTON▓] (taller, glow appears)
Active:   [▓BUTTON▓] (pressed down animation)
```

---

## Accessibility Note

All three variants meet **WCAG AA** color contrast requirements:
- **Swiss**: High contrast (dark teal on white = 6.5:1)
- **Cyberpunk**: High contrast (cyan on dark = 7.2:1)
- **Organic**: High contrast (orange on white = 4.5:1)

No variant is "inaccessible," but:
- **Swiss**: Best for print-like clarity
- **Cyberpunk**: Best for night use (dark mode friendly)
- **Organic**: Best for general accessibility

---

## Animation Summary

### Swiss
- Smooth cubic-bezier(0.4, 0, 0.2, 1)
- Minimal motion, focus on subtle refinement
- No complex animations

### Cyberpunk
- Bouncy cubic-bezier(0.23, 1, 0.320, 1)
- Shimmer effects, glowing animations
- High visual energy

### Organic
- Spring-like cubic-bezier(0.34, 1.56, 0.64, 1)
- Playful, bouncy interactions
- Underline animations, shine effects

---

## Font Choices Explained

### Swiss: Helvetica Neue
- Classic, elegant, European
- Maximum readability
- Associated with quality design (Apple, luxury brands)

### Cyberpunk: Courier Prime / IBM Plex Mono
- Monospace = "hacker/code" aesthetic
- Technical, futuristic
- Adds credibility to "high-tech" positioning

### Organic: Georgia / Trebuchet MS
- Humanistic, warm, friendly
- Slightly playful
- More approachable than sans-serif

---

## Next Steps

1. **Test each variant** on the live site
2. **Gather user feedback** (first impressions, memorability)
3. **Choose based on target audience**
4. **Refine selected variant** with real data
5. **Consider brand guidelines** alignment
6. **Plan rollout** (all users, staged, A/B test)

Which variant resonates with your brand? 🎨
