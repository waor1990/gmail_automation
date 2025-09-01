from scripts.dashboard.callbacks import make_empty_stl_row
from scripts.dashboard.theme import get_theme_style


def test_make_empty_stl_row_defaults():
    row = make_empty_stl_row()
    assert row["read_status"] is False
    assert row["delete_after_days"] is None


def test_make_empty_stl_row_custom_defaults():
    row = make_empty_stl_row({"read_status": True, "delete_after_days": 5})
    assert row["read_status"] is True
    assert row["delete_after_days"] == 5


def test_get_theme_style_dark_and_light():
    dark = get_theme_style("dark")
    light = get_theme_style("light")
    assert dark["backgroundColor"] == "#222"
    assert light["backgroundColor"] == "#fff"
