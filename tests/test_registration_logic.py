"""
Tests for the pure ID-generation logic in registration.py - the part
that matters most to get right before any Sheets/ODR rewrite touches
it, since a bug here means duplicate or colliding sample IDs.
"""

import registration


def test_unique_sample_id_avoids_existing_ids(monkeypatch):
    # Force the first two generated names to collide with what's
    # already "in the register," so the retry loop has to run twice.
    names = iter([
        ["already", "taken", "one"],
        ["already", "taken", "one"],
        ["fresh", "new", "name"],
    ])
    monkeypatch.setattr(registration.coolname, "generate", lambda n: next(names))

    existing = {"already-taken-one"}
    result = registration.unique_sample_id(existing)

    assert result == "fresh-new-name"
    assert result not in existing


def test_unique_sample_id_format(monkeypatch):
    monkeypatch.setattr(registration.coolname, "generate", lambda n: ["cool", "buffalo", "water"])
    assert registration.unique_sample_id(set()) == "cool-buffalo-water"


def test_next_subsample_id_first_subsample():
    assert registration.next_subsample_id("cool-buffalo-water", set()) == "cool-buffalo-water-A"


def test_next_subsample_id_increments_past_existing():
    existing = {"cool-buffalo-water", "cool-buffalo-water-A", "cool-buffalo-water-B"}
    assert registration.next_subsample_id("cool-buffalo-water", existing) == "cool-buffalo-water-C"


def test_next_subsample_id_ignores_other_parents():
    # A different parent's subsamples shouldn't affect this parent's
    # next letter.
    existing = {"other-parent-A", "other-parent-B"}
    assert registration.next_subsample_id("cool-buffalo-water", existing) == "cool-buffalo-water-A"


def test_next_subsample_id_raises_when_exhausted():
    parent = "cool-buffalo-water"
    existing = {f"{parent}-{letter}" for letter in registration.string.ascii_uppercase}
    try:
        registration.next_subsample_id(parent, existing)
        assert False, "expected ValueError when all A-Z letters are taken"
    except ValueError:
        pass
