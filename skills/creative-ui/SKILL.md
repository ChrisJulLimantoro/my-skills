---
name: creative-ui
description: This skill should be used when the user asks to "design a UI", "make this look better", "improve the visual design", "create a creative interface", "design a component", "pick a color palette", "choose typography", "add animations", "make it more visually interesting", or "polish the look and feel". Focuses on visual creativity, aesthetics, and craft — not just functional layout.
version: 0.1.0
---

# Creative UI Designer

Design visually compelling, creative interfaces with strong aesthetic intent. Go beyond functional — make it memorable.

## Design Philosophy

Good UI design has a point of view. Before touching code or layout:

1. Identify the **emotional tone**: Should this feel playful, authoritative, minimal, expressive, calm, energetic?
2. Identify the **audience**: Who is looking at this and what do they expect to feel?
3. Identify the **one thing to make remarkable**: Not everything needs to be bold — pick one element (a heading, a button, a transition, a color) to be the visual anchor.

State these three things before proposing any visual decisions.

## Color

### Palette Construction

Build palettes with intention, not randomness:

- **Monochromatic + accent**: One hue in 5–7 shades + one high-contrast accent. Clean, confident.
- **Analogous**: Two to three adjacent hues. Harmonious, natural.
- **Complementary split**: One dominant hue + two hues adjacent to its complement. Dynamic without being harsh.

Rules:
- Limit to 3 roles: background, surface, text/content — then one accent, one semantic (error/success)
- Assign meaning consistently: the accent color should only appear on the most important interactive element per view
- Dark mode is not just inverted: darks should be slightly warm or cool-tinted, not pure `#000000`; lights rarely need to be `#ffffff`

### Contrast
- Body text on background: minimum 7:1 (AAA)
- UI component text: minimum 4.5:1 (AA)
- Use a real contrast checker — do not estimate

### Palette Output Format

When proposing a palette, output it as design tokens:

```css
:root {
  --color-bg:        #0f0f11;   /* near-black, slightly cool */
  --color-surface:   #1c1c20;   /* card/panel background */
  --color-border:    #2e2e34;   /* subtle separator */
  --color-text:      #e8e8f0;   /* primary text */
  --color-text-muted:#8888a0;   /* secondary text */
  --color-accent:    #7c6df5;   /* primary CTA, links */
  --color-accent-hover: #9b8fff;
  --color-success:   #3ecf8e;
  --color-error:     #f87171;
}
```

## Typography

### Pairing Strategy

- **Contrast pairings work**: a geometric sans (headings) + humanist sans (body), or a serif (headings) + sans (body)
- Avoid pairing two fonts from the same category with similar proportions — they fight rather than complement
- Limit to two typefaces maximum; use weight and size variation for hierarchy within each

### Type Scale

Use a modular scale (1.25× or 1.333× ratio):

| Role | Size | Weight | Line Height |
|---|---|---|---|
| Display | 48–72px | 700–800 | 1.1 |
| H1 | 36–48px | 700 | 1.2 |
| H2 | 28–36px | 600 | 1.25 |
| H3 | 22–28px | 600 | 1.3 |
| Body | 16–18px | 400 | 1.6 |
| Small / caption | 12–14px | 400–500 | 1.5 |

- Body text should almost always be 16px minimum
- Do not set `font-weight: 900` on body text
- Line length: 60–75 characters for comfortable reading (use `max-width: 65ch`)

## Layout and Spacing

### Spacing System

Use an 8px base grid. All spacing values should be multiples of 4 or 8:

```
4px  — hairline gap, icon padding
8px  — tight spacing between related items
16px — standard component padding
24px — section subdivision
32px — component separation
48px — section separation
64px — major layout divisions
```

Never use arbitrary values like 13px or 22px for structural spacing.

### Visual Hierarchy Through Space

Space is a design element, not an afterthought:
- Group related elements tightly; separate distinct groups generously
- The most important element on the page should have the most breathing room around it
- White space signals confidence — resist the urge to fill every gap

### Layout Patterns Worth Reaching For

- **Bento grid**: irregular grid of card-like blocks — visually rich, works for dashboards and marketing
- **Editorial layout**: full-bleed imagery with text overlay — high impact for hero sections
- **Asymmetric split**: 60/40 or 70/30 column split — more dynamic than equal halves
- **Sticky focal point**: one prominent element (large number, icon, illustration) that anchors the eye

## Micro-interactions and Motion

Motion communicates state. Use it purposefully:

| Trigger | Motion | Duration | Easing |
|---|---|---|---|
| Button hover | Slight scale up (1.02×) + background shift | 150ms | ease-out |
| Button press | Scale down (0.97×) | 80ms | ease-in |
| Modal appear | Fade + translate-Y from +8px | 200ms | ease-out |
| Page transition | Fade or slide | 250–350ms | ease-in-out |
| Loading state | Skeleton shimmer or subtle pulse | loop | linear |
| Success state | Brief scale bounce (1.0 → 1.05 → 1.0) | 300ms | spring |

Rules:
- Animate `transform` and `opacity` only — never `width`, `height`, `margin`, or `top`
- Respect `prefers-reduced-motion`: wrap all decorative animations in a media query
- Duration sweet spot: 100–300ms for UI feedback; 250–500ms for layout transitions

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

## Creative Elevation Techniques

When a design looks "correct but boring", reach for:

- **Noise texture overlay**: subtle grain at 3–8% opacity on backgrounds — adds tactility
- **Gradient mesh**: multi-point gradients on hero sections instead of flat color
- **Typographic scale contrast**: pair a very large (80–120px) display size with normal body text — creates drama
- **Border-radius consistency**: pick one radius scale and stick to it (e.g., 4px / 8px / 16px / full)
- **Glassmorphism** (use sparingly): `backdrop-filter: blur(12px)` + semi-transparent surface — works well for overlays on rich backgrounds
- **Expressive empty states**: illustrate or animate zero-data and loading states instead of plain text

## Output Format

For every design proposal, deliver:

1. **Stated intent**: emotional tone, audience, visual anchor
2. **Color tokens** as CSS custom properties or Swift Color assets
3. **Typography spec**: font pairing, scale table, key size/weight assignments
4. **Spacing note**: which spacing system is in use
5. **Motion spec**: key transitions with duration and easing
6. **Code**: implement the design in the appropriate framework (SwiftUI, React/Tailwind, plain CSS)
7. **What makes it remarkable**: one sentence on the deliberate creative choice that elevates this above generic
