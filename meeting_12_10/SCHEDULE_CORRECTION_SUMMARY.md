# Phase 2 Agentic Voice - Schedule Correction Summary

**Generated:** December 9, 2025 (Updated 9:45 PM)
**Original SOW Go-Live:** January 7, 2026
**Approved Revised Baseline:** January 13, 2026 (+6d FPS reassignment)
**Current Projection:** January 30, 2026

---

## Executive Summary

Two root causes have been identified for the schedule variance:

1. **FPS Developer Reassignment** (Nov 25 - Dec 9)
   - Developer pulled to resolve intent taxonomy issues
   - Impact: 6 working days shift approved
   - Resolution: Baseline moves from Jan 7 to Jan 13

2. **IGT SIP Trunks Delay** (Dec 8 → Dec 23)
   - Configuration taking 2-3 weeks vs 1 week originally planned
   - Per 12/05 note from IGT: "configuration will take another 2-3 weeks"
   - Impact: 15 calendar days cascading through entire critical path

---

## Schedule Projection

| Milestone | SOW Date | Current Projection | Variance |
|-----------|----------|-------------------|----------|
| IGT Staging Complete | Dec 8 | Dec 23 | +15 days |
| Cognigy Phase 2 | Dec 15 | Dec 30 | +15 days |
| FPS QA Testing | Dec 18 | Jan 6 | +19 days |
| Partner Integrations | Dec 18 | Jan 7 | +20 days |
| UAT Testing | Dec 25 | Jan 19 | +25 days |
| UAT Approval | Dec 25 | Jan 21 | +27 days |
| CAB Approval | Jan 6 | Jan 28 | +22 days |
| **Production Deployment** | Jan 7 | **Jan 30** | **+23 days** |

**Gap to Approved Baseline:** 18 days (per Smartsheet NETDAYS formula)

---

## Baseline Updates Required

**Total rows to update:** 54

### Key Updates:
- **5 tasks** shifting from Jan 7 → Jan 13 baseline (final deployment tasks)
- **49 tasks** with proportional baseline shift (+6 days)
- **21 tasks** already complete (no change)

---

## Recovery Options (18-Day Gap)

| Option | Action | Days Saved | Decision Owner |
|--------|--------|------------|----------------|
| A | QA parallel with partner integrations | 2-3 days | @Chirag |
| B | Compress UAT from 8d to 5d | 3 days | @Frontier |
| C | Compress CAB from 4d to 2d | 2 days | @Frontier |
| D | Accept revised go-live of Jan 30 | N/A | @Frontier |

**Maximum Recovery:** 7-8 days if options A, B, C all approved → Jan 22-23

---

## Files Generated

| File | Purpose |
|------|---------|
| `schedule_correction_jan13.py` | Analysis script with critical path recalculation |
| `update_smartsheet_baselines.py` | **Smartsheet API update script** |
| `Schedule_Corrections_Jan13.xlsx` | Excel report with all corrections |
| `corrections_jan13.json` | Machine-readable corrections data |

---

## How to Apply Updates

### Option 1: API Update (Recommended)

```bash
# Preview changes (dry-run)
python update_smartsheet_baselines.py --dry-run

# Apply changes
python update_smartsheet_baselines.py
```

The script will:
1. Create a backup of the current sheet
2. Update all 54 baselines
3. Apply in batches of 50 rows

### Option 2: Manual Update

1. Open `Schedule_Corrections_Jan13.xlsx`
2. Go to "Baseline Updates" tab
3. For each row, update the Baseline Finish column to the "New Baseline" value
4. Smartsheet will auto-recalculate variance

---

## Contractual Protection (SOW Section 9)

> "FPS shall not be liable for penalties or damages if delays occur due to dependencies outside FPS control (by Frontier, Cognigy, CSG, IGT, etc.)"

The IGT delay (15 days) is explicitly covered under this clause.

---

## Post-Update Verification

After 12/10 meeting, verify:

1. [ ] IGT SIP Trunk Dec 23 target confirmed (@Sandeep)
2. [ ] Compression decisions documented (QA, UAT, CAB)
3. [ ] Variance acknowledged by stakeholders
4. [ ] Recovery plan approved if needed

---

## Recommendations

1. **Maintain Jan 13 as official baseline**
   - Approved via FPS developer reassignment agreement
   - Baselines show original commitment; variance shows true slip
   - Do NOT change baselines to hide variance

2. **Document IGT delay formally**
   - Note added to 1.8 referencing the 12/05 communication
   - Per SOW Section 9, external delays are covered

3. **Monitor IGT progress**
   - Target: Dec 23 completion (BOTTLENECK)
   - Any further slip will cascade to go-live

4. **Evaluate compression options in 12/10 meeting**
   - QA parallel with partner integrations (2-3d, @Chirag)
   - UAT 8d→5d compression (3d, @Frontier)
   - CAB 4d→2d same-day approval (2d, @Frontier)

---

## Summary

| Metric | Value |
|--------|-------|
| Original SOW Go-Live | January 7, 2026 |
| Approved Revised Baseline | January 13, 2026 |
| Current Projection | **January 30, 2026** |
| Gap to Approved Baseline | **18 days** (per NETDAYS) |
| Root Cause (Internal) | FPS dev reassignment (+6 days) |
| Root Cause (External) | IGT SIP trunks (+15 days cascade) |
| SOW Coverage | 21 of 23 days covered by Section 9 |
| Recovery Options | Up to 7-8 days if all approved |
