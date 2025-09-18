# Configuration Examples

The `config/gmail_config-final.json` file maps one or more senders to an
existing Gmail label. Start by copying the sample file at
`config/config-sample/gmail_config.sample.json` and adjust the entries to match
your workflow. Each label maps to a list of rule objects; every rule bundles
the senders that share the same behavior.

```json
{
  "SENDER_TO_LABELS": {
    "Finance": [
      {
        "read_status": false,
        "delete_after_days": 30,
        "emails": [
          "billing@example.com",
          "alerts@example.com"
        ]
      }
    ],
    "Newsletters": [
      {
        "read_status": true,
        "delete_after_days": null,
        "emails": [
          "news@example.com"
        ]
      }
    ]
  }
}
```

- `read_status` controls whether messages are marked as read after labeling.
- `delete_after_days` can be an integer or `null`. When set, messages older than
  the threshold are deleted after processing.
- `emails` lists every sender that should receive the same handling.

The automation normalizes string values such as `"true"`/`"false"` for
`read_status` and converts `delete_after_days` to integers. Labels referenced in
`SENDER_TO_LABELS` must already exist in Gmail; create them before running the
script or through the dashboard.
