"""
Smartsheet SDK Client - Using Official Python SDK
Handles API operations with proper rate limiting and error handling
"""

import smartsheet
import time
from typing import Dict, List, Optional, Any
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID


class SmartsheetSDKClient:
    """Client using official Smartsheet Python SDK"""

    def __init__(self, api_token: str = None):
        self.api_token = api_token or SMARTSHEET_API_TOKEN
        self.client = smartsheet.Smartsheet(self.api_token)
        self.client.errors_as_exceptions(True)

        # Track created objects for reference/rollback
        self.created_objects = {
            "reports": [],
            "dashboards": [],
            "sheets": []
        }

    def get_sheet(self, sheet_id: int, include: List[str] = None) -> smartsheet.models.Sheet:
        """Get sheet with optional includes"""
        kwargs = {}
        if include:
            kwargs['include'] = ','.join(include)

        return self.client.Sheets.get_sheet(sheet_id, **kwargs)

    def get_sheet_as_dict(self, sheet_id: int, include: List[str] = None) -> Dict:
        """Get sheet and convert to dictionary"""
        sheet = self.get_sheet(sheet_id, include)
        return sheet.to_dict()

    def list_columns(self, sheet_id: int) -> List[Dict]:
        """Get list of columns for a sheet"""
        sheet = self.get_sheet(sheet_id)
        return [col.to_dict() for col in sheet.columns]

    def get_summary_fields(self, sheet_id: int) -> List[Dict]:
        """Get sheet summary fields"""
        sheet = self.get_sheet(sheet_id, include=['summary'])
        if sheet.summary and sheet.summary.fields:
            return [field.to_dict() for field in sheet.summary.fields]
        return []

    # Report Operations
    def create_report(self, report_spec: smartsheet.models.Report) -> smartsheet.models.Report:
        """Create a new report"""
        result = self.client.Reports.create_report(report_spec)
        if result.result:
            self.created_objects["reports"].append({
                "id": result.result.id,
                "name": result.result.name
            })
        return result.result

    def get_report(self, report_id: int) -> smartsheet.models.Report:
        """Get a report by ID"""
        return self.client.Reports.get_report(report_id)

    def list_reports(self) -> List[smartsheet.models.Report]:
        """List all accessible reports"""
        response = self.client.Reports.list_reports(include_all=True)
        return response.data

    def delete_report(self, report_id: int) -> None:
        """Delete a report"""
        self.client.Reports.delete_report(report_id)

    # Dashboard (Sight) Operations
    def create_dashboard(self, name: str, folder_id: int = None, workspace_id: int = None) -> Any:
        """
        Create a new dashboard (sight) using direct API call
        The SDK doesn't have a create method, so we use requests directly
        """
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        payload = {"name": name}

        if workspace_id:
            url = f"https://api.smartsheet.com/2.0/workspaces/{workspace_id}/sights"
        elif folder_id:
            url = f"https://api.smartsheet.com/2.0/folders/{folder_id}/sights"
        else:
            url = "https://api.smartsheet.com/2.0/sights"

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code in [200, 201]:
            result = response.json().get("result", {})
            self.created_objects["dashboards"].append({
                "id": result.get("id"),
                "name": result.get("name")
            })
            # Return an object with id attribute for compatibility
            class DashboardResult:
                def __init__(self, data):
                    self.id = data.get("id")
                    self.name = data.get("name")
            return DashboardResult(result)
        else:
            raise Exception(f"Failed to create dashboard: {response.status_code} - {response.text}")

    def get_dashboard(self, sight_id: int) -> smartsheet.models.Sight:
        """Get a dashboard by ID"""
        return self.client.Sights.get_sight(sight_id)

    def list_dashboards(self) -> List[smartsheet.models.Sight]:
        """List all accessible dashboards"""
        response = self.client.Sights.list_sights(include_all=True)
        return response.data

    def delete_dashboard(self, sight_id: int) -> None:
        """Delete a dashboard"""
        self.client.Sights.delete_sight(sight_id)

    def update_dashboard_name(self, sight_id: int, new_name: str) -> smartsheet.models.Sight:
        """Update dashboard name"""
        sight = smartsheet.models.Sight()
        sight.name = new_name
        result = self.client.Sights.update_sight(sight_id, sight)
        return result.result

    def update_dashboard_with_widgets(
        self,
        sight_id: int,
        widgets: List[Dict],
        name: str = None
    ) -> Any:
        """
        Update dashboard with widgets using PUT /sights/{sightId}

        The API accepts widgets as an array in the sight update.
        This is the primary way to add widgets to a dashboard.
        """
        import requests

        # First, get the current dashboard to preserve its name
        current = self.get_dashboard(sight_id)

        url = f"https://api.smartsheet.com/2.0/sights/{sight_id}"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

        # The API requires the name field
        payload = {
            "name": name or current.name,
            "widgets": widgets
        }

        response = requests.put(url, headers=headers, json=payload)

        if response.status_code == 200:
            return response.json()
        else:
            error_msg = f"Failed to update dashboard: {response.status_code} - {response.text}"
            raise Exception(error_msg)

    # Workspace Operations
    def list_workspaces(self) -> List[smartsheet.models.Workspace]:
        """List all workspaces"""
        response = self.client.Workspaces.list_workspaces(include_all=True)
        return response.data

    def get_workspace(self, workspace_id: int) -> smartsheet.models.Workspace:
        """Get workspace details"""
        return self.client.Workspaces.get_workspace(workspace_id)

    # Utility Methods
    def get_column_id_by_name(self, sheet_id: int, column_name: str) -> Optional[int]:
        """Get column ID by its name"""
        columns = self.list_columns(sheet_id)
        for col in columns:
            if col.get('title', '').lower() == column_name.lower():
                return col.get('id')
        return None

    def get_summary_field_id_by_title(self, sheet_id: int, field_title: str) -> Optional[int]:
        """Get summary field ID by its title"""
        fields = self.get_summary_fields(sheet_id)
        for field in fields:
            if field.get('title', '').lower() == field_title.lower():
                return field.get('id')
        return None

    def get_created_objects(self) -> Dict:
        """Return all objects created during this session"""
        return self.created_objects

    def save_created_objects(self, filename: str = "created_objects.json"):
        """Save created objects to JSON file"""
        import json
        with open(filename, 'w') as f:
            json.dump(self.created_objects, f, indent=2)
        print(f"Created objects saved to {filename}")

    def rollback(self):
        """Delete all objects created during this session"""
        print("Starting rollback...")

        for dashboard in reversed(self.created_objects["dashboards"]):
            try:
                self.delete_dashboard(dashboard["id"])
                print(f"  Deleted dashboard: {dashboard['name']} (ID: {dashboard['id']})")
            except Exception as e:
                print(f"  Failed to delete dashboard {dashboard['id']}: {e}")

        for report in reversed(self.created_objects["reports"]):
            try:
                self.delete_report(report["id"])
                print(f"  Deleted report: {report['name']} (ID: {report['id']})")
            except Exception as e:
                print(f"  Failed to delete report {report['id']}: {e}")

        print("Rollback complete")
