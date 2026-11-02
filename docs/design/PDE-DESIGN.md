# PDE dashboard design handoff

Extracted from the Portfolio Decarbonisation Engine (PDE) app. Use it to keep a second dashboard
visually consistent with it. Start with `reference/*.html` (open in a browser) to see the look,
then copy the tokens and kit CSS.

## Contents

| Folder | What |
|---|---|
| `css/app/01-tokens-shell.css` | **Start here.** `:root` tokens (colour, radius, shadow, font, easing), base body, 3-column shell, left nav, View block |
| `css/app/16-kit.css` | Shared component kit: type scale, status tags `.ktag`, switches `.ksw`, chips `.kchip`, KPI strip `.kstrip`, sortable table, sheets, toasts |
| `css/app/*.css` (other) | Page-specific styles (measure card, tray board, canvas, etc.), useful as examples of the tokens in use |
| `css/card_kit.css`, `overview.css`, `register.css`, `cash_flow.css` | Tool-level styles (tables, charts, cash flow) |
| `css/brand.css` | Logo placement rules |
| `js/card_kit.js` | `Kit.ui` builders (tag, sw, chips, strip, table) that emit the HTML the kit CSS styles |
| `spec/shared-kit.md` | Written spec of the kit: type scale, component APIs |
| `brand/` | Logos, wordmark, icon (SVG, PNG, favicon) and `README.md` with usage rules |
| `fonts/` | Geist, Geist Mono, serif + italic (woff2) |
| `reference/` | Rendered HTML pages and a screenshot showing the design in use |

## Design language

- **Feel:** calm, light, flat. White cards on a faint lilac-grey page, thin borders, soft shadows,
  generous radii, purple as the single primary. No gradients on surfaces.
- **Colour tokens**
  - Primary purple `--purple #6D28D9`, hover `--purple-600 #5B21B6`, tint `--purple-050 #F2ECFD`,
    `--purple-100 #E4D8FB`, `--purple-200 #C4ACF2`, deep `--deep #2A1052` (avatars, dark accents)
  - Text `--ink #1A1622`, `--ink-2 #5A5566`, `--ink-3 #6B6577`
  - Surfaces `--bg #F6F5F8`, `--bg-2 #EFEDF3`, `--surface #FFFFFF`, borders `--line #E7E4EE`, `--line-2 #DAD6E4`
  - Status: ok `#12805F` on `#E5FAF0`; error `#B4231F` on `#FDE7E7`; **"needs a look" burnt orange
    `--need #C2410C`** on `#FFF4ED` (used only as the marker dot / tag, never as a general warning colour)
  - Accents (charts, highlights): blue `#0B41CD`, pink `#FF3D8B`, green `#0FB86E` (each with -050 / -600 shades)
- **Radius:** `--r-lg 16`, `--r-md 14`, `--r-sm 10`, `--r-xs 6`, pills `999px`, chart bars `3px` (sharper than the UI)
- **Shadow:** `--sh-1` (cards), `--sh-2` (popovers)
- **Type:** Geist (UI), Geist Mono (numbers/code), fallback Segoe UI. Base 15px, letter-spacing -0.011em.
  Scale is 10 / 10.5 / 11 / 11.5 / 12 / 12.5 / 13 / 14 / 15 / 16 px via `--fs-*`. Nothing smaller, nothing
  off-scale. Uppercase micro-labels: 10.5-11px, weight 600-700, letter-spacing .05-.08em, `--ink-3`.
- **Icons:** Material Symbols Outlined (variable font, class `.ms`; weight 300 at 18px and below, 400 above).
  The font is embedded as base64 in `css/app/11-compare-tiles.css`; regenerate with `tools/fetch_symbols.py` in the source repo if needed.
- **Motion:** `--ease cubic-bezier(.16,.84,.44,1)`; hovers .14-.18s, layout changes .7s. Disable transitions while dragging.
- **Layout:** full-height 3-column grid: account nav (64px collapsed / 236px wide), assistant rail
  (384px, resizable via `--railw`), main canvas (1fr). Nav items 36px high, radius `--r-sm`; the active item is
  `--purple-050` with `--purple-600` text, weight 600. Primary button: purple, 36px high, `--r-md`, soft purple glow shadow.
- **Components:** status tag = pill with a 6px dot (green on, grey off, dashed outline n/a, purple edited/running).
  KPI tiles = `.kstrip` 1-5 across. Tables: sortable, 11px heads, 12.5px body, right-aligned numbers.

## Setting up the new dashboard

1. Load fonts (`@font-face` for `fonts/*.woff2`, families "Geist" and "Geist Mono") or embed as base64.
2. Paste the `:root` block and body rules from `01-tokens-shell.css` first; then `16-kit.css`.
3. Build layout with the grid shell; use `Kit.ui` (or the same class names) for tags, chips, KPI strips, tables.
4. Use `brand/` assets only per `brand/README.md`. If this is a different product, swap the logo but keep the tokens.
5. Do not introduce new colours, radii or font sizes; extend the tokens instead.

## Caveats

- CSS files are fragments of a larger single-file build and depend on each other's variables; `16-kit.css`
  needs `01-tokens-shell.css`. Some page CSS references app-specific selectors and can be ignored.
- Source repo: Real-Estate-Decaronbisation-Engine (`engine/app-v2/src/css`, `engine/brand`, `engine/docs`).
