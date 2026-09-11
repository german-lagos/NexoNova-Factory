"""P3.3 boundaries and explicit public content projection."""
import json
from factory.constants import ROOT
BASE = ROOT / "templates/corporate-site"
def read(path): return json.loads(path.read_text())

def test_pilot_public_projection_matches_approved_identity_and_plan_examples():
    spec=read(ROOT/"config/pilots/nexonova/corporate-site.json")
    public=read(ROOT/"config/pilots/nexonova/visual-content.json")
    assert public["brand"]["name"] == spec["brand"]["name"]
    for token, value in spec["brand"]["colors"].items(): assert public["brand"][token] == value
    assert [p["id"] for p in public["plans"]] == [p["id"] for p in spec["plans"]]
    assert [s["title"] for s in public["services"]] == spec["services"]

def test_template_default_has_no_pilot_commercial_data_or_identity():
    default=read(BASE/"src/content/site.json")
    assert default["plans"] == []
    assert "NexoNova" not in json.dumps(default)
    for path in (BASE/"src").rglob("*"):
        if path.is_file():
            assert "nexonova-prototype" not in path.read_text()
            assert "nexonova-factory" not in path.read_text()

def test_visual_selection_does_not_copy_pending_assets_or_missing_resources():
    decision=read(ROOT/"config/pilots/nexonova/visual-selection.v1.json")
    assert decision["selected_binary_assets"] == []
    assert len(decision["missing_not_selected"]) == 5
    assert not (BASE/"public/assets").exists()
    assert not list((BASE/"src").rglob("route.ts"))
