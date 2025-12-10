# Health Summary Generator

Generates dashboard-ready project health summaries from Smartsheet data.

## Folder Structure

```
health_summary_generator/
├── generate.py              # Main generator script
├── README.md               # This file
└── outputs/
    ├── 2025-12-10_001/     # First run on Dec 10
    │   ├── health_summary_2025-12-10_001.txt
    │   ├── health_summary_2025-12-10_001.html
    │   └── health_summary_2025-12-10_001.json
    ├── 2025-12-10_002/     # Second run on Dec 10
    │   └── ...
    └── 2025-12-11_001/     # First run on Dec 11
        └── ...
```

## Usage

```bash
# From project root:
cd health_summary_generator

# Generate all formats (txt, html, json)
python generate.py

# Generate specific format only
python generate.py --text
python generate.py --html
python generate.py --json

# Print to console without saving
python generate.py --console
```

## Output Formats

### Plain Text (.txt)
```
PROJECT HEALTH: 🔴 RED

Project is 18 days behind schedule

Target: 2026-01-30 | Original: 2026-01-07 | Variance: -18d
Progress: 26% complete (75 tasks)

Health Breakdown:
  🔴 Critical: 31
  🟡 At Risk:  9
  🟢 On Track: 35

Vendor Progress:
  FPS        ███░░░░░░░ 37%
  IGT        ░░░░░░░░░░ 0%
  Cognigy    ███░░░░░░░ 35%
  CSG        ░░░░░░░░░░ 0%
  Frontier   ███░░░░░░░ 30%

Key Insights:
  ⚠️ IGT, CSG at 0% - blocking progress
```

### HTML (.html)
Styled HTML for Smartsheet rich text widgets. Includes:
- Color-coded status indicator
- Compact metric cards
- Visual progress bars for vendors
- Highlighted insights box

### JSON (.json)
Machine-readable format for API integration.

## Run Naming Convention

| Component | Format | Example |
|-----------|--------|---------|
| Date | YYYY-MM-DD | 2025-12-10 |
| Run Number | 3-digit padded | 001, 002, 003 |
| Full Run ID | date_number | 2025-12-10_001 |

The run counter resets daily and increments with each run.

## Workflow

1. **Before standup**: Run `python generate.py`
2. **Copy HTML**: Open the `.html` file, copy contents
3. **Paste in Smartsheet**: Paste into a rich text widget
4. **Archive**: Outputs are auto-organized by date

## Integration Ideas

- **Scheduled runs**: Task Scheduler / cron to run before daily standup
- **Slack/Teams**: Post `.txt` output to channel
- **Email digest**: Include in automated status emails
- **Diff comparison**: Compare `.json` between runs to track changes

---

*Last updated: December 10, 2025*
