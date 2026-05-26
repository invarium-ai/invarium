from __future__ import annotations

import html
from typing import Any


_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f8f9fa;color:#212529;font-size:14px;line-height:1.5}
.wrap{max-width:960px;margin:0 auto;padding:24px 16px}
header{background:#1a1a2e;color:#fff;padding:20px 24px;border-radius:8px;margin-bottom:20px}
header h1{font-size:20px;font-weight:700;letter-spacing:.5px}
header .meta{font-size:12px;color:#adb5bd;margin-top:6px}
.summary-bar{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:20px}
.stat{background:#fff;border:1px solid #dee2e6;border-radius:8px;padding:14px 20px;flex:1;min-width:120px}
.stat .label{font-size:11px;color:#6c757d;text-transform:uppercase;letter-spacing:.5px}
.stat .value{font-size:22px;font-weight:700;margin-top:2px}
.card{background:#fff;border:1px solid #dee2e6;border-radius:8px;margin-bottom:16px;overflow:hidden}
.card-header{display:flex;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid #dee2e6}
.card-header h2{font-size:15px;font-weight:600;flex:1}
.badge{display:inline-block;font-size:11px;font-weight:700;padding:2px 8px;border-radius:4px;letter-spacing:.4px}
.badge-pass{background:#d1fae5;color:#065f46}
.badge-fail{background:#fee2e2;color:#991b1b}
.badge-regression{background:#fef3c7;color:#92400e}
.card-body{padding:16px 18px}
.metrics{display:flex;gap:16px;flex-wrap:wrap;margin-bottom:12px}
.metric{min-width:100px}
.metric .m-label{font-size:11px;color:#6c757d;text-transform:uppercase;letter-spacing:.4px}
.metric .m-value{font-size:16px;font-weight:600;margin-top:1px}
.flaky-warn{background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;padding:8px 12px;font-size:12px;color:#92400e;margin-bottom:10px}
.section-title{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:#6c757d;margin:12px 0 6px}
.pill-list{display:flex;flex-wrap:wrap;gap:6px}
.pill{font-size:11px;background:#e9ecef;border-radius:4px;padding:2px 8px}
.pill-danger{background:#fee2e2;color:#991b1b}
.pill-warn{background:#fef3c7;color:#92400e}
.pill-info{background:#dbeafe;color:#1e40af}
.fail-list{list-style:none;margin-top:4px}
.fail-list li{font-size:12px;color:#6b7280;padding:3px 0 3px 12px;border-left:3px solid #fca5a5;margin-bottom:4px}
.comparison{background:#fff;border:1px solid #dee2e6;border-radius:8px;margin-bottom:16px}
.comparison-header{padding:14px 18px;border-bottom:1px solid #dee2e6;display:flex;align-items:center;gap:10px}
.comparison-header h2{font-size:15px;font-weight:600;flex:1}
.comparison-body{padding:16px 18px}
.regression-item{border-left:4px solid #f59e0b;padding:10px 14px;margin-bottom:10px;background:#fffbeb;border-radius:0 6px 6px 0}
.regression-item h3{font-size:13px;font-weight:600;margin-bottom:6px}
.regression-detail{font-size:12px;color:#6b7280;margin-top:3px}
.path-change{font-size:12px;color:#6b7280;padding:6px 10px;background:#f8f9fa;border-radius:4px;margin-top:6px;font-family:monospace}
.no-issues{font-size:13px;color:#059669}
.tool-bar-wrap{margin-top:8px}
.tool-bar-label{font-size:11px;color:#6c757d;margin-bottom:3px}
.tool-bar{display:flex;align-items:center;gap:8px;margin-bottom:4px}
.tool-bar .name{font-size:11px;width:110px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tool-bar .bar-bg{flex:1;background:#e9ecef;border-radius:3px;height:8px}
.tool-bar .bar-fill{background:#6366f1;border-radius:3px;height:8px}
.tool-bar .pct{font-size:11px;color:#6c757d;width:36px;text-align:right}
footer{text-align:center;font-size:11px;color:#adb5bd;margin-top:24px;padding-top:16px;border-top:1px solid #dee2e6}
"""


def _e(text: Any) -> str:
    return html.escape(str(text))


def _badge(report: dict[str, Any]) -> str:
    if report.get("failed_runs", 0) > 0:
        return '<span class="badge badge-fail">FAIL</span>'
    return '<span class="badge badge-pass">PASS</span>'


def _regression_badge() -> str:
    return '<span class="badge badge-regression">REGRESSION</span>'


def _tool_bars(tool_presence: dict[str, float]) -> str:
    if not tool_presence:
        return ""
    bars = []
    for name, rate in sorted(tool_presence.items(), key=lambda x: -x[1]):
        fill_pct = min(rate, 100)
        bars.append(
            f'<div class="tool-bar">'
            f'<span class="name" title="{_e(name)}">{_e(name)}</span>'
            f'<div class="bar-bg"><div class="bar-fill" style="width:{fill_pct:.1f}%"></div></div>'
            f'<span class="pct">{rate:.0f}%</span>'
            f"</div>"
        )
    return (
        '<div class="tool-bar-wrap">'
        '<div class="tool-bar-label">Tool usage</div>'
        + "".join(bars)
        + "</div>"
    )


def _report_card(report: dict[str, Any], regression_names: set[str]) -> str:
    name = report["test_name"]
    is_regression = name in regression_names and not report.get("failed_runs", 0)
    badge = _regression_badge() if is_regression else _badge(report)

    flakiness = report.get("flakiness_score", 0.0)
    flaky_html = ""
    if flakiness > 0:
        label = "high" if flakiness >= 0.5 else "moderate" if flakiness >= 0.2 else "low"
        flaky_html = (
            f'<div class="flaky-warn">&#9888; Flaky ({label}): score {flakiness:.3f}'
            + (" &mdash; unstable tool paths" if report.get("unstable_tool_paths") else "")
            + "</div>"
        )

    avg_lat = report.get("average_latency")
    avg_cost = report.get("average_cost")

    metrics_html = (
        f'<div class="metrics">'
        f'<div class="metric"><div class="m-label">Runs</div><div class="m-value">{report["total_runs"]}</div></div>'
        f'<div class="metric"><div class="m-label">Passed</div><div class="m-value" style="color:#059669">{report["passed_runs"]}</div></div>'
        f'<div class="metric"><div class="m-label">Failed</div><div class="m-value" style="color:#dc2626">{report["failed_runs"]}</div></div>'
        f'<div class="metric"><div class="m-label">Success</div><div class="m-value">{report["success_rate"]:.1f}%</div></div>'
        f'<div class="metric"><div class="m-label">Avg steps</div><div class="m-value">{report["average_steps"]:.1f}</div></div>'
        + (f'<div class="metric"><div class="m-label">Avg latency</div><div class="m-value">{avg_lat:.2f}s</div></div>' if avg_lat is not None else "")
        + (f'<div class="metric"><div class="m-label">Avg cost</div><div class="m-value">${avg_cost:.4f}</div></div>' if avg_cost is not None else "")
        + "</div>"
    )

    failure_cats = report.get("failure_categories", {})
    cats_html = ""
    if failure_cats:
        pills = "".join(f'<span class="pill pill-danger">{_e(c)}: {n}</span>' for c, n in failure_cats.items())
        cats_html = f'<div class="section-title">Failure Categories</div><div class="pill-list">{pills}</div>'

    failure_reasons = report.get("failure_reasons", [])
    failures_html = ""
    if failure_reasons:
        items = "".join(f"<li>{_e(r)}</li>" for r in failure_reasons)
        failures_html = f'<div class="section-title">Failure Details</div><ul class="fail-list">{items}</ul>'

    tool_html = _tool_bars(report.get("tool_presence", {}))

    paths = report.get("common_tool_paths", [])
    paths_html = ""
    if paths:
        path_pills = "".join(
            f'<span class="pill pill-info">{_e(" → ".join(p["path"]) or "(no tools)")} &nbsp;{p["rate"]:.0f}%</span>'
            for p in paths
        )
        paths_html = f'<div class="section-title">Common Tool Paths</div><div class="pill-list">{path_pills}</div>'

    return (
        f'<div class="card">'
        f'<div class="card-header">{badge}<h2>{_e(name)}</h2></div>'
        f'<div class="card-body">'
        + flaky_html
        + metrics_html
        + cats_html
        + failures_html
        + tool_html
        + paths_html
        + "</div></div>"
    )


def _comparison_section(comparison: dict[str, Any]) -> str:
    if not comparison:
        return ""
    summary = comparison.get("summary", "")
    regressions = comparison.get("regressions", [])
    matched = comparison.get("matched_tests", [])
    current_only = comparison.get("current_only_tests", [])
    baseline_only = comparison.get("baseline_only_tests", [])

    status_badge = (
        '<span class="badge badge-regression">REGRESSION</span>'
        if regressions
        else '<span class="badge badge-pass">OK</span>'
    )

    meta_pills = ""
    if matched:
        meta_pills += "".join(f'<span class="pill">{_e(n)}</span>' for n in matched)
    if current_only:
        meta_pills += "".join(f'<span class="pill pill-info">new: {_e(n)}</span>' for n in current_only)
    if baseline_only:
        meta_pills += "".join(f'<span class="pill pill-warn">removed: {_e(n)}</span>' for n in baseline_only)

    regression_items = ""
    for reg in regressions:
        path_change = reg.get("primary_path_change")
        path_html = ""
        if path_change:
            prev = " → ".join(path_change["previous_path"]) or "(no tools)"
            curr = " → ".join(path_change["current_path"]) or "(no tools)"
            path_html = f'<div class="path-change">Path: {_e(prev)} ({path_change["previous_rate"]:.0f}%) → {_e(curr)} ({path_change["current_rate"]:.0f}%)</div>'
        drops = "".join(
            f'<div class="regression-detail">&#8595; {_e(d["tool_name"])}: {d["previous_rate"]:.0f}% → {d["current_rate"]:.0f}%</div>'
            for d in reg.get("tool_coverage_drops", [])
        )
        lat_html = f'<div class="regression-detail">Latency delta: {reg["latency_delta"]:+.2f}s</div>' if reg.get("latency_delta") is not None else ""
        cost_html = f'<div class="regression-detail">Cost delta: ${reg["cost_delta"]:+.4f}</div>' if reg.get("cost_delta") is not None else ""
        cats = reg.get("failure_categories", {})
        cats_html = ""
        if cats:
            pills = "".join(f'<span class="pill pill-danger">{_e(c)}: {n}</span>' for c, n in cats.items())
            cats_html = f'<div style="margin-top:6px"><div class="pill-list">{pills}</div></div>'
        regression_items += (
            f'<div class="regression-item">'
            f'<h3>{_e(reg["test_name"])}</h3>'
            f'<div class="regression-detail">Success: {reg["previous_success_rate"]:.1f}% → {reg["current_success_rate"]:.1f}% &nbsp;|&nbsp; Step delta: {reg["step_delta"]:+.1f}</div>'
            + lat_html + cost_html + drops + cats_html + path_html
            + "</div>"
        )

    body = (
        f'<div class="regression-detail" style="margin-bottom:10px">{_e(summary)}</div>'
        + (f'<div class="pill-list" style="margin-bottom:12px">{meta_pills}</div>' if meta_pills else "")
        + (regression_items if regression_items else '<div class="no-issues">&#10003; No regressions detected</div>')
    )

    return (
        f'<div class="comparison">'
        f'<div class="comparison-header">{status_badge}<h2>Baseline Comparison</h2></div>'
        f'<div class="comparison-body">{body}</div>'
        f"</div>"
    )


def render_html_report(session_data: dict[str, Any]) -> str:
    created_at = session_data.get("created_at", "")
    suite_id = session_data.get("suite_id", "")
    reports = session_data.get("reports", [])
    comparison = session_data.get("baseline_comparison", {})
    regression_names = {r["test_name"] for r in comparison.get("regressions", [])}

    total = len(reports)
    passed = sum(1 for r in reports if not r.get("failed_runs", 0))
    failed = total - passed
    flaky = sum(1 for r in reports if r.get("flakiness_score", 0) > 0)

    summary_bar = (
        f'<div class="summary-bar">'
        f'<div class="stat"><div class="label">Tests</div><div class="value">{total}</div></div>'
        f'<div class="stat"><div class="label">Passed</div><div class="value" style="color:#059669">{passed}</div></div>'
        f'<div class="stat"><div class="label">Failed</div><div class="value" style="color:#dc2626">{failed}</div></div>'
        f'<div class="stat"><div class="label">Flaky</div><div class="value" style="color:#d97706">{flaky}</div></div>'
        + (f'<div class="stat"><div class="label">Regressions</div><div class="value" style="color:#d97706">{len(comparison.get("regressions", []))}</div></div>' if comparison else "")
        + "</div>"
    )

    cards = "".join(_report_card(r, regression_names) for r in reports)
    comp_section = _comparison_section(comparison)
    meta_parts = [f"Generated: {_e(created_at)}"]
    if suite_id:
        meta_parts.append(f"Suite: {_e(suite_id)}")

    return (
        "<!doctype html><html lang='en'><head>"
        "<meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>AgentCheck Report</title>"
        f"<style>{_CSS}</style>"
        "</head><body><div class='wrap'>"
        f"<header><h1>AgentCheck Report</h1><div class='meta'>{' &nbsp;|&nbsp; '.join(meta_parts)}</div></header>"
        + summary_bar
        + cards
        + comp_section
        + "<footer>Generated by AgentCheck</footer>"
        "</div></body></html>\n"
    )
