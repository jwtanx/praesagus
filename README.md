# praesagus

A quantitative market analysis engine designed to spot institutional trading signals and predict macro trend reversals.

This repo also hosts Cursor Agent Skills for equity research workflows.

## Skills

| Skill | Path | Description |
|-------|------|-------------|
| Elite IPO & Equity Research | `skills/elite-ipo-equity-research/` | Institutional-grade equity research for Bursa Malaysia and global tech stocks/IPOs |

### elite-ipo-equity-research

Produces sell-side quality output including:

- 34-column side-by-side comparison table
- DCF methodology and scenario analysis (Bull / Base / Bear)
- Risk matrix and executive summary
- IPO Investment Score (/100)
- Final recommendation with conviction and allocation guidance
- RM1,500 retail IPO allocation strategy
- Ranked output table

**Trigger terms:** Bursa Malaysia, Malaysian IPOs, ACE/Main/LEAP listings, NASDAQ/NYSE tech stocks, cross-border equity comparisons.

## Installation

Symlink the skill into your personal Cursor skills folder so it is available across all projects:

```bash
ln -s "$(pwd)/skills/elite-ipo-equity-research" ~/.cursor/skills/elite-ipo-equity-research
```

## Usage

In Cursor Agent, invoke the skill by name or ask for analysis of specific stocks/IPOs:

```
Use the elite-ipo-equity-research skill to analyze [Company A], [Company B]
```

Replace the analysis targets placeholder in the skill with your company list, or provide them in your prompt.
