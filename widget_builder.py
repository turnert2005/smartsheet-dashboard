"""
Widget Builder for Smartsheet Dashboards
Creates widget configurations for the Phase 2 - Agentic Voice Dashboard

Widget types supported:
- CHART, GRIDGANTT, IMAGE, METRIC, RICHTEXT
- SHEETSUMMARY, SHORTCUT, SHORTCUTICON, SHORTCUTLIST, TITLE
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class WidgetPosition:
    """Widget position and size on the dashboard grid"""
    x: int = 0
    y: int = 0
    width: int = 3
    height: int = 3


class WidgetBuilder:
    """Builds widget configurations for dashboard"""

    def __init__(
        self,
        sheet_id: int,
        summary_fields: Dict[str, Dict],
        column_ids: Dict[str, int],
        report_ids: Dict[str, int] = None
    ):
        self.sheet_id = sheet_id
        self.summary_fields = summary_fields  # {title: {id, displayValue}}
        self.column_ids = column_ids  # {column_name: column_id}
        self.report_ids = report_ids or {}

        # Widget counter for unique IDs (temporary, API will assign real IDs)
        self._widget_counter = 0

    def _next_widget_id(self) -> int:
        """Generate a temporary widget ID"""
        self._widget_counter += 1
        return self._widget_counter

    def _get_summary_field_id(self, title: str) -> Optional[int]:
        """Get summary field ID by title"""
        field = self.summary_fields.get(title, {})
        return field.get('id')

    def _get_column_id(self, name: str) -> Optional[int]:
        """Get column ID by name"""
        return self.column_ids.get(name.lower())

    # Title Widget
    def create_title_widget(
        self,
        title: str,
        subtitle: str = None,
        position: WidgetPosition = None
    ) -> Dict:
        """Create a title widget"""
        pos = position or WidgetPosition(0, 0, 12, 2)

        widget = {
            "type": "TITLE",
            "title": title,
            "xPosition": pos.x,
            "yPosition": pos.y,
            "width": pos.width,
            "height": pos.height,
            "showTitle": True,
            "contents": {
                "type": "TITLE",
                "backgroundColor": "#FFFFFF"
            }
        }

        if subtitle:
            widget["contents"]["htmlContent"] = f"<p>{subtitle}</p>"

        return widget

    # Metric Widget
    def create_metric_widget(
        self,
        title: str,
        summary_field_title: str,
        position: WidgetPosition = None,
        hyperlink_url: str = None
    ) -> Dict:
        """
        Create a metric widget displaying a sheet summary field value

        Args:
            title: Widget display title
            summary_field_title: Name of the summary field to display
            position: Widget position on grid
            hyperlink_url: Optional URL to link to
        """
        pos = position or WidgetPosition(0, 0, 3, 3)
        summary_field_id = self._get_summary_field_id(summary_field_title)

        widget = {
            "type": "METRIC",
            "title": title,
            "showTitle": True,
            "xPosition": pos.x,
            "yPosition": pos.y,
            "width": pos.width,
            "height": pos.height,
            "contents": {
                "type": "METRIC",
                "sheetId": self.sheet_id,
                "cellData": [{
                    "objectId": self.sheet_id,
                    "dataSource": "SUMMARY_FIELD",
                    "columnId": summary_field_id,
                    "label": title
                }]
            }
        }

        if hyperlink_url:
            widget["contents"]["hyperlink"] = {"url": hyperlink_url}

        return widget

    # Sheet Summary Widget
    def create_sheet_summary_widget(
        self,
        title: str,
        summary_field_ids: List[int],
        position: WidgetPosition = None
    ) -> Dict:
        """Create a sheet summary widget showing multiple summary fields"""
        pos = position or WidgetPosition(0, 0, 4, 4)

        return {
            "type": "SHEETSUMMARY",
            "title": title,
            "showTitle": True,
            "xPosition": pos.x,
            "yPosition": pos.y,
            "width": pos.width,
            "height": pos.height,
            "contents": {
                "type": "SHEETSUMMARY",
                "sheetId": self.sheet_id,
                "summaryFieldIds": summary_field_ids
            }
        }

    # Chart Widget
    def create_chart_widget(
        self,
        title: str,
        chart_type: str,
        position: WidgetPosition = None,
        column_ids: List[int] = None,
        legend_position: str = "RIGHT"
    ) -> Dict:
        """
        Create a chart widget

        Args:
            title: Widget display title
            chart_type: PIE, DONUT, BAR, LINE, COLUMN
            position: Widget position on grid
            column_ids: Column IDs to include in chart
            legend_position: LEFT, RIGHT, TOP, BOTTOM
        """
        pos = position or WidgetPosition(0, 0, 4, 4)

        widget = {
            "type": "CHART",
            "title": title,
            "showTitle": True,
            "xPosition": pos.x,
            "yPosition": pos.y,
            "width": pos.width,
            "height": pos.height,
            "contents": {
                "type": "CHART",
                "chartType": chart_type,
                "sheetId": self.sheet_id,
                "legend": {
                    "position": legend_position
                }
            }
        }

        if column_ids:
            widget["contents"]["includedColumnIds"] = column_ids

        return widget

    # Report Widget (GRIDGANTT type)
    def create_report_widget(
        self,
        title: str,
        report_id: int,
        position: WidgetPosition = None,
        show_title: bool = True
    ) -> Dict:
        """
        Create a report widget

        Note: Report widgets use type GRIDGANTT in the API
        """
        pos = position or WidgetPosition(0, 0, 12, 5)

        return {
            "type": "GRIDGANTT",
            "title": title,
            "showTitle": show_title,
            "showTitleIcon": False,
            "xPosition": pos.x,
            "yPosition": pos.y,
            "width": pos.width,
            "height": pos.height,
            "contents": {
                "type": "REPORT",
                "reportId": report_id
            }
        }

    # Rich Text Widget
    def create_richtext_widget(
        self,
        title: str,
        html_content: str,
        position: WidgetPosition = None
    ) -> Dict:
        """Create a rich text widget for custom formatted content"""
        pos = position or WidgetPosition(0, 0, 6, 4)

        return {
            "type": "RICHTEXT",
            "title": title,
            "showTitle": True,
            "xPosition": pos.x,
            "yPosition": pos.y,
            "width": pos.width,
            "height": pos.height,
            "contents": {
                "type": "RICHTEXT",
                "htmlContent": html_content
            }
        }

    # Shortcut Widget
    def create_shortcut_widget(
        self,
        title: str,
        shortcuts: List[Dict],
        position: WidgetPosition = None
    ) -> Dict:
        """
        Create a shortcut widget with links

        Args:
            title: Widget title
            shortcuts: List of shortcut configs, each containing:
                - label: Display text
                - sheetId OR reportId OR url: Link target
        """
        pos = position or WidgetPosition(0, 0, 3, 2)

        return {
            "type": "SHORTCUTLIST",
            "title": title,
            "showTitle": bool(title.strip()),
            "xPosition": pos.x,
            "yPosition": pos.y,
            "width": pos.width,
            "height": pos.height,
            "contents": {
                "type": "SHORTCUTLIST",
                "shortcutData": shortcuts
            }
        }

    # Image Widget
    def create_image_widget(
        self,
        title: str,
        position: WidgetPosition = None,
        private_id: str = None,
        hyperlink_url: str = None
    ) -> Dict:
        """Create an image widget"""
        pos = position or WidgetPosition(0, 0, 3, 3)

        widget = {
            "type": "IMAGE",
            "title": title,
            "showTitle": False,
            "xPosition": pos.x,
            "yPosition": pos.y,
            "width": pos.width,
            "height": pos.height,
            "contents": {
                "type": "IMAGE",
                "fit": "FIT"
            }
        }

        if private_id:
            widget["contents"]["privateId"] = private_id

        if hyperlink_url:
            widget["contents"]["hyperlink"] = {"url": hyperlink_url}

        return widget

    # =====================================
    # Dashboard-specific widget builders
    # =====================================

    def build_row1_kpi_widgets(self, start_y: int = 2) -> List[Dict]:
        """
        Build Row 1: Critical KPI Widgets
        STATUS | VARIANCE | NEW TARGET | ORIGINAL PLAN
        """
        widgets = []

        # STATUS widget
        widgets.append(self.create_metric_widget(
            title="STATUS",
            summary_field_title="Project Health",
            position=WidgetPosition(0, start_y, 3, 3)
        ))

        # VARIANCE widget
        widgets.append(self.create_metric_widget(
            title="VARIANCE",
            summary_field_title="Project Variance",
            position=WidgetPosition(3, start_y, 3, 3)
        ))

        # NEW TARGET widget
        widgets.append(self.create_metric_widget(
            title="NEW TARGET",
            summary_field_title="Target Go-Live",
            position=WidgetPosition(6, start_y, 3, 3)
        ))

        # ORIGINAL PLAN widget
        widgets.append(self.create_metric_widget(
            title="ORIGINAL PLAN",
            summary_field_title="Original Go-Live",
            position=WidgetPosition(9, start_y, 3, 3)
        ))

        return widgets

    def build_row2_chart_widgets(self, start_y: int = 5) -> List[Dict]:
        """
        Build Row 2: Visual Snapshot Charts
        HEALTH COUNTS (Pie) | COMPLETION % (Donut) | TASKS BY STATUS (Bar)
        """
        widgets = []

        health_col = self._get_column_id("health")
        status_col = self._get_column_id("status")

        # HEALTH COUNTS - Pie chart
        widgets.append(self.create_chart_widget(
            title="HEALTH COUNTS",
            chart_type="PIE",
            position=WidgetPosition(0, start_y, 4, 4),
            column_ids=[health_col] if health_col else None
        ))

        # COMPLETION % - Donut chart
        widgets.append(self.create_chart_widget(
            title="COMPLETION %",
            chart_type="DONUT",
            position=WidgetPosition(4, start_y, 3, 4),
            column_ids=[status_col] if status_col else None
        ))

        # TASKS BY STATUS - Bar chart
        widgets.append(self.create_chart_widget(
            title="TASKS BY STATUS",
            chart_type="BAR",
            position=WidgetPosition(7, start_y, 5, 4),
            column_ids=[status_col] if status_col else None
        ))

        return widgets

    def build_row3_fire_list(self, start_y: int = 9) -> List[Dict]:
        """
        Build Row 3: Fire List Report Widget
        """
        widgets = []

        at_risk_id = self.report_ids.get("at_risk")
        if at_risk_id:
            widgets.append(self.create_report_widget(
                title="🔥 THE FIRE LIST: TOP 5 AT-RISK",
                report_id=at_risk_id,
                position=WidgetPosition(0, start_y, 12, 5)
            ))

        return widgets

    def build_row4_vendor_milestones(
        self,
        start_y: int = 14,
        vendor_data: Dict[str, float] = None
    ) -> List[Dict]:
        """
        Build Row 4: Vendor Progress & Milestones
        """
        widgets = []

        # Default vendor data
        if vendor_data is None:
            vendor_data = {
                "FPS": 80,
                "IGT": 40,
                "Cognigy": 60,
                "CSG": 40,
                "Frontier": 20
            }

        # Build vendor progress HTML
        vendor_html = self._build_vendor_progress_html(vendor_data)
        widgets.append(self.create_richtext_widget(
            title="VENDOR PROGRESS",
            html_content=vendor_html,
            position=WidgetPosition(0, start_y, 6, 5)
        ))

        # Milestones report widget
        milestones_id = self.report_ids.get("milestones")
        if milestones_id:
            widgets.append(self.create_report_widget(
                title="UPCOMING MILESTONES",
                report_id=milestones_id,
                position=WidgetPosition(6, start_y, 6, 5)
            ))

        return widgets

    def _build_vendor_progress_html(self, vendor_data: Dict[str, float]) -> str:
        """Build HTML for vendor progress display"""
        html = ['<div style="font-family: Arial, sans-serif; padding: 10px; font-size: 14px;">']

        for vendor, pct in vendor_data.items():
            filled = int(pct / 10)
            empty = 10 - filled

            # Use HTML entities for progress bar
            bar = "█" * filled + "░" * empty

            html.append(f'''
                <div style="margin-bottom: 12px; display: flex; align-items: center;">
                    <span style="width: 80px; font-weight: bold;">{vendor}:</span>
                    <span style="font-family: monospace; letter-spacing: 2px; margin: 0 10px;">{bar}</span>
                    <span style="font-weight: bold; color: {"#2e7d32" if pct >= 60 else "#f57c00" if pct >= 40 else "#c62828"};">{int(pct)}%</span>
                </div>
            ''')

        html.append('</div>')
        return ''.join(html)

    def build_row5_quick_links(self, start_y: int = 19) -> List[Dict]:
        """
        Build Row 5: Quick Links
        Task Sheet | Gantt View | Summary | Overdue Report
        """
        widgets = []

        # Task Sheet shortcut
        widgets.append(self.create_shortcut_widget(
            title="",
            shortcuts=[{
                "label": "📋 Task Sheet",
                "sheetId": self.sheet_id
            }],
            position=WidgetPosition(0, start_y, 3, 2)
        ))

        # Gantt View shortcut
        widgets.append(self.create_shortcut_widget(
            title="",
            shortcuts=[{
                "label": "📊 Gantt View",
                "sheetId": self.sheet_id
            }],
            position=WidgetPosition(3, start_y, 3, 2)
        ))

        # Summary shortcut
        widgets.append(self.create_shortcut_widget(
            title="",
            shortcuts=[{
                "label": "📈 Summary",
                "sheetId": self.sheet_id
            }],
            position=WidgetPosition(6, start_y, 3, 2)
        ))

        # Overdue Report shortcut
        at_risk_id = self.report_ids.get("at_risk")
        if at_risk_id:
            widgets.append(self.create_shortcut_widget(
                title="",
                shortcuts=[{
                    "label": "⚠️ At-Risk Report",
                    "reportId": at_risk_id
                }],
                position=WidgetPosition(9, start_y, 3, 2)
            ))

        return widgets

    def build_all_widgets(self, vendor_data: Dict[str, float] = None) -> List[Dict]:
        """Build all widgets for the complete dashboard"""
        all_widgets = []

        # Title widget
        all_widgets.append(self.create_title_widget(
            title="Phase 2 - Agentic Voice",
            subtitle="Project Dashboard",
            position=WidgetPosition(0, 0, 12, 2)
        ))

        # Row 1: KPI Widgets
        all_widgets.extend(self.build_row1_kpi_widgets(start_y=2))

        # Row 2: Chart Widgets
        all_widgets.extend(self.build_row2_chart_widgets(start_y=5))

        # Row 3: Fire List
        all_widgets.extend(self.build_row3_fire_list(start_y=9))

        # Row 4: Vendor Progress & Milestones
        all_widgets.extend(self.build_row4_vendor_milestones(
            start_y=14,
            vendor_data=vendor_data
        ))

        # Row 5: Quick Links
        all_widgets.extend(self.build_row5_quick_links(start_y=19))

        return all_widgets
