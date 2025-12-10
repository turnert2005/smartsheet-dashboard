"""
Fix Task Structure - Move rows to correct sections
"""

import smartsheet
from config import SMARTSHEET_API_TOKEN, TASK_SHEET_ID

client = smartsheet.Smartsheet(SMARTSHEET_API_TOKEN)
client.errors_as_exceptions(True)

# Section IDs
DEVELOPMENT_PHASE_ID = 4070495058595716
QA_TESTING_PHASE_ID = 8331586707591044
PROD_DEPLOYMENT_ID = 8258034787094404

# Rows to move
MOVES = [
    # (row_id, new_parent_id, description)

    # CSG Staging Dependencies - move to Development Phase
    # (4880335066566532, DEVELOPMENT_PHASE_ID, "CSG Staging Dependencies -> Development Phase"),

    # CSG Production Dependencies - move to Production Deployment
    (6006234973409156, PROD_DEPLOYMENT_ID, "CSG Production Dependencies -> Production Deployment"),

    # Cognigy Production Dependencies - move to Production Deployment
    (2628535252881284, PROD_DEPLOYMENT_ID, "Cognigy Production Dependencies -> Production Deployment"),

    # IGT Production Dependencies - move to Production Deployment (currently orphaned at parent level)
    (7132134880251780, PROD_DEPLOYMENT_ID, "IGT Production Dependencies -> Production Deployment"),
]


def move_rows():
    """Move rows to correct parent sections"""
    print("=" * 70)
    print("  MOVING ROWS TO CORRECT SECTIONS")
    print("=" * 70)

    for row_id, new_parent_id, description in MOVES:
        print(f"\n  Moving: {description}")

        # Create row update with new parent
        row = smartsheet.models.Row()
        row.id = row_id
        row.parent_id = new_parent_id

        try:
            result = client.Sheets.update_rows(TASK_SHEET_ID, [row])
            print(f"    [OK] Moved successfully")
        except Exception as e:
            print(f"    [ERROR] {e}")

    print("\n" + "=" * 70)
    print("  MOVES COMPLETE")
    print("=" * 70)


def verify_structure():
    """Verify the new structure"""
    print("\n" + "=" * 70)
    print("  VERIFYING NEW STRUCTURE")
    print("=" * 70)

    sheet = client.Sheets.get_sheet(TASK_SHEET_ID)

    sections = {
        QA_TESTING_PHASE_ID: "QA & Testing Phase",
        PROD_DEPLOYMENT_ID: "Production Deployment"
    }

    for section_id, section_name in sections.items():
        print(f"\n  {section_name}:")
        for row in sheet.rows:
            if row.parent_id == section_id:
                task_name = None
                for cell in row.cells:
                    if cell.column_id == sheet.columns[0].id:
                        task_name = cell.value
                        break
                print(f"    Row {row.row_number}: {task_name[:50]}")


if __name__ == "__main__":
    move_rows()
    verify_structure()
