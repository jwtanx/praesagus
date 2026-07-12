# Ingestion Platform Connector Catalog

This document summarizes ingestion connectors for major platforms and the implementation patterns used in Praesagus.

## Connector types

- Official API connectors (preferred)
- SDK / library connectors
- Public data / feeds
- Scraping connectors (last resort, obey terms)

## Platforms

### Social media

- Reddit: official API, PRAW, Pushshift fallback
- X / Twitter: official API v2, bearer token, `httpx`
- TikTok: unofficial APIs, third-party scraper logic, or approved SDKs when available
- YouTube: official Data API v3 via `googleapiclient`
- Instagram: Graph API for business accounts / scraping for public posts
- Threads: Meta Graph API where supported
- Mastodon: ActivityPub and public instance APIs
- Discord: public events and channel data via bots where permitted

### Search and trends

- Google Trends: `pytrends` for trending search terms and interest over time
- Google News: official RSS / search API / Google News page scraping
- Bing Trends: accessible through Bing search APIs or news RSS
- Wikipedia Trending: public pageview APIs

### E-commerce and reviews

- Amazon: public review scraping with rate limits and UI analysis
- Etsy / eBay: official APIs where available; scraping for public listings
- Walmart / Target: public feeds and review pages

### Developer ecosystems

- GitHub: official API, GraphQL, events
- Stack Overflow: public API and RSS
- Hacker News: official Firebase API and RSS

### Finance & filings

- SEC EDGAR: public REST feeds and bulk data files
- 13F / insider filings: data feeds and scraped SEC index pages

## Local testing recommendations

- Use `moto` to mock AWS services for unit tests.
- Use localstack for Docker-based functional tests.
- Configure connectors to accept local endpoints through environment variables.

## Connector SDK interface

Each connector should implement:

- `authenticate()`
- `discover()`
- `fetch(start, end, cursor)`
- `normalize(raw)`
- `store(raw, normalized)`
- `monitor()`
