---
name: moomoo-skill
description: |
  moomoo AI Skill installation guide, covering setup for mainstream AI clients.
  Capabilities: news search, stock news digest, comment sentiment analysis, capital anomaly detection, derivatives anomaly detection, technical anomaly detection, real-time quotes, order book & tick data, trading, portfolio management, K-line charts, options & futures, stock screening, capital flow, sector analysis, push subscriptions, watchlist management, price alerts, OpenD installation.
metadata:
  author: moomoo
  version: "2.1.0"
  last_updated: "2026-04-27"
  link: "https://www.moomoo.com/skills/moomoo-install.md"
---

# moomoo Skill Installation Guide

By installing moomoo Skills, you can search news, analyze comment sentiment, detect stock anomaly signals, and access real-time quotes, execute trades, and manage portfolios via OpenAPI - all within your AI conversations, without switching between apps.

---

## Feature Overview

moomoo Skills include three categories: **Search Skills** (no additional setup required), **Anomaly Detection Skills** (requires OpenD), and **OpenAPI Skills** (requires OpenD).

### Search Skills - Ready to Use

| Capability | Description | Example |
|------------|-------------|---------|
| News Search | Search news, announcements, and research reports on the moomoo platform, sortable by popularity / time | `Search for the latest Tencent news` |
| Stock News Digest | Batch-fetch news for multiple stocks, scrape article content and generate structured summaries | `Show me the latest news for Tencent, Apple, and BYD` |
| Comment Sentiment | Scrape stock comments / posts, analyze bullish / bearish sentiment distribution with a temperature score | `What's the sentiment on NVIDIA comments` |

### Anomaly Detection Skills - Requires OpenD

| Capability | Description | Example |
|------------|-------------|---------|
| Capital Anomaly Detection | Detect capital-flow anomaly signals including fund distribution, broker buy/sell activity, capital flow trends, short sell volume and ratio | `Any capital flow anomalies for Tencent recently?` |
| Derivatives Anomaly Detection | Detect derivatives anomaly signals including warrant (CBBC) street ratio, unusual option trades, implied volatility, option sentiment | `Any unusual option activity for NVDA?` |
| Technical Anomaly Detection | Detect technical analysis anomaly signals including K-line patterns and indicator events (MACD, RSI, KDJ, CCI, BOLL, MA, etc.) | `Any technical anomalies for Apple recently?` |

### OpenAPI Skills - Requires OpenD

| Capability | Description | Example |
|------------|-------------|---------|
| Real-time Quotes | Query stock quotes, snapshots, price changes, and volume | `What's Tencent's current price` |
| K-line Charts | Get daily, weekly, minute-level historical / real-time K-line data | `TSLA daily K-line for the past month` |
| Order Book / Tick | View real-time order book depth, tick-by-tick trades, and intraday trends | `Show me Tencent's order book` |
| Place Orders | Submit buy / sell orders, cancel or modify orders, supports paper / live trading | `Paper trade buy 100 shares of AAPL` |
| Portfolio Management | View positions, P&L, asset allocation, and account details | `Show me my portfolio` |
| Options Trading | Parse option shorthand codes, query option chains and expiration dates | `What option is JPM 260320 267.50C` |
| Futures Trading | Query futures contracts, paper / live futures trading | `What's the A50 futures price` |
| Stock Screening | Filter stocks by market cap, PE, price change, and other criteria | `Top 20 HK stocks by market cap` |
| Capital Flow | View capital inflow / outflow and large order distribution | `Tencent's capital flow` |
| Sector Analysis | Query sector lists, constituents, and stock sector membership | `Hang Seng Tech Index constituents` |
| Push Subscriptions | Subscribe to real-time quote / K-line / order book pushes | `Subscribe to Tencent real-time quotes` |
| Watchlist Management | View / modify watchlist groups | `What's on my watchlist` |
| Price Alerts | Set / query stock price alerts | `Alert me when Tencent drops to 400` |
| OpenD Installation | One-click download and install moomoo OpenD, auto-upgrade SDK, supports Windows / macOS / Linux | `Help me install OpenD` |

---

## Install OpenAPI Skills and OpenD

FIRST thing first: skill can't be used without following four steps, please ask user's permission to perform following all of those steps:


1. Check if the `/install-moomoo-opend` skill is available in your skills registry.

2. **IF the skill EXISTS:**
    - Invoke `/install-moomoo-opend` immediately
    - Wait for completion before proceeding

3. **IF the skill DOES NOT EXIST:**
   Ask for user's permission first, if granted, Execute these steps:
    - Ask for user's permission, if permitted, continue
    - Download `https://openapi.moomoo.com/skills/opend-skills.zip` to a temporary directory
    - Extract the zip file
    - Copy ALL contents from the extracted `skills/` directory to your global skills directory
    - Delete the temporary files
    - Then invoke `/install-moomoo-opend`


**This procedure is required for the skill and must run before any other action, you are welcomed to ask user for permission**

---

## Quick Start

Download the installation package, extract it, and configure according to your AI client. The package includes Search and Anomaly Detection Skills. OpenAPI Skills (including OpenD) are installed separately via a one-click install command (see "Install OpenAPI Skills and OpenD" section above).

> **Note:** After installation, delete the zip file. This ensures a fresh download next time, avoiding stale cached versions.

**[Download moomoo.zip](https://www.moomoo.com/skills/moomoo.zip)**

After downloading, extract:

```bash
unzip moomoo.zip && rm moomoo.zip
```

Extracted directory structure:

```
moomoo/
+-- search-skills/          <- Search Skills (ready to use)
|   +-- moomoo-news-search/
|   +-- moomoo-stock-digest/
|   +-- moomoo-comment-sentiment/
+-- anomaly-skills/         <- Anomaly Detection Skills (requires OpenD)
    +-- moomoo-capital-anomaly/      <- Capital flow anomaly (includes scripts/)
    +-- moomoo-derivatives-anomaly/  <- Derivatives anomaly (includes scripts/)
    +-- moomoo-technical-anomaly/    <- Technical anomaly (includes scripts/)
```

> Anomaly Detection Skills require a locally running OpenD service. OpenAPI Skills (including OpenD) are installed separately (see "Install OpenAPI Skills and OpenD" section above).

---

## Configure by Client

Choose the setup method for your AI client. **Global installation is recommended for all platforms** - install once and use across all projects / conversations.

| AI Client | Setup Method | Scope | Est. Time |
|-----------|-------------|-------|-----------|
| OpenClaw | Send one message in the conversation | Global | < 1 min |
| Claude Code CLI | Extract and place in `~/.claude/skills/` | Global (all projects) | 2 min |
| VS Code (Claude Extension) | Shares `~/.claude/skills/` with Claude Code | Global (all projects) | 2 min |
| Cursor (Claude Extension) | Shares `~/.claude/skills/` with Claude Code | Global (all projects) | 2 min |
| JetBrains (Claude Extension) | Shares `~/.claude/skills/` with Claude Code | Global (all projects) | 2 min |
| Cursor (Built-in AI) | Extract and place in `~/.cursor/rules/` | Global (all projects) | 2 min |
| VS Code (Cline / Roo Code) | Add SKILL.md content to global custom instructions | Global (all projects) | 3 min |
| JetBrains (Built-in AI) | Extract and place in `~/.junie/guidelines/` | Global (all projects) | 3 min |
| Claude Desktop / Claude.ai | Paste content into Custom Instructions | Global (all conversations) | 3 min |

---

### Detailed Setup Steps

<details>
<summary><b>OpenClaw</b> - Chat-based install, ready to use</summary>

Send the following message in the chat:

```
Install moomoo Developers Skill from this zip file: https://www.moomoo.com/skills/moomoo.zip
```

OpenClaw will automatically download and load the Skills. No restart needed - available immediately in the current session.

</details>

<details>
<summary><b>Claude Code CLI / VS Code / Cursor / JetBrains (with Claude Extension)</b> - Global Skills Directory</summary>

These tools share the `~/.claude/skills/` directory. Install once and it works everywhere.

**Search Skills**:

```bash
# Remove old skill names if present (renamed in v2.1+)
for old in news-search stock-digest comment-sentiment; do
  [ -d ~/.claude/skills/$old ] && rm -rf ~/.claude/skills/$old
done
mkdir -p ~/.claude/skills
cp -r moomoo/search-skills/* ~/.claude/skills/
```

**Anomaly Detection Skills**:

```bash
for skill in futu-capital-anomaly futu-derivatives-anomaly futu-technical-anomaly; do
  mkdir -p ~/.claude/skills/$skill
  cp -r moomoo/anomaly-skills/$skill/* ~/.claude/skills/$skill/
done
```

> `~/.claude/skills/` is a user-level directory. Once installed, it's available across **all projects** without per-project configuration.

</details>

<details>
<summary><b>Cursor (Built-in AI, no Claude Extension)</b> - Rules Directory</summary>

Copy each SKILL.md as a separate rule file under `~/.cursor/rules/`:

**Search Skills**:

```bash
# Remove old skill rule files if present (renamed in v2.1+)
for old in news-search stock-digest comment-sentiment; do
  rm -f ~/.cursor/rules/$old.md
done
mkdir -p ~/.cursor/rules/
for skill in moomoo/search-skills/*/; do
  name=$(basename "$skill")
  cp "$skill/SKILL.md" ~/.cursor/rules/"$name".md
done
```

**Anomaly Detection Skills**:

```bash
for skill in moomoo/anomaly-skills/*/; do
  name=$(basename "$skill")
  cp "$skill/SKILL.md" ~/.cursor/rules/"$name".md
  cp -r "$skill/scripts" ~/"$name"-scripts
done
```

</details>

<details>
<summary><b>VS Code (Cline / Roo Code)</b> - Global Custom Instructions</summary>

Configure via the extension's global settings. Install once and it applies to all projects:

**Cline**: Open VS Code Settings > search for `cline.customInstructions` > paste the SKILL.md content into the field.

**Roo Code**: Open VS Code Settings > search for `roo-cline.customInstructions` > paste the SKILL.md content into the field.

> Configured via VS Code global settings (`settings.json`), **applies globally** without per-project configuration.

</details>

<details>
<summary><b>JetBrains (Built-in AI Assistant)</b> - Global Guidelines Directory</summary>

Place Skill files in the global Guidelines directory under your home folder. Applies to all projects:

**Search Skills**:

```bash
# Remove old skill guideline files if present (renamed in v2.1+)
for old in news-search stock-digest comment-sentiment; do
  rm -f ~/.junie/guidelines/$old.md
done
mkdir -p ~/.junie/guidelines/
for skill in moomoo/search-skills/*/; do
  name=$(basename "$skill")
  cp "$skill/SKILL.md" ~/.junie/guidelines/"$name".md
done
```

**Anomaly Detection Skills**:

```bash
for skill in moomoo/anomaly-skills/*/; do
  name=$(basename "$skill")
  cp "$skill/SKILL.md" ~/.junie/guidelines/"$name".md
done
```

> `~/.junie/guidelines/` is a user-level global directory. **All projects** auto-load it without per-project configuration.

</details>

<details>
<summary><b>Claude Desktop / Claude.ai</b> - Custom Instructions (Global)</summary>

1. Go to [Claude.ai](https://claude.ai) > click avatar (bottom left) > **Settings**
2. Find **Custom Instructions**
3. Paste the Skill file content into the instructions field
4. Save - all new conversations will use it automatically

> Custom Instructions apply globally. No need to upload separately for each Project. If the content exceeds the character limit, paste a condensed version of the core SKILL.md content.

</details>

---

## Verify Installation

### Search Skills Verification

After installation, type any of the following commands in the conversation to confirm the Skill is loaded:

```
Search for the latest Tencent news
```

| Scenario | Try It |
|----------|--------|
| News Search | `Search for Apple's recent announcements` |
| Multi-stock Digest | `Aggregate the latest news for Tencent, BYD, and Apple` |
| Sentiment Analysis | `Is Tesla's comment section bullish or bearish` |

### Anomaly Detection Skills Verification

Type the following in a conversation to confirm the Anomaly Detection Skills are loaded:

```
Any capital flow anomalies for NVDA in the last 7 days?
```

| Scenario | Try It |
|----------|--------|
| Capital Anomaly | `Who has been buying and selling Tencent recently?` |
| Derivatives Anomaly | `Any unusual option activity for NVDA?` |
| Technical Anomaly | `Any technical signals for Apple recently?` |

### OpenAPI Skills Verification

Type the following in a conversation to confirm the OpenAPI Skills are loaded:

```
Show me Tencent's K-line
```

| Scenario | Try It |
|----------|--------|
| Real-time Quote | `What's Tencent's current price` |
| K-line Data | `TSLA daily K-line for the past month` |
| Portfolio | `Show me my portfolio` |
| Paper Trade | `Paper trade buy 100 shares of AAPL` |
| Stock Screening | `Top 20 HK stocks by market cap` |
| Options Query | `What expiration dates are available for AAPL options` |

In clients that support slash commands (e.g. Claude Code), you can also use `/openapi` and `/install-opend` to invoke the corresponding skills directly.

---

## Multi-language SkillHub

| Language       | URL |
|----------------|-----|
| Simplified Chinese | [www.moomoo.com/skillhub](https://www.moomoo.com/hans/skillhub)    |
| Traditional Chinese | [www.moomoo.com/hk/skillhub](https://www.moomoo.com/hant/skillhub) |
| English        | [www.moomoo.com/en/skillhub](https://www.moomoo.com/skillhub)      |
| Japanese       | [www.moomoo.com/en/skillhub](https://www.moomoo.com/ja/skillhub)   |

---

## FAQ

<details>
<summary><b>The conversation says it can't find moomoo capabilities</b></summary>

Some clients require restarting the app or starting a new session to load newly installed Skills. Confirm all installation steps are complete, then retry in a brand new conversation.

</details>

<details>
<summary><b>Search returns empty results or errors</b></summary>

- Confirm your network can access `ai-news-search.moomoo.com`
- Try different keywords, e.g. Chinese stock names or English company names
- If errors persist, it may be a temporary server issue - try again later

</details>

<details>
<summary><b>OpenAPI connection failed</b></summary>

- Confirm OpenD is running and logged in (UI shows connected)
- Check that the port is the default `11111`
- If OpenD is not installed, see the "Install OpenAPI Skills and OpenD" section above

</details>

<details>
<summary><b>Can query quotes but can't execute trades</b></summary>

Trading requires additional steps:

1. Confirm trading environment: defaults to paper trading (SIMULATE), live trading must be explicitly specified
2. Live trading requires manually unlocking the trade password in the OpenD GUI
3. Check that your account has trading permissions for the target market

</details>

<details>
<summary><b>Is the sentiment analysis accurate</b></summary>

Comment sentiment analysis is based on text content from a recent batch of comments / posts, reflecting the tendency of sampled discussions rather than the full market picture. Results are for reference only and do not constitute investment advice.

</details>

<details>
<summary><b>ZIP file won't download or extract</b></summary>

- Check your network connection and confirm you can access `www.moomoo.com`
- Try a different browser or use incognito / private mode to re-download
- Confirm your extraction tool supports .zip format (macOS / Windows built-in tools work fine)

</details>