# Configuration Examples

The `config/gmail_config-final.json` file maps senders or keywords to Gmail labels.
You can create this file by copying and customizing `config/config-sample/gmail_config.sample.json`.
Below is a simple example:

```json
{
    "SENDER_TO_LABELS": {
        "alice@example.com": {
            "label": "From-Alice",
            "mark_read": true
        }
    },
    "KEYWORD_TO_LABELS": {
        "invoice": {
            "label": "Invoices",
            "mark_read": false,
            "delete_after_days": 30
        }
    }
}
```

Adjust these values to suit your workflow. Labels must already exist in your
mailbox or the script will attempt to create them.
