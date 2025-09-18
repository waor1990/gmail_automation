from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
LOGS_DIR = ROOT / "logs"
CONFIG_JSON = CONFIG_DIR / "gmail_config-final.json"
LABELS_JSON = CONFIG_DIR / "gmail_labels_data.json"
REPORT_TXT = CONFIG_DIR / "ECAQ_Report.txt"
DIFF_JSON = CONFIG_DIR / "email_differences_by_label.json"
NEW_SENDERS_CSV = CONFIG_DIR / "new_senders.csv"
