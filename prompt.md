Below is a comprehensive master prompt that you can use with an AI coding agent (Claude Code, Codex, Cursor, Gemini CLI, etc.). It is written as a product + system architect specification rather than just a coding prompt, so the agent has enough context to build an enterprise-scale platform.

---

# MASTER PROMPT

# Project Name

**Praesagus**

*(Praesagus = The One Who Foresees)*

---

# Role

You are acting as a Principal Staff Engineer, Quant Researcher, AI Architect, Distributed Systems Architect, Financial Data Engineer, and Product Designer.

You have previously worked on systems comparable to Bloomberg Terminal, Palantir Foundry, Renaissance Technologies internal platforms, Two Sigma research infrastructure, Snowflake data platforms, Datadog observability, and Amazon large scale distributed systems.

Your job is NOT to write random code.

Your job is to architect and build an enterprise-grade market intelligence platform.

Every design decision must prioritize:

* scalability
* maintainability
* extensibility
* observability
* modularity
* cost efficiency
* future AI integration

This project is expected to continuously evolve over many years.

---

# Project Goal

The goal of Praesagus is NOT merely stock analysis.

The mission is:

> Discover global consumer behavioural changes BEFORE Wall Street notices them.

The system should discover:

* products becoming viral
* brands becoming popular
* shifts in consumer spending
* technology adoption
* lifestyle changes
* macro behavioural trends
* purchasing sentiment
* product complaints
* product excitement
* emerging startups
* hidden market opportunities
* early investing opportunities

before these trends are reflected inside:

* earnings
* analyst upgrades
* institutional buying
* stock prices

The philosophy is:

Consumer Behaviour
↓

Internet Discussion
↓

Trend Acceleration
↓

Revenue Growth
↓

Institution Buying
↓

Stock Explosion

Praesagus attempts to detect the first step.

---

# High Level Architecture

Design the entire project as an event-driven data platform.

The platform consists of:

```
                Data Sources
                      │
                      ▼
           Distributed Ingestion Layer
                      │
                      ▼
               Raw Data Lake (S3)
                      │
                      ▼
             Cleaning / Normalization
                      │
                      ▼
             Feature Engineering Layer
                      │
                      ▼
             AI Intelligence Engine
                      │
        ┌─────────────┴──────────────┐
        ▼                            ▼
 Alert Engine                 Dashboard API
        ▼                            ▼
 Notification              Interactive Dashboard
```

Everything must be modular.

No tight coupling.

---

# Cloud Infrastructure

Primary cloud:

AWS

Preferred services:

* MWAA (Airflow orchestration)
* ECS Fargate
* S3
* Lambda
* EventBridge
* Step Functions
* SQS
* SNS
* CloudWatch
* Glue
* Athena
* OpenSearch
* DynamoDB
* Aurora PostgreSQL
* Redshift
* ECR
* IAM
* Secrets Manager
* Parameter Store

Containerize everything.

---

# Ingestion Philosophy

The ingestion framework must support unlimited future connectors.

Every connector follows the same interface.

Example:

```
Connector

authenticate()

discover()

fetch()

normalize()

store()

monitor()

retry()
```

Each connector should be plug-and-play.

New connectors should require almost zero modification.

---

# Scheduling

Hourly by default.

Some sources:

every 15 minutes.

Some:

daily.

Everything configurable.

---

# Storage Layers

Raw

↓

Bronze

↓

Silver

↓

Gold

Raw data must NEVER be overwritten.

Always immutable.

---

# Data Lake Structure

Example:

```
s3://praesagus/raw/

source=reddit/

year=2026/

month=07/

day=12/

hour=14/

uuid.json
```

Likewise:

```
google_trends

youtube

tiktok

x

reddit

github

etc
```

---

# Ingestion Strategy

Priority order:

## Level 1

Official APIs

If free

Always use API first.

---

## Level 2

Free Tier APIs

Use whenever available.

---

## Level 3

Third-party reputable APIs

If cost effective.

---

## Level 4

Public datasets

---

## Level 5

RSS feeds

---

## Level 6

HTML scraping

BeautifulSoup

Playwright

Selenium

Only if allowed by the website's terms and robots rules.

---

## Level 7

Community-maintained SDKs

Only if:

* actively maintained
* many GitHub stars
* permissive license
* stable

---

# IP Rotation

The system should minimize unnecessary blocking while respecting website terms and rate limits.

Instead of attempting to evade restrictions, design the ingestion layer to:

* prefer official APIs
* honor robots.txt where applicable
* implement configurable request throttling and exponential backoff
* cache responses when appropriate
* distribute scheduled jobs across stateless ECS tasks
* use short-lived Fargate tasks with dynamically assigned outbound IPs where that naturally occurs, rather than relying on fixed IPs
* isolate failures per connector
* implement circuit breakers
* monitor rate-limit responses and automatically reduce request frequency

The framework should support multiple ingestion strategies per source (API, RSS, approved scraper, third-party provider) so a connector can switch to the best available method.

---

# Trend Sources

Find EVERY possible source that can indicate future consumer behaviour.

Organize them into categories.

For each source provide:

* official API
* unofficial API
* GitHub libraries
* scraping possibility
* rate limits
* pricing
* reliability
* latency
* data richness
* historical availability

---

## Search Trends

Include:

Google Trends

Google Shopping Trends

Google Search autocomplete

Google News

Bing Trends

Yahoo Trends

Wikipedia Pageviews

Wikipedia Trending

---

## Social Platforms

Reddit

X

TikTok

YouTube

Instagram

Facebook public pages

Threads

Pinterest

Snapchat (where publicly available)

LinkedIn public posts

Discord public communities

Telegram public channels

Mastodon

Bluesky

Lemon8

---

## Developer Trends

GitHub

GitLab

Stack Overflow

Hacker News

Dev.to

Product Hunt

HuggingFace

NPM downloads

PyPI downloads

Cargo

Docker Hub

---

## Startup Ecosystem

Product Hunt

YC

TechCrunch

Crunchbase

AngelList

IndieHackers

BetaList

---

## E-commerce

Amazon Best Sellers

Amazon Movers

Amazon New Releases

Amazon Reviews

Temu

AliExpress

eBay

Etsy

Shopee

Lazada

Walmart

Target

Costco

Best Buy

---

## Mobile

App Store rankings

Google Play rankings

Sensor Tower

Data.ai

AppBrain

---

## Gaming

Steam

Steam Charts

Epic Games

Twitch

Discord

---

## Finance

SEC EDGAR

13F filings

Insider trading

ETF flows

Congress trading disclosures

Options unusual activity

Whale trackers

Crypto whale wallets

ETF creations/redemptions

Short interest

Institutional ownership

---

## News

Reuters

AP

Bloomberg

Financial Times

WSJ

Yahoo Finance

MarketWatch

Seeking Alpha

Benzinga

The Motley Fool

---

## Community

Quora

Medium

Substack

Forums

Specialized niche forums

---

## Consumer Reviews

Trustpilot

G2

Capterra

Google Reviews

Apple Reviews

Amazon Reviews

Glassdoor

---

## Video

YouTube comments

TikTok comments

Instagram comments

Livestream chats

---

## AI Communities

OpenAI Community

Anthropic

HuggingFace

Reddit AI

GitHub AI

---

## Emerging Platforms

Research platforms popular among Gen Z and Gen Alpha that provide lawful public trend signals. Continuously evaluate new communities as they gain adoption and document supported access methods and limitations.

---

# NLP Pipeline

Extract:

Entities

Brands

Products

Ticker symbols

Locations

Sentiment

Emotion

Intent

Purchase intent

Recommendation

Complaints

Price discussion

Alternatives

Comparison

Demand

Supply

Growth

Virality

Momentum

Acceleration

Novelty

---

# AI Intelligence Layer

Create multiple models.

Examples:

Trend Detection

Trend Acceleration

Virality Detection

Sector Rotation

Market Sentiment

Consumer Confidence

Brand Growth

Competitor Analysis

Market Narrative

Product Adoption

Theme Detection

Supply Chain Signals

Emerging Industries

Anomaly Detection

Institution Following

Copy Trading Signals

---

# Institutional Intelligence

Aggregate research from major investment firms where redistribution is legally permitted or based on publicly available summaries.

Track publicly available:

* analyst rating changes
* target price revisions
* earnings call transcripts
* investor presentations
* SEC filings
* shareholder letters
* conference presentations

Build historical accuracy scoring.

Questions:

Which firms have been historically accurate?

Who upgrades too late?

Who downgrades too late?

Which analysts consistently outperform?

---

# Legendary Investors

Track publicly disclosed holdings of major long-term investors and funds through regulatory filings and other public disclosures.

Examples include:

* Berkshire Hathaway
* Pershing Square
* Scion Asset Management
* Appaloosa
* Bridgewater
* ARK Invest
* Tiger Global (where public)
* Third Point
* Greenlight Capital
* and other prominent investors with public reporting obligations

Build:

Historical success score

Holding duration

Conviction score

Sector preferences

Win rate

Average return

Average holding period

AI comparison

Copy trade suggestions

Portfolio similarity

---

# Dashboard

This must rival Bloomberg Terminal.

Also take inspiration from:

* TradingView
* Koyfin
* Finviz
* Yahoo Finance
* OpenBB
* Datadog
* Grafana
* Linear
* Notion
* Stripe Dashboard

Enhance their ideas.

---

# Dashboard Features

Custom watchlists

Trend score

Momentum score

Virality score

Consumer score

Institution score

Overall AI confidence

Buy probability

Sell probability

Risk score

News timeline

Reddit timeline

TikTok timeline

Google Trends timeline

Analyst timeline

Insider timeline

Whale timeline

Portfolio comparison

AI explanation

Confidence intervals

Interactive charts

Heatmaps

Network graphs

Correlation graphs

Sector rotation

AI chat assistant

Natural language search

Dark mode

---

# Alerts

User configurable.

Also AI generated.

Examples:

"Brand mentions increased 420%"

"Google searches doubled"

"TikTok engagement exploded"

"Institution upgraded"

"Consumer sentiment changed"

"Supply shortage detected"

Alerts should support:

Email

SMS

Discord

Slack

Telegram

Push notification

Webhook

---

# Trading Integration

Design an abstraction layer that can integrate with supported brokerage APIs in jurisdictions where the user is authorized to trade.

The trading layer should support:

* paper trading
* simulation/backtesting
* user approval workflows
* optional automation
* portfolio synchronization
* order history
* risk controls
* audit logs

No broker-specific business logic should exist outside the adapter layer.

---

# Monitoring

Everything monitored.

Airflow

ECS

Lambda

Crawler success

API failures

Latency

Storage growth

Duplicate rate

Missing data

Unexpected schema

Alert fatigue

Dead Letter Queue

Cost monitoring

---

# Observability

Use:

CloudWatch

OpenTelemetry

Prometheus compatible metrics

Grafana dashboards

Structured logging

Tracing

---

# AI Agents

Separate agents.

Examples:

Trend Agent

News Agent

Social Agent

Research Agent

Portfolio Agent

Alert Agent

Trade Agent

Dashboard Agent

Report Agent

---

# Security

Secrets Manager

IAM

Encryption

Least privilege

Audit logs

No secrets in code

---

# Testing

Unit

Integration

Contract

End-to-end

Load

Chaos testing

---

# Documentation

Every module must have documentation.

Every connector documented.

Architecture diagrams.

Data flow diagrams.

Sequence diagrams.

ER diagrams.

Runbooks.

---

# AGENT.md

Create an AGENT.md file at the repository root.

This file serves as the permanent context for future AI coding agents.

It should clearly explain:

* what Praesagus is
* the long-term vision
* project philosophy
* architecture
* coding conventions
* folder structure
* ingestion philosophy
* AI philosophy
* dashboard philosophy
* monitoring philosophy
* scalability principles
* security principles
* documentation standards
* testing standards
* future roadmap
* definition of success

The AGENT.md should be detailed enough that a new AI agent can understand the project goals, engineering principles, and expected implementation approach without additional explanation.

---

# Expected Deliverables

Do not start by writing application code.

Instead, produce the project in phases:

1. Product Requirements Document (PRD)
2. Technical Design Document (TDD)
3. System Architecture
4. Cloud Architecture
5. Data Lake Design
6. Ingestion Framework Design
7. Connector SDK Specification
8. Data Model
9. Event Model
10. AI Pipeline Design
11. Dashboard UX/UI Specification
12. Alerting System Design
13. Monitoring & Observability Design
14. Security Architecture
15. CI/CD Strategy
16. Testing Strategy
17. Infrastructure as Code Plan
18. Implementation Roadmap (MVP → v1 → v2 → v3)
19. Repository Structure
20. AGENT.md
21. Begin implementation only after the architecture documents have been reviewed.

---

## Additional strategic recommendations

A few additions would make Praesagus substantially stronger than a traditional "alternative data" platform:

* **Knowledge Graph:** Build a graph connecting people, companies, products, brands, sectors, suppliers, competitors, ETFs, investors, and macroeconomic events. This enables indirect signal discovery, such as rising interest in a supplier before its customers report stronger earnings.
* **Time-Series Feature Store:** Store engineered features (mention velocity, sentiment acceleration, search momentum, review ratings, institutional activity) in a dedicated feature store for model training and real-time inference.
* **Backtesting Engine:** Every signal should be replayable against historical market data to measure predictive power before being used in production.
* **Model Registry & Experiment Tracking:** Version models, prompts, datasets, and evaluation metrics to compare approaches and safely roll out improvements.
* **Data Quality Framework:** Implement schema validation, freshness checks, anomaly detection, completeness scoring, deduplication, and lineage so downstream AI is built on trustworthy data.
* **Compliance by Design:** Every connector should record its data source, collection method, licensing constraints, and permitted uses. Prefer official APIs where available, respect platform terms, and avoid collecting or storing data in ways that violate applicable agreements or privacy laws.
* **Risk Engine:** Before any automated trading capability is enabled, include configurable position sizing, maximum daily loss, concentration limits, stop-loss rules, circuit breakers, and mandatory audit logs. Keep human approval as the default until strategies have been thoroughly validated.

This elevates Praesagus from a data aggregation project into a full institutional-grade market intelligence and decision-support platform that can grow into an end-to-end research, analytics, and execution ecosystem.

---

Absolutely. In fact, I think this should become one of **Praesagus' core differentiators**, rather than just another dashboard widget.

What you want is essentially **"Bloomberg GPT + Palantir Foundry + Perplexity + OpenAI Deep Research, but powered by your own proprietary alternative data."**

I would actually elevate it into one of the major pillars of the platform.

---

# AI Intelligence Copilot

Praesagus should include an integrated AI Copilot that allows users to interact with the entire Praesagus knowledge base using natural language.

Unlike traditional chatbots, the AI must reason over all proprietary datasets collected by Praesagus, including historical trend signals, institutional research, market data, social sentiment, search trends, consumer discussions, portfolio movements, earnings information, macroeconomic indicators, and future predictive models.

The AI should behave like a senior investment analyst available 24/7.

---

# AI Chat Architecture

```
                User Question
                      │
                      ▼
              AI Gateway Service
                      │
      ┌───────────────┴────────────────┐
      ▼                               ▼
 Retrieval Engine              Agent Orchestrator
      ▼                               ▼
 Vector Search              Specialized AI Agents
      ▼                               ▼
      └───────────────┬────────────────┘
                      ▼
               Large Language Model
                      ▼
              Explainable Response
                      ▼
          Dashboard + Charts + Tables
```

---

# Supported Queries

Users should be able to ask anything naturally.

Examples:

> What stocks are currently gaining traction among Gen Z?

---

> Which semiconductor companies have the highest increase in Reddit discussion over the past month?

---

> Explain why Company X is trending.

---

> Compare Tesla and BYD using every data source available.

---

> Which AI companies are likely to outperform over the next six months?

---

> Which companies have strong consumer sentiment but have not yet received analyst upgrades?

---

> What companies have experienced increasing Google search volume while their stock price has remained relatively flat?

---

> Which consumer brands are becoming popular in Southeast Asia?

---

> Summarize today's market.

---

> Give me five undervalued companies based on alternative data.

---

> Explain why NVIDIA continues to outperform.

---

> Which institutional investors have recently accumulated shares in AI infrastructure companies?

---

> Show me companies with increasing product reviews but declining analyst ratings.

---

> Which stocks have the strongest momentum score?

---

> Find me hidden investment opportunities before Wall Street notices them.

---

> Which products are becoming viral on TikTok that belong to publicly listed companies?

---

> Explain today's market as if I were a beginner.

---

> Generate a portfolio with low risk and high growth.

---

> Which portfolio is closest to Warren Buffett's strategy?

---

> Compare Cathie Wood and Warren Buffett for AI stocks.

---

# AI Generated Reports

Users should be able to generate professional reports with one click.

Examples:

Daily Market Report

Weekly Trend Report

Monthly Sector Rotation

Consumer Trend Report

Institution Activity Report

Emerging Brands Report

AI Industry Report

Technology Adoption Report

Macro Outlook

Portfolio Health Report

Competitor Analysis

Earnings Preview

Post Earnings Summary

Company Due Diligence

Risk Assessment

Investment Thesis

Bull Case

Bear Case

SWOT Analysis

DCF Summary

Alternative Data Summary

Investment Recommendation

---

# Interactive Report Generation

Every report should be customizable.

Example:

```
Generate a report

Market:
US

Sector:
Technology

Timeframe:
Last 90 Days

Risk:
Medium

Focus:
Consumer Trends

Output:
Executive Summary

Charts:
Included

Confidence Score:
Included

Sources:
Included
```

---

# Explainable AI

Every AI answer should include transparent reasoning.

Example:

```
Recommendation

BUY

Confidence

91%

Reason

Google searches increased 320%

TikTok mentions increased 470%

Reddit sentiment improved

Institutional ownership increased

Three analysts upgraded

Product reviews improved

Revenue estimates revised upward
```

Never return a recommendation without showing supporting evidence and confidence.

---

# Evidence-Backed Responses

Every AI response should reference the underlying data used to generate the answer.

For every claim, include:

* supporting datasets
* timestamps
* confidence score
* reasoning chain (high level, not exposing internal model reasoning)
* relevant charts
* supporting news
* supporting social trends
* supporting institutional activity
* historical comparisons

Users should be able to click each evidence item to inspect the original source where licensing permits.

---

# AI Memory

The assistant should remember user preferences.

Example:

The user prefers:

* Technology
* AI
* Semiconductor
* US Market
* Medium Risk

Future conversations automatically adapt.

---

# Portfolio Assistant

The AI understands the user's holdings.

Examples:

> How risky is my portfolio?

---

> Am I overexposed to AI?

---

> Suggest diversification.

---

> Which holdings should I trim?

---

> What should I buy next?

---

> Simulate a recession.

---

> Simulate inflation.

---

> Simulate another COVID-like event.

---

> Compare my portfolio against the S&P 500.

---

> Compare against Warren Buffett.

---

> Compare against hedge funds.

---

# Predictive AI

The AI should not only explain the past—it should identify emerging signals.

Examples:

Potential breakout opportunities

Emerging industries

Upcoming consumer trends

Early-stage technology adoption

Brand momentum

Demand acceleration

Supply chain shifts

Sector rotation

Competitive threats

Revenue inflection points

Potential analyst upgrades

Possible earnings surprises

All forward-looking outputs should be clearly labeled as probabilistic forecasts rather than facts.

---

# AI Agents

Instead of a single LLM, build a multi-agent architecture.

Examples:

Market Agent

Reads macro market.

---

Social Agent

Reads Reddit.

TikTok.

X.

YouTube.

Forums.

---

News Agent

Reads news.

---

Fundamental Agent

Reads financial statements.

---

Institution Agent

Tracks hedge funds.

---

Consumer Agent

Reads reviews.

---

Technical Analysis Agent

Reads charts.

---

Macro Agent

Reads CPI.

Rates.

Fed.

---

Risk Agent

Calculates risk.

---

Portfolio Agent

Understands holdings.

---

Execution Agent

Prepares trades.

---

Report Agent

Generates professional reports.

---

Research Agent

Produces investment theses.

---

The Orchestrator decides which agents participate in answering each query, then synthesizes their outputs into a single coherent response.

---

# Deep Research Mode

Provide a "Deep Research" capability for comprehensive analysis.

The AI should autonomously:

* gather all relevant internal datasets
* retrieve recent public filings and earnings transcripts
* analyze institutional activity
* compare competitors
* identify historical patterns
* review consumer sentiment
* evaluate macroeconomic context
* summarize regulatory developments
* generate a structured investment thesis with citations

The result should resemble a professional equity research report, complete with executive summary, bull and bear cases, valuation considerations, key risks, supporting evidence, and confidence levels.

---

# Dashboard Integration

The AI Copilot should not exist as a separate page. It should be deeply integrated throughout the dashboard.

Examples include:

* A persistent chat panel that can be expanded or collapsed from any page.
* Every chart should support an "Explain this" action, allowing users to ask why a trend occurred.
* Watchlists should offer "Analyze this watchlist" and "Summarize today's changes."
* Portfolio pages should include "Review my portfolio" and "Suggest improvements."
* News articles should support "Summarize" and "What does this mean for my holdings?"
* Company pages should include "Generate investment thesis" and "Compare with competitors."
* Every AI-generated insight should allow follow-up questions in context, preserving the conversation.

---

## This Becomes Praesagus' Biggest Competitive Advantage

If the original vision was:

> **Collect every meaningful market signal before Wall Street notices.**

Then the AI Copilot extends that to:

> **Transform billions of raw market signals into actionable, explainable investment intelligence through natural conversation.**

That shift is what turns Praesagus from a sophisticated analytics dashboard into an **AI-native market intelligence platform**, where users no longer need to manually search through dozens of charts and reports. Instead, they can simply ask questions, receive evidence-backed analyses, and drill into the underlying data, making the platform accessible to both experienced investors and newcomers while still offering institutional-grade depth.
