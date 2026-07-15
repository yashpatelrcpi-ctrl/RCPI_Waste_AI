import json
import sqlite3
import os
import traceback
import bulk_test_data
import database
import reports

out = {}

try:
    print('Starting bulk import...')
    result = bulk_test_data.run_bulk_test_data()
    out['bulk_result'] = result

    db_path = database.get_database_name()
    print('Database used:', db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tables = ['citizens','households','complaints','wards','vehicles','staff','waste_collection']
    counts = {}
    for t in tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM {t}')
            counts[t] = cursor.fetchone()[0]
        except Exception as e:
            counts[t] = f'ERROR: {e}'

    out['table_counts'] = counts

    try:
        complaint_report = reports.ReportGenerator.get_complaint_summary()
        waste_report = reports.ReportGenerator.get_waste_summary()
        out['reports'] = {
            'complaint_summary': complaint_report.get('summary') if isinstance(complaint_report, dict) else str(complaint_report),
            'waste_summary': waste_report.get('summary') if isinstance(waste_report, dict) else str(waste_report),
        }
    except Exception as e:
        out['reports_error'] = str(e)

except Exception as e:
    out['exception'] = str(e)
    out['traceback'] = traceback.format_exc()

root = os.path.dirname(os.path.abspath(__file__))
out_path = os.path.join(root, 'bulk_verification_output.json')
with open(out_path, 'w') as f:
    json.dump(out, f, indent=2)

print(f'WROTE {out_path}')
