# MEME AI INVEST Design System v2

This document is the source of truth for all future mobile UI work in `meme_v1`.

## Reference direction

The visual reference approved on 2026-09-20 is the dark MEME AI INVEST brand board with:

- an almost-black navy background
- a glossy ribbon-like `M` that continues into an upward arrow
- cyan / electric blue / violet / magenta accents
- white `MEME` wordmark and widely tracked `AI INVEST`
- thin blue borders rather than bright filled panels
- rounded-square icon tiles
- restrained glow around brand elements only
- compact, premium fintech information hierarchy

The app should feel close to that board. A generic Material dark theme or a simple line-chart logo is not considered an acceptable substitute.

## Product identity

Brand lockup:

- `MEME`
- `AI INVEST`
- tagline: `데이터가 만드는 더 나은 선택`

Brand mark:

- a soft ribbon-shaped M
- blue/cyan on the left
- violet/magenta in the center fold
- cyan rising stroke and arrow on the right
- rounded terminals and a small glossy highlight
- dark navy rounded background when used as the launcher icon

## Source assets

- Flutter brand renderer: `mobile/lib/widgets/brand_logo.dart`
- SVG mark source: `mobile/assets/brand/meme_mark.svg`
- SVG lockup source: `mobile/assets/brand/meme_lockup.svg`
- Android adaptive foreground: `mobile/android/app/src/main/res/drawable/ic_meme_mark.xml`

The Flutter renderer is the runtime source of truth for in-app branding. Android uses a native vector so launcher rendering does not depend on Flutter startup.

## Core palette

Defined in `mobile/lib/theme/app_theme.dart`.

| Token | Value | Purpose |
|---|---|---|
| background | #030C18 | primary app background |
| backgroundSoft | #071220 | app chrome / nav |
| surface | #071423 | card base |
| surfaceElevated | #0A1B2D | controls / raised content |
| border | #173B61 | stronger blue border |
| borderSoft | #102A47 | normal card border |
| textPrimary | #F7F9FD | primary text |
| textSecondary | #9AAECB | secondary text |
| textMuted | #6C82A1 | quiet labels |
| primary | #22DFF7 | cyan |
| primaryBlue | #0797FF | electric blue |
| primaryDeepBlue | #315BFF | blue-violet bridge |
| primaryPurple | #8554FF | AI / fold accent |
| primaryPink | #D84DF2 | ribbon fold highlight |

Semantic finance colors remain separate from the brand gradient:

- positive: green
- negative: red
- warning: amber

Do not use profit/loss colors as decorative brand colors.

## Background and surfaces

The reference is mostly dark space, not a wall of blue cards.

Use:

- `AppBackdrop` for the global near-black navy background
- `AppSurface` for cards
- thin, low-contrast borders
- subtle shadows
- blue/purple ambient glow only around high-emphasis brand moments

Avoid:

- bright blue full-card fills
- strong gradients on every card
- white/light gray surfaces
- heavy neon bloom around ordinary data

## Navigation

Top-level navigation intentionally mirrors the approved reference and contains exactly six destinations:

1. 주식
2. 코인
3. AI 판단
4. 뉴스
5. 성과
6. 설정

Use `BrandNavIcon` so each destination appears as a small outlined rounded-square icon tile.

`알고리즘` is not removed. It lives inside the `AI 판단` hub as a secondary tab next to the judgment history.

The former Paper dashboard is the `성과` destination and remains the default landing screen.

## App bar

Every top-level screen uses `BrandAppBarTitle`.

The app bar should show the MEME lockup continuously rather than replacing the brand with a large page title. The current page name is secondary metadata.

## Layout

Use the spacing tokens from `AppSpacing`.

- 4: micro spacing
- 8: compact spacing
- 12: related items
- 16: standard internal spacing
- 20: screen horizontal padding
- 24: large block spacing
- 28: section spacing

Horizontal screen padding normally stays at 20.

## Radius

Use `AppRadius`.

- 10: compact controls
- 14: inputs / buttons
- 20: cards
- 26: hero / modal surfaces
- pill: status chips

The reference relies on rounded rectangles, but the shapes should remain tight and technical rather than bubbly.

## Typography

Prefer existing Material text styles via `Theme.of(context).textTheme`.

Hierarchy:

1. `headlineMedium`: portfolio value / major result
2. `titleLarge`: section title / important entity
3. `titleMedium`: card title
4. `bodyMedium`: normal information
5. `bodySmall`: supporting metadata

Brand-specific tracking belongs only in the MEME / AI INVEST lockup and small slogan text.

## Shared components

Prefer these before creating local variants:

- `AppBackdrop`
- `AppSurface`
- `SectionTitle`
- `AppEmptyState`
- `BrandMark`
- `BrandLockup`
- `BrandAppBarTitle`
- `BrandNavIcon`
- `BrandHero`

If a new visual pattern appears in two or more screens, move it into a shared widget instead of creating screen-local styling.

## Paper vs Live

Paper and Live must remain visually distinct.

Paper:
- calm cyan/green-leaning status treatment
- clear test-state language

Live:
- red/amber safety emphasis
- safety gates remain visible
- never make Live mode look celebratory

## Candidate score vs AI decision score

These are separate concepts.

Candidate score:
- screener quality / whether a stock deserves analysis
- cyan / blue

AI decision score:
- directional BUY / HOLD / SELL conviction
- semantic action color where useful

Keep `후보 점수 ≠ 매수 점수` anywhere ambiguity is possible.

## Charts and performance

Performance visuals should use:

- dark surfaces
- minimal grid lines
- no decorative legends
- sample count next to rates
- insufficient-sample warnings below 10 closed trades

## Buttons and controls

Primary actions:
- blue/cyan emphasis

Secondary actions:
- dark surface + outline

Destructive / Live confirmation:
- explicit red treatment + confirmation

Do not use full-width rainbow-gradient buttons for routine actions.

## Future development rule

All future Flutter UI changes must follow this file and the shared tokens/components.

When adding a new visual choice:

1. check whether a token/component already exists
2. reuse it if possible
3. if reusable, add it to the design system first
4. update this document if the new choice changes global visual rules

Do not reintroduce a separate palette, radius language, generic Material navigation, or a simplified line-chart logo inside individual feature screens.
