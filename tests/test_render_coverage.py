from scripts.dashboard.callbacks import _render_coverage


def test_render_coverage_shows_percent_and_width():
    html = _render_coverage(10, 5)
    assert "50%" in html
    assert "width:50%" in html
