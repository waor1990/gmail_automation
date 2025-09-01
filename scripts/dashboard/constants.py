from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_JSON = ROOT / "config" / "gmail_config-final.json"
LABELS_JSON = ROOT / "config" / "gmail_labels_data.json"
REPORT_TXT = ROOT / "config" / "ECAQ_Report.txt"
DIFF_JSON = ROOT / "config" / "email_differences_by_label.json"
LOGS_DIR = ROOT / "logs"
NEW_SENDERS_CSV = ROOT / "config" / "new_senders.csv"
