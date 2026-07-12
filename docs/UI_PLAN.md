# Praesagus Frontend UI Plan

## Overview

The Praesagus frontend will be a lightweight dashboard and research workspace that sits on top of the FastAPI backend. It should provide market intelligence, trend signals, platform ingestion visibility, and skill-driven research outputs in a clear, evidence-first interface.

This UI plan covers:
- user personas and primary workflows
- pages and route structure
- core components and data views
- visual and interaction principles
- API integration points and tech stack

## User Personas

1. **Research Analyst**
   - Needs fast access to signal summaries, platform feed health, and evidence.
   - Uses the product to build market narratives and validate investment theses.

2. **Portfolio Manager**
   - Wants high-level trend dashboards, risk snapshots, and portfolio-relevant signals.
   - Uses the UI to monitor momentum and asset allocation cues.

3. **Data Engineer / Ops**
   - Needs ingestion status, connector health, and pipeline freshness.
   - Uses the UI to validate the underlying data feeds and troubleshoot failures.

## Primary Workflows

- Review the daily trend dashboard and top signals.
- Drill into specific platform feeds (Reddit, Twitter, YouTube, Hacker News, TikTok, Threads).
- Explore signal categories: consumer, market, ESG, macro, capital markets.
- Launch skill-driven research prompts or view prebuilt skill output templates.
- Monitor ingestion jobs and Airflow DAG status.

## Page Map

### 1. Dashboard (`/`)
- Hero metrics: top 5 trends, trend momentum, signal strength.
- Trend cards: Retail demand, social buzz, macro heat, issuer risk, hidden gem alerts.
- Recent evidence: latest signal documents, feed counts, top source contributors.
- Quick links: Research Lab, Platform Health, Skill Catalog.

### 2. Trends Explorer (`/trends`)
- Table/list of current trends from `/api/v1/trends`.
- Filters: category, source, confidence, timeframe.
- Trend detail panel: evidence snippets, signal origin, score breakdown, historical momentum.

### 3. Platform Feeds (`/platforms`)
- Connector health overview: ingestion status, last run, items ingested.
- Source cards for each platform: Reddit, Twitter/X, YouTube, TikTok, Threads, Hacker News, Google Trends, GitHub, Stack Overflow.
- Feed-specific detail pages with raw count graphs, freshness, and sample payloads.

### 4. Research Lab (`/research`)
- Skill catalog: cards for each skill (e.g. Elite IPO, Hidden Gem, AI Thesis, ESG Framework).
- Prompt builder: select a skill, enter tickers/keywords, and generate an analysis request.
- Saved reports and output history.

### 5. Data Pipeline Monitor (`/pipeline`)
- Airflow DAG status summary.
- Recent pipeline run history and failure alerts.
- Localstack/S3/Dynamo health indicators.

### 6. Settings / Integrations (`/settings`)
- API keys and connector configuration guidance.
- Data retention and bucket settings.
- Frontend theme, refresh intervals, and notification preferences.

## Core Components

### Global Layout
- Top navigation with page tabs: Dashboard, Trends, Platforms, Research, Pipeline, Settings.
- Side panel for quick filters and saved views.
- Sticky top bar with selected date/time context and refresh action.

### Trend Card
- Title and category badge.
- Score visualization (bar, sparkline, or gauge).
- Short evidence summary.
- Link to detail pane.

### Signal Table
- Columns: Trend, Source, Score, Category, Last Updated, Confidence.
- Inline filters and search.
- Row expansion for evidence snippets.

### Platform Feed Card
- Platform name and icon.
- Last ingestion timestamp.
- Status badge: healthy / warning / failed.
- Items ingested in last 24h.

### Connector Detail Panel
- Latest run status and schedule.
- Metrics: request count, success rate, latency.
- Raw events preview or sample payloads.

### Skill Catalog Tile
- Skill name and description.
- Core output type: research note, thesis, scenario analysis.
- Recommended inputs and example prompts.

### Research Prompt Builder
- Skill dropdown.
- Input fields for tickers, sectors, concepts, and context.
- Generated prompt preview.
- Action button to request analysis.

## Visual & Interaction Principles

- **Evidence-first**: every insight should link back to a source or connector.
- **Clear hierarchy**: use cards, tables, and minimal color accents for status.
- **Modular views**: allow analysts to drill from high-level dashboards to signal detail.
- **Responsive layout**: desktop-first, but usable on tablets.
- **Stateful refresh**: auto-refresh metrics + manual refresh control.

## API Integration

The frontend should consume backend endpoints such as:
- `GET /api/v1/trends` → populate Trends Explorer and Dashboard cards.
- `GET /api/v1/platforms` (future) → connector list and status.
- `GET /api/v1/pipeline` (future) → DAG and run history.
- `POST /api/v1/research` (future) → skill prompt execution.

Until those endpoints exist, the UI can start with static configs and trend data from `backend/main.py`.

## Tech Stack Recommendation

- React (Vite) or Next.js for fast iteration.
- TypeScript for schema safety.
- Tailwind CSS or Chakra UI for consistent styling.
- Recharts or Chart.js for charts.
- React Query for API data fetching and cache.

## Implementation Phases

### Phase 1: MVP Dashboard
- Basic routes: Dashboard, Trends, Platforms.
- Use static / fallback trend data and simple cards.
- One example connector health card.

### Phase 2: API Integration
- Connect `/api/v1/trends`.
- Add dynamic feed health from backend.
- Add trend detail and search/filtering.

### Phase 3: Research Lab
- Add skill catalog page.
- Build prompt form UI.
- Add request flow to backend research endpoint.

### Phase 4: Pipeline Monitor
- Add Airflow DAG status and pipeline run view.
- Integrate connector config and ingestion metrics.

## Folder Structure

Recommended frontend folder layout:

```
frontend/
  src/
    components/
      TrendCard.tsx
      PlatformCard.tsx
      SignalTable.tsx
      SkillTile.tsx
      PromptBuilder.tsx
    pages/
      index.tsx
      trends.tsx
      platforms.tsx
      research.tsx
      pipeline.tsx
      settings.tsx
    services/
      api.ts
    stores/
      state.ts
    styles/
      globals.css
```

## Next Step
Add a frontend skeleton repo under `/frontend/` with a Vite or Next.js starter, then wire the `Dashboard` and `Trends` pages to the current API.
