"""
Project Health Summary Generator
Generates a pithy, dashboard-ready status summary from Smartsheet data.

Usage:
    python generate_health_summary.py           # Plain text output
    python generate_health_summary.py --html    # HTML for rich text widget
    python generate_health_summary.py --json    # JSON for API consumption
"""

import smartsheet
from datetime import datetime, date
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID


def get_sheet_data():
    """Fetch current data from Smartsheet"""
    client = smartsheet.Smartsheet(SMARTSHEET_API_TOKEN)
    client.errors_as_exceptions(True)

    sheet = client.Sheets.get_sheet(TASK_SHEET_ID, include="summary")

    # Extract summary fields
    summary = {}
    if sheet.summary and sheet.summary.fields:
        for field in sheet.summary.fields:
            val = field.display_value
            # If no display_value, check object_value
            if val is None and field.object_value is not None:
                obj = field.object_value
                # Handle DateObjectValue and similar types
                if hasattr(obj, "value"):
                    val = obj.value
                elif isinstance(obj, dict) and obj.get("objectType") == "DATE":
                    val = obj.get("value")
                else:
                    val = str(obj)
            summary[field.title] = val

    return {
        "sheet_name": sheet.name,
        "total_rows": sheet.total_row_count,
        "summary": summary,
        "fetched_at": datetime.now(),
    }


def generate_summary(data: dict) -> dict:
    """Generate health summary from sheet data"""
    s = data["summary"]

    # Helper to extract date value
    def get_date(val):
        if isinstance(val, dict):
            return val.get("value", "TBD")
        if isinstance(val, str) and val.startswith("{"):
            import json

            try:
                parsed = json.loads(val)
                return parsed.get("value", val)
            except:
                pass
        return val if val else "TBD"

    # Extract key metrics
    project_health = s.get("Project Health", "Unknown")
    variance = s.get("Project Variance", 0)
    target_date = get_date(s.get("Target Go-Live"))
    original_date = get_date(s.get("Original Go-Live"))
    pct_complete = s.get("% Complete", 0)

    total_red = int(s.get("Total Red", 0))
    total_yellow = int(s.get("Total Yellow", 0))
    total_green = int(s.get("Total Green", 0))
    total_tasks = int(s.get("Total Tasks", 0))

    # Vendor progress
    vendors = {
        "FPS": s.get("FPS Complete", 0),
        "IGT": s.get("IGT Complete", 0),
        "Cognigy": s.get("Cognigy Complete", 0),
        "CSG": s.get("CSG Complete", 0),
        "Frontier": s.get("Frontier Complete", 0),
    }

    # Convert percentages safely
    def to_pct(val):
        if val is None:
            return 0
        try:
            val = float(val)
            return int(val * 100) if val < 1 else int(val)
        except (ValueError, TypeError):
            return 0

    pct_complete = to_pct(pct_complete)

    for k, v in vendors.items():
        vendors[k] = to_pct(v)

    # Determine status emoji and color
    if project_health == "Red":
        status_indicator = "🔴"
        status_color = "#BD696A"
    elif project_health == "Yellow":
        status_indicator = "🟡"
        status_color = "#E0B774"
    else:
        status_indicator = "🟢"
        status_color = "#33826A"

    # Find blockers (vendors at 0%)
    blockers = [k for k, v in vendors.items() if v == 0]

    # Find leader
    leader = max(vendors, key=lambda k: vendors[k])
    leader_pct = vendors[leader]

    # Generate headline
    if variance and int(variance) < 0:
        headline = f"Project is {abs(int(variance))} days behind schedule"
    elif variance and int(variance) > 0:
        headline = f"Project is {int(variance)} days ahead of schedule"
    else:
        headline = "Project is on schedule"

    # Generate insights
    insights = []

    if blockers:
        insights.append(f"⚠️ {', '.join(blockers)} at 0% - blocking progress")

    if total_red > total_green:
        insights.append(f"🔥 {total_red} critical tasks vs {total_green} on track")

    if leader_pct > 50:
        insights.append(f"✅ {leader} leading at {leader_pct}%")

    return {
        "health": project_health,
        "status_indicator": status_indicator,
        "status_color": status_color,
        "headline": headline,
        "variance": variance,
        "target_date": target_date,
        "original_date": original_date,
        "pct_complete": pct_complete,
        "total_tasks": total_tasks,
        "task_breakdown": {
            "red": total_red,
            "yellow": total_yellow,
            "green": total_green,
        },
        "vendors": vendors,
        "blockers": blockers,
        "insights": insights,
        "generated_at": data["fetched_at"].strftime("%Y-%m-%d %H:%M"),
    }


def format_plain_text(summary: dict) -> str:
    """Format summary as plain text"""
    lines = [
        f"PROJECT HEALTH: {summary['status_indicator']} {summary['health'].upper()}",
        f"",
        f"{summary['headline']}",
        f"",
        f"Target: {summary['target_date']} | Original: {summary['original_date']} | Variance: {summary['variance']}d",
        f"Progress: {summary['pct_complete']}% complete ({summary['total_tasks']} tasks)",
        f"",
        f"Health Breakdown:",
        f"  🔴 Critical: {summary['task_breakdown']['red']}",
        f"  🟡 At Risk:  {summary['task_breakdown']['yellow']}",
        f"  🟢 On Track: {summary['task_breakdown']['green']}",
        f"",
        f"Vendor Progress:",
    ]

    for vendor, pct in summary["vendors"].items():
        bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
        lines.append(f"  {vendor:10} {bar} {pct}%")

    if summary["insights"]:
        lines.append("")
        lines.append("Key Insights:")
        for insight in summary["insights"]:
            lines.append(f"  {insight}")

    lines.append("")
    lines.append(f"Generated: {summary['generated_at']}")

    return "\n".join(lines)


def format_html(summary: dict) -> str:
    """Format summary as HTML for Smartsheet rich text widget"""

    vendor_bars = []
    for vendor, pct in summary["vendors"].items():
        color = "#33826A" if pct >= 50 else "#E0B774" if pct >= 25 else "#BD696A"
        vendor_bars.append(
            f"""
            <div style="display: flex; align-items: center; margin: 4px 0;">
                <span style="width: 70px; font-weight: 600;">{vendor}</span>
                <div style="flex: 1; background: #E8E8E8; height: 16px; border-radius: 3px; margin: 0 8px;">
                    <div style="width: {pct}%; background: {color}; height: 100%; border-radius: 3px;"></div>
                </div>
                <span style="width: 35px; text-align: right; font-weight: 600;">{pct}%</span>
            </div>
        """
        )

    insights_html = "".join(
        [f'<div style="margin: 4px 0;">{i}</div>' for i in summary["insights"]]
    )

    html = f"""
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #4C4C4C; padding: 8px;">
    <div style="display: flex; align-items: center; margin-bottom: 12px;">
        <span style="font-size: 24px; margin-right: 8px;">{summary['status_indicator']}</span>
        <div>
            <div style="font-size: 16px; font-weight: bold; color: {summary['status_color']};">{summary['health'].upper()}</div>
            <div style="font-size: 12px; color: #9A9A9A;">{summary['headline']}</div>
        </div>
    </div>

    <div style="display: flex; justify-content: space-between; margin: 12px 0; padding: 8px; background: #F5F5F5; border-radius: 4px;">
        <div style="text-align: center;">
            <div style="font-size: 18px; font-weight: bold;">{summary['pct_complete']}%</div>
            <div style="font-size: 10px; color: #9A9A9A;">COMPLETE</div>
        </div>
        <div style="text-align: center;">
            <div style="font-size: 18px; font-weight: bold;">{summary['variance']}d</div>
            <div style="font-size: 10px; color: #9A9A9A;">VARIANCE</div>
        </div>
        <div style="text-align: center;">
            <div style="font-size: 18px; font-weight: bold;">{summary['task_breakdown']['red']}</div>
            <div style="font-size: 10px; color: #9A9A9A;">CRITICAL</div>
        </div>
    </div>

    <div style="margin: 12px 0;">
        <div style="font-weight: bold; margin-bottom: 6px; font-size: 11px; color: #006643;">VENDOR PROGRESS</div>
        {''.join(vendor_bars)}
    </div>

    {f'<div style="margin-top: 12px; padding: 8px; background: #FFF9E6; border-left: 3px solid #E0B774; font-size: 12px;">{insights_html}</div>' if summary['insights'] else ''}

    <div style="margin-top: 12px; font-size: 10px; color: #9A9A9A; text-align: right;">
        Updated: {summary['generated_at']}
    </div>
</div>
"""
    return html.strip()


def format_json(summary: dict) -> str:
    """Format summary as JSON"""
    import json

    return json.dumps(summary, indent=2, default=str)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate project health summary")
    parser.add_argument("--html", action="store_true", help="Output as HTML")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--save", type=str, help="Save output to file")
    args = parser.parse_args()

    print("Fetching data from Smartsheet...", end=" ")
    data = get_sheet_data()
    print("OK")

    summary = generate_summary(data)

    if args.json:
        output = format_json(summary)
    elif args.html:
        output = format_html(summary)
    else:
        output = format_plain_text(summary)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Saved to: {args.save}")
    else:
        print("\n" + "=" * 60)
        print(output)
        print("=" * 60)


if __name__ == "__main__":
    main()
