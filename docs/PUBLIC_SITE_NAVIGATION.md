# Public Site Navigation

Public pages should use the shared `<praesagus-site-nav>` web component and its stylesheet from `artifacts/shared/`. This keeps the brand position and 16px type, 64px minimum bar height, 1680px maximum width, links, active state, and responsive menu consistent.

## Static pages

Load the shared assets from the page's path, then add the component before the page content:

```html
<link rel="stylesheet" href="../shared/site-navigation.css">
<script src="../shared/site-navigation.js"></script>
<praesagus-site-nav root="../" current="tickets"></praesagus-site-nav>
```

Use `root="./"` for the homepage and `root="../"` for a one-level page such as Reports, Seasonality, or Tickets. Set `current` to the active page key: `home`, `reports`, `calendar`, `technical`, `tickers`, `seasonality`, or `tickets`.

## Vite pages

Import the same sources from `frontend/src/main.tsx`:

```ts
import '../../artifacts/shared/site-navigation.js';
import '../../artifacts/shared/site-navigation.css';
```

Render the registered web component before the page body:

```tsx
import type { ElementType } from 'react';

const PublicSiteNavigation = 'praesagus-site-nav' as ElementType<{ root?: string; current?: string }>;

<PublicSiteNavigation root="../" current="seasonality" />
```

The common stylesheet switches to the accessible Menu control at 980px and below. Do not add page-specific font sizes, logo spacing, bar widths, or breakpoints to the shared header.
