"""Unit tests for the deterministic GateEngine."""
from app.services.gate_engine import GateEngine
from app.models.schemas import GateRule


def test_evaluate_rule_greater_equal_with_tolerance():
    rule = GateRule(
        metric_name="accuracy",
        operator=">=",
        threshold=0.85,
        tolerance=0.01,
        severity="blocker"
    )
    # Exact threshold
    res = GateEngine.evaluate_rule(rule, {"accuracy": 0.85})
    assert res.passed is True

    # Within tolerance (0.84 is within 0.85 - 0.01)
    res = GateEngine.evaluate_rule(rule, {"accuracy": 0.841})
    assert res.passed is True

    # Below tolerance
    res = GateEngine.evaluate_rule(rule, {"accuracy": 0.839})
    assert res.passed is False


def test_evaluate_rule_less_equal():
    rule = GateRule(
        metric_name="latency_p95",
        operator="<=",
        threshold=250.0,
        tolerance=10.0,
        severity="warning"
    )
    res_pass = GateEngine.evaluate_rule(rule, {"latency_p95": 255.0})
    assert res_pass.passed is True

    res_fail = GateEngine.evaluate_rule(rule, {"latency_p95": 265.0})
    assert res_fail.passed is False


def test_evaluate_rule_in_range():
    rule = GateRule(
        metric_name="calibration_slope",
        operator="in_range",
        threshold=1.0,
        tolerance=0.1,
        severity="info"
    )
    # Range is [0.9, 1.1]
    assert GateEngine.evaluate_rule(rule, {"calibration_slope": 1.05}).passed is True
    assert GateEngine.evaluate_rule(rule, {"calibration_slope": 0.88}).passed is False


def test_evaluate_rule_missing_metric():
    rule = GateRule(metric_name="safety_score", threshold=0.9, severity="blocker")
    res = GateEngine.evaluate_rule(rule, {})
    assert res.passed is False
    assert res.actual_value is None
    assert "Missing metric" in res.message


def test_evaluate_all_blocker_failure_yields_rejected():
    rules = [
        GateRule(metric_name="acc", operator=">=", threshold=0.90, severity="blocker"),
        GateRule(metric_name="lat", operator="<=", threshold=100.0, severity="warning"),
    ]
    metrics = {"acc": 0.80, "lat": 90.0}
    verdict, results, score, summary = GateEngine.evaluate_all(rules, metrics)
    assert verdict == "REJECTED"
    assert score < 75.0
    assert "Gate Verdict: REJECTED" in summary


def test_evaluate_all_warning_failure_yields_needs_review():
    rules = [
        GateRule(metric_name="acc", operator=">=", threshold=0.80, severity="blocker"),
        GateRule(metric_name="lat", operator="<=", threshold=100.0, severity="warning"),
    ]
    metrics = {"acc": 0.85, "lat": 150.0}
    verdict, results, score, summary = GateEngine.evaluate_all(rules, metrics)
    assert verdict == "NEEDS_REVIEW"
    assert 70.0 <= score <= 85.0


def test_evaluate_all_passing_yields_approved():
    rules = [
        GateRule(metric_name="acc", operator=">=", threshold=0.80, severity="blocker"),
        GateRule(metric_name="lat", operator="<=", threshold=100.0, severity="warning"),
    ]
    metrics = {"acc": 0.95, "lat": 80.0}
    verdict, results, score, summary = GateEngine.evaluate_all(rules, metrics)
    assert verdict == "APPROVED_FOR_RELEASE"
    assert score == 100.0
