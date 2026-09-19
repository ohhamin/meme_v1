# MEME AI INVEST Design System v1

This document is the source of truth for all future mobile UI work in `meme_v1`.

## Brand idea

MEME AI INVEST should feel like a modern, trustworthy fintech product rather than a trading terminal.

Core ideas:

- data-driven investing
- calm confidence
- measurable growth
- dark premium fintech UI
- blue/cyan/purple brand gradient
- rounded, compact surfaces
- strong information hierarchy
- restrained use of glow and gradients

The brand mark is a ribbon-like `M` that continues into an upward arrow. The mark represents analysis flowing into action and growth.

## Source assets

- `mobile/assets/brand/meme_mark.svg`
- `mobile/assets/brand/meme_lockup.svg`
- Flutter-native mark: `mobile/lib/widgets/brand_logo.dart`
- Android adaptive icon: `mobile/android/app/src/main/res/drawable/ic_meme_mark.xml`

The Flutter-native mark is preferred inside the app because it scales cleanly without raster assets.

## Color tokens

Defined in `mobile/lib/theme/app_theme.dart`.

| Token | Value | Purpose |
|---|---|---|
| background | #07111F | primary app background |
| backgroundSoft | #0A1627 | navigation / secondary background |
| surface | #0E1C2F | standard cards |
| surfaceElevated | #13243A | inputs / elevated cards |
| border | #1E3857 | card/input borders |
| textPrimary | #F5F8FF | main text |
| textSecondary | #A0B2C9 | supporting text |
| textMuted | #71839B | quiet labels |
| primary | #2FD8FF | cyan brand accent |
| primaryBlue | #2F7BFF | action blue |
| primaryPurple | #8B5CFF | AI / gradient accent |
| positive | #21D49B | profit / healthy status |
| negative | #FF6275 | loss / destructive state |
| warning | #FFBF5B | warning / insufficient sample |

## Brand gradient

Primary gradient:

`cyan → blue → purple`

Use it for:

- logo mark
- hero sections
- very high-emphasis brand moments

Do not use gradients on every card or button.

## Layout

Use the spacing tokens from `AppSpacing`.

- 4: micro spacing
- 8: compact spacing
- 12: related items
- 16: standard internal spacing
- 20: screen horizontal padding
- 24: large block spacing
- 28: section spacing

Screen horizontal padding should normally remain 20.

## Radius

Use `AppRadius`.

- 10: compact controls
- 14: inputs / buttons
- 20: cards
- 26: hero / modal surfaces
- pill: status chips

Avoid square cards unless the component is intentionally data-grid-like.

## Typography

Prefer existing Material text styles via `Theme.of(context).textTheme`.

Hierarchy:

1. `headlineMedium`: portfolio value / major result
2. `titleLarge`: section title / important entity
3. `titleMedium`: card title
4. `bodyMedium`: normal information
5. `bodySmall`: supporting metadata

Do not create arbitrary font sizes unless a brand component specifically needs them.

## Shared components

Prefer these before creating local variants:

- `AppSurface`
- `SectionTitle`
- `AppEmptyState`
- `BrandMark`
- `BrandLockup`
- `BrandAppBarTitle`
- `BrandHero`

If a new reusable UI pattern appears in two or more screens, move it into a shared widget.

## Cards

All standard cards should:

- use `AppSurface`
- use subtle gradient surface
- have a 1px brand border
- use minimal dark shadow
- avoid heavy glow
- keep primary numeric result visually dominant

## Semantic finance colors

Use semantic colors only for meaning:

- green: positive return / connected / safe
- red: negative return / destructive / live-risk warning
- amber: caution / insufficient sample / degraded state
- cyan/blue: neutral product action / selection
- purple: AI/algorithm context

Never use green just because something is selectable.

## Paper vs Live

Paper and Live must remain visually distinct.

Paper:
- cyan/green leaning
- calm test-state language

Live:
- red/amber safety emphasis
- show safety gates clearly
- never make Live look like a celebratory state

## Candidate score vs AI decision score

These are separate concepts and must stay visually and verbally distinct.

Candidate score:
- screener quality / whether the stock deserves analysis
- use cyan/blue

AI decision score:
- directional BUY/HOLD/SELL conviction
- use action-specific semantic color only when appropriate

Always keep the wording `후보 점수 ≠ 매수 점수` where ambiguity is possible.

## Charts and performance

Performance visuals should default to:

- dark surface
- minimal grid lines
- no unnecessary legends
- show sample count next to rates
- show insufficient sample warnings under 10 closed trades

## Buttons

Primary actions:
- blue/cyan emphasis

Secondary actions:
- outlined border

Destructive / Live-confirm actions:
- explicit red styling and confirmation

Do not use full-width gradient buttons by default. Gradient is reserved for brand moments, not routine controls.

## Navigation

Bottom navigation uses:

- dark secondary background
- cyan selected icon/label
- muted blue-gray inactive state
- soft blue selected indicator

Every top-level screen uses `BrandAppBarTitle` so the product identity stays consistent.

## Future development rule

All future Flutter UI changes should follow this file and the tokens/components in `app_theme.dart`.

When adding a new design choice:

1. check whether a token/component already exists
2. reuse it if possible
3. if the pattern is reusable, add it to the design system first
4. update this document when introducing a new global visual rule

Do not introduce a separate color palette, radius system, or card language inside individual feature screens.
