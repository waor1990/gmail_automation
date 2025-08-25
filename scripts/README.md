# Scripts Directory

Helper commands are exposed as Python modules. Run them with:

``` python
python -m scripts.<name> [options]
```

Available commands:

- `setup` – create the virtual environment
- `create_issues` – open GitHub issues from files
- `resolve_issue` – close an issue and archive its file
- `clean_git_history` – remove sensitive files from history
- `validate_no_secrets` – check for sensitive files before committing
- `extract_gmail_labels` – export Gmail labels to JSON

Legacy `.sh` and `.ps1` shims forward to these modules and print a
deprecation notice.
