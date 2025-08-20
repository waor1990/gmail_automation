from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_JSON = ROOT / "config" / "gmail_config-final.json"
LABELS_JSON = ROOT / "config" / "gmail_labels_data.json"
REPORT_TXT = ROOT / "config" / "ESAQ_Report.txt"
DIFF_JSON = ROOT / "config" / "email_differences_by_label.json"
