from app.db.models import Rule, RuleType, ThresholdUnit
from app.integrations.base_client import IntegrationError
from app.rules import engine, movie_watched, series_watched
from app.rules.base import RuleResult


async def _add_rule(db_session, rule_type, enabled=True):
    rule = Rule(
        name=f"{rule_type.value} rule",
        rule_type=rule_type,
        enabled=enabled,
        threshold_value=30,
        threshold_unit=ThresholdUnit.days,
    )
    db_session.add(rule)
    await db_session.commit()
    await db_session.refresh(rule)
    return rule


async def test_preview_merges_approaching_and_exempt_across_rule_types(db_session, monkeypatch):
    await _add_rule(db_session, RuleType.movie_watched_cleanup)
    await _add_rule(db_session, RuleType.series_watched_cleanup)

    async def fake_movie_evaluate(db, run_id, rule, ctx, dry_run=False):
        return RuleResult(items=[{"status": "approaching", "hours_remaining": 5.0, "watched_at": "2026-01-01T00:00:00"}])

    async def fake_series_evaluate(db, run_id, rule, ctx, dry_run=False):
        return RuleResult(items=[{"status": "exempt", "hours_remaining": None, "watched_at": "2026-01-02T00:00:00"}])

    monkeypatch.setattr(movie_watched, "evaluate", fake_movie_evaluate)
    monkeypatch.setattr(series_watched, "evaluate", fake_series_evaluate)

    preview = await engine.preview_watched_status(db_session)

    assert len(preview["approaching"]) == 1
    assert len(preview["exempt"]) == 1


async def test_preview_ignores_disabled_rules(db_session, monkeypatch):
    await _add_rule(db_session, RuleType.movie_watched_cleanup, enabled=False)

    called = False

    async def fake_evaluate(db, run_id, rule, ctx, dry_run=False):
        nonlocal called
        called = True
        return RuleResult()

    monkeypatch.setattr(movie_watched, "evaluate", fake_evaluate)

    await engine.preview_watched_status(db_session)

    assert called is False


async def test_preview_skips_rule_on_integration_error_without_failing(db_session, monkeypatch):
    await _add_rule(db_session, RuleType.movie_watched_cleanup)

    async def failing_evaluate(db, run_id, rule, ctx, dry_run=False):
        raise IntegrationError("jellyfin is not enabled in Settings")

    monkeypatch.setattr(movie_watched, "evaluate", failing_evaluate)

    preview = await engine.preview_watched_status(db_session)

    assert preview == {"approaching": [], "exempt": []}


async def test_preview_sorts_approaching_by_soonest_first(db_session, monkeypatch):
    await _add_rule(db_session, RuleType.movie_watched_cleanup)

    async def fake_evaluate(db, run_id, rule, ctx, dry_run=False):
        return RuleResult(
            items=[
                {"status": "approaching", "hours_remaining": 100.0, "watched_at": "2026-01-01T00:00:00"},
                {"status": "approaching", "hours_remaining": 5.0, "watched_at": "2026-01-01T00:00:00"},
            ]
        )

    monkeypatch.setattr(movie_watched, "evaluate", fake_evaluate)

    preview = await engine.preview_watched_status(db_session)

    assert [i["hours_remaining"] for i in preview["approaching"]] == [5.0, 100.0]
