# 🎨 Design System - Queue Buttons

## Button Specifications

### 🔴 Delete Button (X)
```css
Position: top-left (0.5rem, 0.5rem)
Size: 2.25rem × 2.25rem
Background: rgba(220, 38, 38, 0.85) + backdrop-blur(8px)
Color: white
Icon: X (cross)
Z-index: 30
```

**Hover:**
- Background: rgba(220, 38, 38, 1)
- Transform: scale(1.1)
- Shadow: 0 4px 12px rgba(220, 38, 38, 0.4)

---

### 🔵 Open Button
```css
Position: top-right (0.5rem, 0.5rem)
Size: 2.25rem × 2.25rem
Background: rgba(0, 0, 0, 0.6) + backdrop-blur(8px)
Color: white
Icon: External link
Z-index: 20
```

**Hover:**
- Background: rgba(0, 0, 0, 0.8)
- Transform: scale(1.1)

---

### 🟢 Persist Button (Save)
```css
Position: bottom-right (0.5rem, 0.5rem)
Size: 2.25rem × 2.25rem
Background: rgba(var(--primary-rgb), 0.9) + backdrop-blur(8px)
Color: white
Icon: Checkmark
Z-index: 20
```

**States:**
1. **Default**: Outline checkmark
2. **Loading**: Spinning circle (animate-spin)
3. **Success**: Filled checkmark + opacity(0.7)

**Hover:**
- Background: rgba(var(--primary-rgb), 1)
- Transform: scale(1.1)
- Shadow: 0 4px 12px rgba(var(--primary-rgb), 0.4)

---

### 🎵 Volume Button (Video only)
```css
Position: bottom-left (0.5rem, 0.5rem)
Size: 2.25rem × 2.25rem
Background: rgba(0, 0, 0, 0.6) + backdrop-blur(8px)
Color: white
Icon: Speaker (muted/unmuted)
Z-index: 20
```

**Hover:**
- Background: rgba(0, 0, 0, 0.8)
- Transform: scale(1.1)

---

### ▶️ Play/Pause Button (Video only)
```css
Position: center (50%, 50%)
Size: 3rem × 3rem
Background: rgba(0, 0, 0, 0.6) + backdrop-blur(8px)
Color: white
Icon: Play/Pause triangle
Z-index: 10
```

**Behavior:**
- Shows when paused or on hover
- Hides 1.5s after playing starts
- Always visible on hover

**Hover:**
- Background: rgba(0, 0, 0, 0.8)
- Transform: scale(1.1)

---

## Overlay Gradient

### Photo Cards
```css
Gradient: linear-gradient(to top, rgba(0,0,0,0.4), transparent 40%, rgba(0,0,0,0.2))
Opacity: 0 (default), 1 (hover)
Transition: 0.3s
```

### Video Cards
```css
Gradient: linear-gradient(to top, rgba(0,0,0,0.4), transparent 40%, rgba(0,0,0,0.2))
Opacity: 0 (default), 1 (hover or paused)
Transition: 0.3s
```

---

## Icons SVG

### Checkmark (Persist)
```svg
<svg viewBox="0 0 24 24">
  <path d="M5 13l4 4L19 7"/>
</svg>
```

### X (Delete)
```svg
<svg viewBox="0 0 24 24">
  <path d="M6 18L18 6M6 6l12 12"/>
</svg>
```

### External Link (Open)
```svg
<svg viewBox="0 0 24 24">
  <path d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
</svg>
```

### Play
```svg
<svg viewBox="0 0 24 24">
  <path d="M8 5v14l11-7z"/>
</svg>
```

### Pause
```svg
<svg viewBox="0 0 24 24">
  <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
</svg>
```

### Volume Muted
```svg
<svg viewBox="0 0 24 24">
  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
  <line x1="23" y1="9" x2="17" y2="15"/>
  <line x1="17" y1="9" x2="23" y2="15"/>
</svg>
```

### Volume On
```svg
<svg viewBox="0 0 24 24">
  <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
  <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
</svg>
```

---

## Color Variables

```css
--primary: #6366f1 (Indigo)
--primary-rgb: 99, 102, 241
--danger: rgb(220, 38, 38) (Red)
--bg-card: Dark theme card background
--text: Main text color
--muted: Muted text color
--bord: Border color
```

---

## Responsive Breakpoints

```css
/* Mobile */
@media (max-width: 640px) {
  /* 2 columns grid */
  /* Buttons stay same size (36px) */
}

/* Tablet */
@media (min-width: 641px) and (max-width: 1024px) {
  /* auto-fill grid */
}

/* Desktop */
@media (min-width: 1025px) {
  /* auto-fill grid with larger cards */
}
```

---

## Animation Timings

```css
Transitions: 0.2s ease (buttons)
Transitions: 0.3s ease (overlays, cards)
FadeInScale: 0.3s ease-out
Hover effects: instant (0s delay)
Play button hide: 1.5s delay
```
