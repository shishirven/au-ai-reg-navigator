from pathlib import Path

from regnav.authority import load_notes, note_for


def test_repo_notes_flag_privacy_act_obligation() -> None:
    n = note_for("oaic_app1_adm_2026")
    assert n is not None
    assert "APP 1.7-1.9" in n.explains_binding and n.in_force_from == "2026-12-10"
    assert "Explains binding law" in n.badge and "2026-12-10" in n.badge
    assert note_for("naic_ai6_foundations") is None  # voluntary guidance: no binding law behind it
    assert note_for("apra_cps230_2026") is None  # binding itself: no note needed


def test_notes_are_display_only_and_keyed_by_known_docs() -> None:
    import yaml

    known = {d["id"] for d in yaml.safe_load(Path("data/sources.yaml").read_text())["documents"]}
    assert set(load_notes()) <= known


def test_missing_file_is_empty(tmp_path: Path) -> None:
    assert load_notes(str(tmp_path / "nope.yaml")) == {}


def test_notes_do_not_affect_index_version() -> None:
    from regnav.ingest.index import _CODE_FILES

    assert "authority.py" not in _CODE_FILES  # changing notes never changes chunks or the index
