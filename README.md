# 🌿 GreenCode

[![Carbon Footprint](https://img.shields.io/badge/carbon-4.2g%20CO₂-22C55E?style=flat&logo=leaflet&logoColor=white)](https://greencode.dev)
[![PyPI](https://img.shields.io/pypi/v/greencode?color=22C55E)](https://pypi.org/project/greencode/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-22C55E.svg)](https://python.org)

**Measure the carbon footprint of your code. Get a live badge for your README.**

One GitHub Action. One badge. Every push — your CO₂ tracked automatically.

```
pip install greencode
greencode measure
```

---

## Why?

Every time your tests run, your CI consumes electricity → produces CO₂.
Most developers have no idea how much. **GreenCode makes it visible.**

- 🌿 **4.2g CO₂** — your test suite per run
- 🔥 **87g CO₂** — after a careless dependency bump
- 📈 **+340%** — what that new ML model added

---

## Quick Start

### 1. Install

```bash
pip install greencode
```

### 2. Measure

```bash
# Measure while running your tests
greencode measure

# With a custom command
greencode measure --command "python -m pytest tests/ -x"

# Output as JSON (for CI integration)
greencode measure --json
```

**Output:**
```
╭─────────────────────────────────────────╮
│         GreenCode Measurement           │
│                                         │
│  Project:  mylib                        │
│  Commit:   a3f9c2d  (main)              │
│  CO₂:      🌿 4.2100 g  (0.00000421 kg) │
│  Grade:    GREEN — low carbon           │
│  Method:   measured                     │
│                                         │
│  vs prev:  ▼ 0.8g (-16.0%)             │
╰─────────────────────────────────────────╯

Badge saved → .greencode/badge.svg
Add to README:
[![Carbon Footprint](https://greencode.dev/badge/you/mylib.svg)](https://greencode.dev)
```

### 3. Add the badge to your README

```markdown
[![Carbon Footprint](https://greencode.dev/badge/YOUR_USERNAME/YOUR_REPO.svg)](https://greencode.dev)
```

It updates automatically on every push. 🎯

---

## GitHub Action

Add to `.github/workflows/carbon.yml`:

```yaml
name: Carbon Footprint

on: [push, pull_request]

jobs:
  measure:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: greencode-dev/greencode@v1
        with:
          country: DEU        # Your server's country (emission factors)
          comment-on-pr: true # Post CO₂ report as PR comment
```

**What it does on every push:**
- Runs your tests while measuring CO₂
- Updates `.greencode/badge.svg` in your repo
- Posts a comment on PRs showing the delta vs `main`

**PR Comment:**

```
## 🌿 Carbon Footprint Report

| Metric | Value     |
|--------|-----------|
| CO₂    | 4.2100g   |
| Grade  | GREEN     |
| Commit | a3f9c2d   |

> This PR: ▲ +2.3g CO₂ (+15% vs main)
```

---

## Badge grades

| Badge | Threshold | Meaning |
|-------|-----------|---------|
| 🌿 green  | < 10g CO₂  | Low carbon — well optimized |
| 🌡 yellow | 10–50g CO₂ | Moderate — room to improve |
| 🔥 red    | > 50g CO₂  | High carbon — needs attention |

---

## Commands

```bash
greencode measure              # Measure + save badge
greencode measure --json       # Raw JSON output
greencode badge                # Regenerate badge from latest
greencode history              # Show measurement history
greencode history --limit 20   # Last 20 measurements
```

---

## Configuration

Create `greencode.toml` in your project root:

```toml
[greencode]
country    = "DEU"        # ISO 3166-1 alpha-3 country code
command    = "pytest ."   # Custom test command
badge_path = ".greencode/badge.svg"
```

**Supported country codes for emission factors:**
`DEU` · `USA` · `GBR` · `FRA` · `CHN` · `RUS` · [+ 40 more →](https://greencode.dev/docs/countries)

---

## Output files

After running `greencode measure`:

```
.greencode/
├── badge.svg      # Your live badge (commit this!)
├── latest.json    # Most recent measurement
└── history.json   # All measurements (last 100)
```

Add `.greencode/badge.svg` and `.greencode/latest.json` to git.  
Add `.greencode/history.json` to `.gitignore` or commit it — your choice.

---

## How it works

GreenCode uses [CodeCarbon](https://github.com/mlco2/codecarbon) under the hood to measure:

1. **Power consumption** — tracks CPU/GPU watts during your test run
2. **Emission factor** — converts kWh → kg CO₂ using your country's grid mix
3. **Badge** — generates a live SVG badge with the result

The measurement is a **relative baseline**, not a certified carbon audit.  
It's useful for tracking trends and comparing PRs — not for ESG reporting.  
For certified reporting, see our [Enterprise plan →](https://greencode.dev/enterprise)

---

## Methodology

```
CO₂ (kg) = Power (kW) × Duration (h) × Emission Factor (kg CO₂/kWh)

Emission factors by country:
  Germany (DEU): 0.366 kg CO₂/kWh
  USA:           0.386 kg CO₂/kWh
  France (FRA):  0.056 kg CO₂/kWh  ← nuclear
  China (CHN):   0.555 kg CO₂/kWh
```

Full methodology: [greencode.dev/docs/methodology](https://greencode.dev/docs/methodology)

---

## Contributing

```bash
git clone https://github.com/greencode-dev/greencode
cd greencode
pip install -e ".[dev]"
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.  
Good first issues: [github.com/greencode-dev/greencode/issues?q=good+first+issue](https://github.com/greencode-dev/greencode/issues?q=good+first+issue)

---

## Roadmap

- [x] CLI: `greencode measure`
- [x] Badge generator
- [x] GitHub Action
- [ ] Web dashboard: greencode.dev/dashboard
- [ ] Leaderboard: top 50 greenest open source projects
- [ ] PR comparison: this PR vs main (CO₂ delta)
- [ ] More languages: Node.js, Go, Rust native hooks
- [ ] Enterprise: certified ESG reporting

---

## License

MIT © [greencode-dev](https://github.com/greencode-dev)

---

<p align="center">
  <a href="https://greencode.dev">greencode.dev</a> ·
  <a href="https://greencode.dev/docs">Docs</a> ·
  <a href="https://github.com/greencode-dev/greencode/issues">Issues</a>
</p>
