"""Deterministic gatekeeper evaluation engine for model release policies."""
from typing import Dict, List, Tuple
from app.models.schemas import GateRule, RuleEvaluationResult


class GateEngine:
    @staticmethod
    def evaluate_rule(rule: GateRule, metrics: Dict[str, float]) -> RuleEvaluationResult:
        metric_val = metrics.get(rule.metric_name)
        if metric_val is None:
            return RuleEvaluationResult(
                metric_name=rule.metric_name, operator=rule.operator, threshold=rule.threshold,
                actual_value=None, passed=False, severity=rule.severity, message=f"Missing metric '{rule.metric_name}'."
            )

        op, val, th, tol = rule.operator, float(metric_val), float(rule.threshold), float(rule.tolerance)
        if op == ">=": passed = val >= (th - tol)
        elif op == "<=": passed = val <= (th + tol)
        elif op == ">": passed = val > (th - tol)
        elif op == "<": passed = val < (th + tol)
        elif op == "==": passed = abs(val - th) <= max(tol, 1e-6)
        elif op == "!=": passed = abs(val - th) > tol
        elif op == "in_range": passed = (th - tol) <= val <= (th + tol)
        else: passed = False

        status_str = "passed" if passed else "failed"
        return RuleEvaluationResult(
            metric_name=rule.metric_name, operator=rule.operator, threshold=rule.threshold,
            actual_value=val, passed=passed, severity=rule.severity,
            message=f"Rule {status_str}: {rule.metric_name} = {val:.4f} {op} {th:.4f} (sev: {rule.severity})"
        )

    @classmethod
    def evaluate_all(cls, rules: List[GateRule], metrics: Dict[str, float]) -> Tuple[str, List[RuleEvaluationResult], float, str]:
        if not rules:
            return "NEEDS_REVIEW", [], 50.0, "No rules defined."

        results = [cls.evaluate_rule(r, metrics) for r in rules]
        b_tot = sum(1 for r in results if r.severity == "blocker")
        b_pass = sum(1 for r in results if r.severity == "blocker" and r.passed)
        w_tot = sum(1 for r in results if r.severity == "warning")
        w_pass = sum(1 for r in results if r.severity == "warning" and r.passed)

        if b_tot > 0 and b_pass < b_tot:
            verdict = "REJECTED"
        elif w_tot > 0 and w_pass < w_tot:
            verdict = "NEEDS_REVIEW"
        else:
            verdict = "APPROVED_FOR_RELEASE"

        b_score = (b_pass / b_tot) if b_tot > 0 else 1.0
        w_score = (w_pass / w_tot) if w_tot > 0 else 1.0
        score = round((b_score * 75.0) + (w_score * 25.0), 2)
        summary = f"Gate Verdict: {verdict}. Blockers: {b_pass}/{b_tot}. Warnings: {w_pass}/{w_tot}. Readiness: {score}%."
        return verdict, results, score, summary
