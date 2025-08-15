import json

# Read gmail_labels_data.json
with open('config/gmail_labels_data.json', 'r') as f:
    labels_data = json.load(f)

# Read gmail_config-final.json  
with open('config/gmail_config-final.json', 'r') as f:
    config_data = json.load(f)

# Extract all emails from gmail_config-final.json (both EMAIL_LIST and SENDER_TO_LABELS)
config_emails = set(config_data.get('EMAIL_LIST', []))
for label, entries in config_data.get('SENDER_TO_LABELS', {}).items():
    for entry in entries:
        if 'emails' in entry:
            config_emails.update(entry['emails'])

# Create detailed comparison by label
output = {
    "comparison_summary": {
        "source_file": "gmail_labels_data.json",
        "target_file": "gmail_config-final.json",
        "total_labels_in_source": len(labels_data['SENDER_TO_LABELS']),
        "total_labels_in_target": len(config_data.get('SENDER_TO_LABELS', {}))
    },
    "missing_emails_by_label": {}
}

total_missing = 0

# Process each label in gmail_labels_data.json
for label_name, entries in labels_data['SENDER_TO_LABELS'].items():
    label_emails = set()
    
    # Collect all emails for this label
    for entry in entries:
        if 'emails' in entry:
            label_emails.update(entry['emails'])
    
    # Find emails missing from config_final
    missing_emails = label_emails - config_emails
    
    if missing_emails or label_name not in config_data.get('SENDER_TO_LABELS', {}):
        output["missing_emails_by_label"][label_name] = {
            "label_exists_in_target": label_name in config_data.get('SENDER_TO_LABELS', {}),
            "total_emails_in_source": len(label_emails),
            "missing_emails_count": len(missing_emails),
            "missing_emails": sorted(list(missing_emails))
        }
        total_missing += len(missing_emails)

output["comparison_summary"]["total_missing_emails"] = total_missing

# Write to output file
with open('email_differences_by_label.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f"Analysis complete!")
print(f"Total labels in source: {len(labels_data['SENDER_TO_LABELS'])}")
print(f"Total labels in target: {len(config_data.get('SENDER_TO_LABELS', {}))}")
print(f"Total missing emails: {total_missing}")
print(f"Labels with missing emails: {len(output['missing_emails_by_label'])}")
print(f"Detailed report saved to: email_differences_by_label.json")
