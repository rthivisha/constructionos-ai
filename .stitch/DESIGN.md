# Design System: ConstructionOS Modern Sleek UI

## 1. Visual Theme & Atmosphere
A high-precision, architectural dark-mode cockpit designed for industrial construction operations. The atmosphere is restrained, tactical, and ultra-crisp — balancing deep obsidian tones with luminous status indicators (Emerald, Crimson, Amber, and Precision Cyan). Interfaces emphasize high information density with immaculate spatial separation, micro-borders, and tactile hardware-feel interactions.

## 2. Color Palette & Functional Roles
- **Base Obsidian Canvas** (`#090D16`) — Background surface for the application container.
- **Card Panel Base** (`#0F172A`) — Structural card panels, container backgrounds, and section groupings.
- **Elevated Interactive Surface** (`#162036`) — Input boxes, hover surfaces, and sub-card containers.
- **Subtle Structural Border** (`rgba(255, 255, 255, 0.08)`) — 1px micro-borders separating cards and modules.
- **Active / Focused Border** (`rgba(56, 189, 248, 0.5)`) — Focused inputs and active card highlights.
- **Command Accent** (`#0284C7` / `#0EA5E9`) — Primary CTA buttons, key action triggers, and primary progress accents.
- **Safety Status Halts** (`#EF4444` / `#DC2626`) — Hard stops, OSHA violations, critical warnings, and blocked pipeline gates.
- **Safety Status Continue** (`#10B981` / `#059669`) — Clear safety checks, approved clearances, and verified controls.
- **Safety Status Conditional** (`#F59E0B` / `#D97706`) — Pending verification gates, trade-off advisories, and conditional flags.
- **Primary Text** (`#F8FAFC`) — High-contrast headlines, primary labels, and critical metrics.
- **Secondary Text** (`#94A3B8`) — Explanatory copy, field descriptions, and metadata.
- **Muted Steel Text** (`#64748B`) — Sub-labels, inactive states, and timestamps.

## 3. Typography Architecture
- **Display & Section Headers:** `Outfit`, sans-serif — Track-tight (`tracking-tight`), weight 700/800, high contrast.
- **Body & Data Labels:** `Inter`, ui-sans-serif — Clean, neutral, high legibility at 12px–14px with relaxed line height.
- **Monospace Technical Fields:** `JetBrains Mono`, `Geist Mono`, ui-monospace — Strictly enforced for Task IDs (`T-101`, `T-104`), currency calculations, latencies, and payload metadata.

## 4. Spacing & Shape Tokens
- **Corner Radii:**
  - Outer Containers & Primary Cards: `1.25rem` (`20px`, `rounded-2xl`)
  - Inputs & Action Buttons: `0.75rem` (`12px`, `rounded-xl`)
  - Badges, Scenario Chips & Tags: `0.5rem` (`8px`, `rounded-lg`)
- **Spacing Scale:** Standard 4px grid (`p-3`, `p-4`, `p-6`, `gap-3`, `gap-6`, `space-y-6`).

## 5. Component Stylings (EventInput & Dashboard)
- **Dashboard Header:** Minimal glassmorphism bar with glowing brand glyph and live status badge.
- **EventInput Container:** Glass-morphic card with `backdrop-blur-xl`, `bg-slate-900/60`, and subtle `border-white/10`.
- **Quick-Scenario Template Chips:** Interactive capsule pills with category badges and crisp hover transitions (`hover:border-sky-500/40 hover:bg-sky-950/30`).
- **Input Textarea:** Deep slate fill (`bg-slate-950/80`), inset focus border (`focus:border-sky-500`), and zero distracting scrollbars.
- **Attachment Trigger & Pill:** Tactile button for file selection + floating chip displaying file icon, filename, size, and clear button.
- **Run Pipeline CTA:** Solid, high-contrast command blue gradient button (`from-sky-500 to-blue-600`) with subtle active scale (`active:scale-[0.98]`) and spinner animation.

## 6. Motion & Micro-Interactions
- **Transitions:** `transition-all duration-200 ease-out` for all hover states.
- **Pulse Indicators:** Perpetual subtle pulse on live stream indicators (`animate-pulse`).
- **Loading State:** Clean SVG spinner with glowing radial trail.

## 7. Anti-Patterns (Banned)
- ❌ No generic neon purple gradients or oversaturated glows.
- ❌ No emojis in functional badges or technical status readouts.
- ❌ No altered data-binding variables or modified API schemas.
- ❌ No pure black backgrounds (`#000000`) without elevation depth.
