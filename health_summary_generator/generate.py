"""
Project Health Summary Generator
Generates a pithy, dashboard-ready status summary from Smartsheet data.

Outputs are saved to: outputs/YYYY-MM-DD_NNN/
  - health_summary_YYYY-MM-DD_NNN.txt
  - health_summary_YYYY-MM-DD_NNN.html
  - health_summary_YYYY-MM-DD_NNN.json

Usage:
    python generate.py              # Generate all formats
    python generate.py --text       # Text only
    python generate.py --html       # HTML only
    python generate.py --json       # JSON only
    python generate.py --console    # Print to console, don't save
"""

import os
import sys
import glob
import smartsheet
from datetime import datetime

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = os.path.join(SCRIPT_DIR, 'outputs')


def get_run_info():
    """Get today's date and next run number"""
    today = datetime.now().strftime('%Y-%m-%d')

    # Find existing runs for today
    pattern = os.path.join(OUTPUTS_DIR, f'{today}_*')
    existing = glob.glob(pattern)

    if existing:
        # Extract run numbers and find max
        run_nums = []
        for path in existing:
            folder_name = os.path.basename(path)
            try:
                run_num = int(folder_name.split('_')[-1])
                run_nums.append(run_num)
            except ValueError:
                pass
        next_run = max(run_nums) + 1 if run_nums else 1
    else:
        next_run = 1

    run_id = f"{today}_{next_run:03d}"
    return today, next_run, run_id


def create_output_folder(run_id):
    """Create output folder for this run"""
    folder = os.path.join(OUTPUTS_DIR, run_id)
    os.makedirs(folder, exist_ok=True)
    return folder


def get_sheet_data():
    """Fetch current data from Smartsheet including task details"""
    client = smartsheet.Smartsheet(SMARTSHEET_API_TOKEN)
    client.errors_as_exceptions(True)

    sheet = client.Sheets.get_sheet(TASK_SHEET_ID, include='summary')

    # Extract summary fields
    summary = {}
    if sheet.summary and sheet.summary.fields:
        for field in sheet.summary.fields:
            val = field.display_value
            # If no display_value, check object_value
            if val is None and field.object_value is not None:
                obj = field.object_value
                # Handle DateObjectValue and similar types
                if hasattr(obj, 'value'):
                    val = obj.value
                elif isinstance(obj, dict) and obj.get('objectType') == 'DATE':
                    val = obj.get('value')
                else:
                    val = str(obj)
            summary[field.title] = val

    # Build column map for row data extraction
    col_map = {col.title: col.id for col in sheet.columns}
    col_id_to_title = {col.id: col.title for col in sheet.columns}

    # Extract task details from rows
    tasks = []
    for row in sheet.rows:
        task = {'row_id': row.id}
        for cell in row.cells:
            col_title = col_id_to_title.get(cell.column_id, '')
            val = cell.display_value if cell.display_value else cell.value
            if val is not None:
                task[col_title] = val
        if task.get('Tasks') or task.get('Task Name') or task.get('Task'):  # Only include rows with task names
            tasks.append(task)

    return {
        'sheet_name': sheet.name,
        'total_rows': sheet.total_row_count,
        'summary': summary,
        'tasks': tasks,
        'columns': list(col_map.keys()),
        'fetched_at': datetime.now()
    }


def generate_summary(data: dict) -> dict:
    """Generate health summary from sheet data"""
    s = data['summary']

    # Helper to extract date value
    def get_date(val):
        if isinstance(val, dict):
            return val.get('value', 'TBD')
        if isinstance(val, str) and val.startswith('{'):
            import json
            try:
                parsed = json.loads(val)
                return parsed.get('value', val)
            except:
                pass
        return val if val else 'TBD'

    # Extract key metrics
    project_health = s.get('Project Health', 'Unknown')
    variance = s.get('Project Variance', 0)
    target_date = get_date(s.get('Target Go-Live'))
    original_date = get_date(s.get('Original Go-Live'))
    pct_complete = s.get('% Complete', 0)

    total_red = int(s.get('Total Red', 0) or 0)
    total_yellow = int(s.get('Total Yellow', 0) or 0)
    total_green = int(s.get('Total Green', 0) or 0)
    total_tasks = int(s.get('Total Tasks', 0) or 0)

    # Vendor progress
    vendors = {
        'FPS': s.get('FPS Complete', 0),
        'IGT': s.get('IGT Complete', 0),
        'Cognigy': s.get('Cognigy Complete', 0),
        'CSG': s.get('CSG Complete', 0),
        'Frontier': s.get('Frontier Complete', 0)
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
    if project_health == 'Red':
        status_indicator = '🔴'
        status_color = '#BD696A'
    elif project_health == 'Yellow':
        status_indicator = '🟡'
        status_color = '#E0B774'
    else:
        status_indicator = '🟢'
        status_color = '#33826A'

    # Find blockers (vendors at 0%)
    blockers = [k for k, v in vendors.items() if v == 0]

    # Find leader
    leader = max(vendors, key=lambda k: vendors[k])
    leader_pct = vendors[leader]

    # Generate headline
    if variance:
        try:
            var_int = int(float(variance))
            if var_int < 0:
                headline = f"Project is {abs(var_int)} days behind schedule"
            elif var_int > 0:
                headline = f"Project is {var_int} days ahead of schedule"
            else:
                headline = "Project is on schedule"
        except:
            headline = "Project status unknown"
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
        'health': project_health,
        'status_indicator': status_indicator,
        'status_color': status_color,
        'headline': headline,
        'variance': variance,
        'target_date': target_date,
        'original_date': original_date,
        'pct_complete': pct_complete,
        'total_tasks': total_tasks,
        'task_breakdown': {
            'red': total_red,
            'yellow': total_yellow,
            'green': total_green
        },
        'vendors': vendors,
        'blockers': blockers,
        'insights': insights,
        'tasks': data.get('tasks', []),
        'columns': data.get('columns', []),
        'generated_at': data['fetched_at'].strftime('%Y-%m-%d %H:%M')
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

    for vendor, pct in summary['vendors'].items():
        bar = '█' * (pct // 10) + '░' * (10 - pct // 10)
        lines.append(f"  {vendor:10} {bar} {pct}%")

    if summary['insights']:
        lines.append("")
        lines.append("Key Insights:")
        for insight in summary['insights']:
            lines.append(f"  {insight}")

    lines.append("")
    lines.append(f"Generated: {summary['generated_at']}")

    return '\n'.join(lines)


def format_html(summary: dict) -> str:
    """Format summary as HTML for Smartsheet rich text widget"""

    vendor_bars = []
    for vendor, pct in summary['vendors'].items():
        color = '#33826A' if pct >= 50 else '#E0B774' if pct >= 25 else '#BD696A'
        vendor_bars.append(f'''
            <div style="display: flex; align-items: center; margin: 4px 0;">
                <span style="width: 70px; font-weight: 600;">{vendor}</span>
                <div style="flex: 1; background: #E8E8E8; height: 16px; border-radius: 3px; margin: 0 8px;">
                    <div style="width: {pct}%; background: {color}; height: 100%; border-radius: 3px;"></div>
                </div>
                <span style="width: 35px; text-align: right; font-weight: 600;">{pct}%</span>
            </div>
        ''')

    insights_html = ''.join([f'<div style="margin: 4px 0;">{i}</div>' for i in summary['insights']])

    html = f'''
<div style="font-family: Arial, sans-serif; font-size: 13px; color: #4C4C4C; padding: 0;">
    <!-- Header with title and timestamp -->
    <div style="background: #006643; color: white; padding: 12px; margin: -8px -8px 12px -8px; border-radius: 4px 4px 0 0;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <div style="font-size: 16px; font-weight: bold;">Phase 2 Agentic Voice</div>
                <div style="font-size: 11px; opacity: 0.85;">Conversational AI Project Dashboard</div>
            </div>
            <div style="text-align: right; font-size: 10px; opacity: 0.85;">
                Updated: {summary['generated_at']}
            </div>
        </div>
    </div>

    <div style="padding: 0 8px 8px 8px;">
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
    </div>
</div>
'''
    return html.strip()


def format_json(summary: dict) -> str:
    """Format summary as JSON"""
    import json
    return json.dumps(summary, indent=2, default=str)


def format_prompt(summary: dict) -> str:
    """Format as a filled-in prompt ready for LLM"""

    # Build task details section
    tasks = summary.get('tasks', [])

    # Group tasks by status
    red_tasks = []
    yellow_tasks = []
    green_tasks = []

    for task in tasks:
        # Get task name (try common column names)
        task_name = task.get('Tasks') or task.get('Task Name') or task.get('Task') or task.get('Activity') or 'Unnamed'
        vendor = task.get('Assigned To') or task.get('Vendor') or task.get('Owner') or 'Unassigned'
        health = task.get('Health') or ''  # Green/Yellow/Red indicator
        status = task.get('Status') or ''  # In Progress/Complete/etc
        due_date = task.get('End Date') or task.get('Due Date') or task.get('Finish') or ''
        variance = task.get('Variance') or ''
        notes = task.get('Notes') or task.get('Description') or ''

        task_line = f"- {task_name} | Vendor: {vendor}"
        if due_date:
            # Clean up date format
            due_str = str(due_date).split('T')[0] if 'T' in str(due_date) else due_date
            task_line += f" | Due: {due_str}"
        if status:
            task_line += f" | Status: {status}"
        if variance:
            task_line += f" | Variance: {variance}d"
        if notes:
            # Truncate long notes
            notes_short = notes[:100] + '...' if len(str(notes)) > 100 else notes
            task_line += f" | Notes: {notes_short}"

        # Use Health column for Red/Yellow/Green classification
        health_lower = str(health).lower()
        if 'red' in health_lower:
            red_tasks.append(task_line)
        elif 'yellow' in health_lower:
            yellow_tasks.append(task_line)
        elif 'green' in health_lower:
            green_tasks.append(task_line)

    # Build task details text
    task_details = ""
    if red_tasks:
        task_details += f"\n**Critical Tasks (Red) - {len(red_tasks)} items:**\n"
        task_details += "\n".join(red_tasks[:15])  # Limit to avoid token overflow
        if len(red_tasks) > 15:
            task_details += f"\n... and {len(red_tasks) - 15} more critical tasks"

    if yellow_tasks:
        task_details += f"\n\n**At-Risk Tasks (Yellow) - {len(yellow_tasks)} items:**\n"
        task_details += "\n".join(yellow_tasks[:10])
        if len(yellow_tasks) > 10:
            task_details += f"\n... and {len(yellow_tasks) - 10} more at-risk tasks"

    if green_tasks:
        task_details += f"\n\n**On-Track Tasks (Green) - {len(green_tasks)} items:**\n"
        task_details += "\n".join(green_tasks[:5])  # Show fewer green tasks
        if len(green_tasks) > 5:
            task_details += f"\n... and {len(green_tasks) - 5} more on-track tasks"

    prompt = f"""You are acting as a project manager preparing an AI-generated summary for a Smartsheet Rich Text widget.
You are given the summary metrics AND detailed task data from the "Phase 2 - Agentic Voice Task Sheet".

## Instructions:
1. Review BOTH the summary metrics AND the detailed task list to assess overall project health.
2. Write a concise project health summary structured as follows:
   - **Status**: One-line health indicator with emoji (🔴/🟡/🟢) and headline
   - **Analysis**: 3-4 sentences explaining schedule variance, vendor progress patterns, and risks. Reference specific tasks/blockers.
   - **Vendor Spotlight**: Quick callout of who's ahead and who's blocking, with specific task examples
   - **Critical Items**: List the top 3-5 most urgent tasks requiring attention
   - **Focus Areas**: Numbered list of top 3 priorities for the week
   - **Next Steps**: 2-3 suggested actions or escalations
3. Use bold section headers.
4. Keep it executive-ready: action-oriented, professional tone. Highlight risks and blockers clearly.
5. Reference specific tasks by name where relevant to add credibility.
6. End with "Updated: {summary['generated_at']}"

---

## Summary Metrics:

**Project Overview:**
- Project Health: {summary['health']}
- Project Variance: {summary['variance']} days
- % Complete: {summary['pct_complete']}%
- Target Go-Live: {summary['target_date']}
- Original Go-Live: {summary['original_date']}

**Task Breakdown:**
- Total Tasks: {summary['total_tasks']}
- Critical (Red): {summary['task_breakdown']['red']}
- At Risk (Yellow): {summary['task_breakdown']['yellow']}
- On Track (Green): {summary['task_breakdown']['green']}

**Vendor Progress:**
- FPS: {summary['vendors']['FPS']}%
- IGT: {summary['vendors']['IGT']}%
- Cognigy: {summary['vendors']['Cognigy']}%
- CSG: {summary['vendors']['CSG']}%
- Frontier: {summary['vendors']['Frontier']}%

---

## Detailed Task Data:
{task_details if task_details else "(No detailed task data available)"}

---

Now generate the executive health summary, incorporating insights from both the metrics AND the specific task details above."""

    return prompt


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Generate project health summary')
    parser.add_argument('--text', action='store_true', help='Generate text only')
    parser.add_argument('--html', action='store_true', help='Generate HTML only')
    parser.add_argument('--json', action='store_true', help='Generate JSON only')
    parser.add_argument('--prompt', action='store_true', help='Generate LLM prompt with current data')
    parser.add_argument('--console', action='store_true', help='Print to console only, do not save')
    args = parser.parse_args()

    # Determine what to generate
    gen_all = not (args.text or args.html or args.json or args.prompt)
    gen_text = args.text or gen_all
    gen_html = args.html or gen_all
    gen_json = args.json or gen_all
    gen_prompt = args.prompt

    # Get run info
    today, run_num, run_id = get_run_info()

    print(f"\n{'='*60}")
    print(f"  HEALTH SUMMARY GENERATOR")
    print(f"  Run: {run_id}")
    print(f"{'='*60}\n")

    # Fetch data
    print("Fetching data from Smartsheet...", end=' ')
    data = get_sheet_data()
    print("OK")

    # Generate summary
    print("Generating summary...", end=' ')
    summary = generate_summary(data)
    print("OK")

    # Format outputs
    outputs = {}
    if gen_text:
        outputs['txt'] = format_plain_text(summary)
    if gen_html:
        outputs['html'] = format_html(summary)
    if gen_json:
        outputs['json'] = format_json(summary)
    if gen_prompt:
        outputs['prompt.md'] = format_prompt(summary)

    # Save or print
    if args.console:
        print(f"\n{'='*60}")
        for fmt, content in outputs.items():
            print(f"\n[{fmt.upper()}]\n")
            print(content)
        print(f"\n{'='*60}")
    else:
        # Create output folder
        output_folder = create_output_folder(run_id)
        print(f"\nOutput folder: {output_folder}")

        # Save files
        saved_files = []
        for fmt, content in outputs.items():
            filename = f"health_summary_{run_id}.{fmt}"
            filepath = os.path.join(output_folder, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            saved_files.append(filename)
            print(f"  Saved: {filename}")

        # Summary
        print(f"\n{'='*60}")
        print(f"  COMPLETE")
        print(f"  Run ID: {run_id}")
        print(f"  Files: {len(saved_files)}")
        print(f"  Location: {output_folder}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
