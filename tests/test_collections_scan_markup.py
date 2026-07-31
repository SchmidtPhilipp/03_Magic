"""Template markers for interactive scan UI."""

from pathlib import Path


def test_collections_template_has_interactive_scan_markup():
    html = Path("templates/collections.html").read_text(encoding="utf-8")
    assert 'id="scanStage"' in html
    assert 'id="scanBoxes"' in html
    assert 'id="scanDetailPanel"' in html
    assert 'id="scanOriginal"' in html
