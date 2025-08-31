from scripts.dashboard.utils_io import validate_import_file


def test_validate_import_file_valid_json():
    contents = '[{"sender": "foo", "labels": ["bar"]}]'
    is_valid, errors = validate_import_file(contents, "data.json")
    assert is_valid is True
    assert errors == []


def test_validate_import_file_invalid_json_missing_fields():
    contents = '[{"sender": "foo"}]'
    is_valid, errors = validate_import_file(contents, "data.json")
    assert is_valid is False
    assert any("missing fields" in e.lower() for e in errors)


def test_validate_import_file_valid_csv():
    contents = "sender,labels\nfoo,bar\n"
    is_valid, errors = validate_import_file(contents, "data.csv")
    assert is_valid is True
    assert errors == []


def test_validate_import_file_invalid_csv_missing_column():
    contents = "sender\nfoo\n"
    is_valid, errors = validate_import_file(contents, "data.csv")
    assert is_valid is False
    assert any("missing columns" in e.lower() for e in errors)
