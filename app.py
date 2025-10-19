"""Streamlit front end for the Claims Coverage Reasoner demo."""

from __future__ import annotations

import io
import json
import os
import uuid
from datetime import datetime, date, time
from typing import Any, Dict, List, Tuple

import streamlit as st
from PIL import Image, ImageDraw
from zipfile import ZipFile

from backend.reasoner import run_reasoner, continue_reasoner


APP_TITLE = "AegisAgent — Guardrails for Coverage Calls"
ALLOWED_IMAGE_TYPES = ["png", "jpg", "jpeg", "webp"]
ALLOWED_DOC_TYPES = ["pdf", "txt"]

SAMPLE_CASES = {
    "Case A - Burst Pipe (should auto-close)": "case_a",
    "Case B - Seepage Suspicion (forces debate)": "case_b",
    "Case C - Rear-End Collision (invoice scrutiny)": "case_c",
}

SAMPLE_CASE_DIR = "data/sample_cases"

STEP_FLOW: List[Dict[str, str]] = [
    {"key": "intake", "title": "Upload Evidence", "subtitle": "Photos, invoices, FNOL text"},
    {"key": "debate", "title": "Agent Debate", "subtitle": "Curator <> Interpreter <> Reviewer"},
    {"key": "decision", "title": "Decision Review", "subtitle": "Outcome, citations, follow-ups"},
]

SEVERITY_STYLES: Dict[str, Tuple[str, str]] = {
    "critical": ("#fee2e2", "#b91c1c"),
    "high": ("#fef3c7", "#b45309"),
    "medium": ("#dbeafe", "#1d4ed8"),
    "low": ("#dcfce7", "#15803d"),
}

STATUS_COLORS: Dict[str, str] = {
    "complete": "#16a34a",
    "current": "#2563eb",
    "upcoming": "#cbd5f5",
}


class SimpleUploadedFile:
    """Simple file-like wrapper used for sample case assets."""

    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data

    def getvalue(self) -> bytes:
        return self._data

    def read(self) -> bytes:  # Streamlit compatibility
        return self._data

    def seek(self, pos: int) -> None:  # Unused but keeps API parity
        pass


def load_sample_case(case_key: str) -> Dict[str, List[SimpleUploadedFile]]:
    """Load bundled sample files for the selected driver case."""

    case_dir = os.path.join(SAMPLE_CASE_DIR, case_key)
    if not os.path.exists(case_dir):
        st.error(f"Sample case directory not found: {case_dir}")
        return {"fnol_files": [], "photos": [], "invoices": []}

    fnol_files: List[SimpleUploadedFile] = []
    photos: List[SimpleUploadedFile] = []
    invoices: List[SimpleUploadedFile] = []

    for filename in os.listdir(case_dir):
        filepath = os.path.join(case_dir, filename)
        if not os.path.isfile(filepath):
            continue

        with open(filepath, "rb") as handle:
            data = handle.read()

        if filename.startswith("fnol") and filename.lower().endswith(".pdf"):
            fnol_files.append(SimpleUploadedFile(filename, data))
        elif filename.startswith("photo") and filename.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            photos.append(SimpleUploadedFile(filename, data))
        elif filename.startswith("invoice") and filename.lower().endswith(".pdf"):
            invoices.append(SimpleUploadedFile(filename, data))

    return {"fnol_files": fnol_files, "photos": photos, "invoices": invoices}


def init_state() -> None:
    if "case_id" not in st.session_state:
        st.session_state.case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"

    st.session_state.setdefault("fnol_text", "")
    st.session_state.setdefault("fnol_files", [])
    st.session_state.setdefault("photos", [])
    st.session_state.setdefault("invoices", [])
    st.session_state.setdefault("sample_fnol_files", [])
    st.session_state.setdefault("sample_photos", [])
    st.session_state.setdefault("sample_invoices", [])
    st.session_state.setdefault("dol_date", date.today())
    st.session_state.setdefault("dol_time", time(hour=12, minute=0))
    st.session_state.setdefault("agent_turns", [])
    st.session_state.setdefault("evidence", [])
    st.session_state.setdefault("expense", {})
    st.session_state.setdefault("decision", {})
    st.session_state.setdefault("citations", [])
    st.session_state.setdefault("objections", [])
    st.session_state.setdefault("metadata", {})
    st.session_state.setdefault("resume_state", {})
    st.session_state.setdefault("ran_once", False)
    st.session_state.setdefault("reviewer_checklist", {})
    st.session_state.setdefault("rfi_email_draft", "")
    st.session_state.setdefault("story_mode_active", False)
    st.session_state.setdefault("story_case_key", "")
    st.session_state.setdefault("story_cursor", 0)
    st.session_state.setdefault("story_highlights", [])
    st.session_state.setdefault("story_autoplay_done", False)
    st.session_state.setdefault("clarification_notes", [])
    st.session_state.setdefault("support_upload_flag", False)
    st.session_state.setdefault("case_closed", False)


def get_combined_uploads(key: str, sample_key: str | None = None) -> List[Any]:
    """Return combined live and sample uploads for the provided key."""

    primary = list(st.session_state.get(key) or [])
    sample_bucket = sample_key or f"sample_{key}"
    primary.extend(list(st.session_state.get(sample_bucket) or []))
    return primary


def get_upload_summary() -> Dict[str, int]:
    """Summarize uploaded artifacts for quick stats."""

    photos = len(get_combined_uploads("photos"))
    invoices = len(get_combined_uploads("invoices"))
    fnol_files = len(get_combined_uploads("fnol_files"))
    narrative = 1 if (st.session_state.get("fnol_text") or "").strip() else 0

    return {
        "photos": photos,
        "invoices": invoices,
        "fnol": fnol_files,
        "narrative": narrative,
    }


def get_step_status() -> Dict[str, str]:
    """Determine the status for each guided step."""

    summary = get_upload_summary()
    has_inputs = any(summary.values())
    agent_turns = st.session_state.get("agent_turns") or []
    decision = st.session_state.get("decision") or {}
    metadata = st.session_state.get("metadata") or {}
    rounds_completed = int(metadata.get("rounds_completed") or (1 if agent_turns else 0))
    objections = st.session_state.get("objections") or []
    blocking = any((obj.get("status", "") or "").strip().lower() == "blocking" for obj in objections)
    approval = metadata.get("approval")
    paused_for_user = bool(metadata.get("paused_for_user", False))

    statuses: Dict[str, str] = {}

    if not has_inputs:
        statuses["intake"] = "current"
        statuses["debate"] = "upcoming"
        statuses["decision"] = "upcoming"
    elif not agent_turns:
        statuses["intake"] = "complete"
        statuses["debate"] = "current"
        statuses["decision"] = "upcoming"
    else:
        statuses["intake"] = "complete"
        statuses["debate"] = "complete" if rounds_completed >= 1 else "current"
        if not decision:
            statuses["decision"] = "current"
        elif paused_for_user:
            statuses["decision"] = "current"
        elif approval is True or not blocking:
            statuses["decision"] = "complete"
        else:
            statuses["decision"] = "current"

    if st.session_state.get("case_closed"):
        statuses["decision"] = "complete"

    return statuses


def render_progress_banner(step_status: Dict[str, str]) -> None:
    """Render the guided journey banner across the top of the app."""

    segments: List[str] = ["<div class='stepper'>"]
    total = len(STEP_FLOW)

    for idx, step in enumerate(STEP_FLOW, start=1):
        status = step_status.get(step["key"], "upcoming")
        segment = f"""
        <div class="stepper__item stepper__item--{status}">
            <div class="stepper__index">{idx}</div>
            <div class="stepper__text">
                <div class="stepper__title">{step['title']}</div>
                <div class="stepper__subtitle">{step['subtitle']}</div>
            </div>
        </div>
        """
        segments.append(segment)
        if idx < total:
            segments.append("<div class='stepper__connector'></div>")

    segments.append("</div>")
    st.markdown("".join(segments), unsafe_allow_html=True)


def render_case_summary_card(upload_summary: Dict[str, int], step_status: Dict[str, str]) -> None:
    """Display a condensed case snapshot in the sidebar."""

    loss_dt = datetime.combine(st.session_state.dol_date, st.session_state.dol_time)
    status_badge = step_status.get("decision", "upcoming")
    badge_text = {
        "complete": "Ready for submission",
        "current": "Needs review",
        "upcoming": "Awaiting run",
    }.get(status_badge, "In progress")

    st.markdown(
        f"""
        <div class="case-card">
            <div class="case-card__header">
                <div>
                    <div class="case-card__label">Case ID</div>
                    <div class="case-card__value">{st.session_state.case_id}</div>
                </div>
                <span class="badge badge--{status_badge}">{badge_text}</span>
            </div>
            <div class="case-card__meta">
                <div>
                    <div class="case-card__meta-label">Loss date</div>
                    <div class="case-card__meta-value">{loss_dt.strftime("%b %d, %Y")}</div>
                </div>
                <div>
                    <div class="case-card__meta-label">Loss time</div>
                    <div class="case-card__meta-value">{loss_dt.strftime("%I:%M %p")}</div>
                </div>
            </div>
            <div class="case-card__grid">
                <div><span class="case-card__metric">{upload_summary['photos']}</span><span>Photos</span></div>
                <div><span class="case-card__metric">{upload_summary['fnol']}</span><span>FNOL PDFs</span></div>
                <div><span class="case-card__metric">{upload_summary['invoices']}</span><span>Invoices</span></div>
                <div><span class="case-card__metric">{upload_summary['narrative']}</span><span>FNOL narrative</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_evidence_entries() -> List[Dict[str, Any]]:
    """Return normalized evidence entries list."""

    evidence = st.session_state.get("evidence") or []
    if isinstance(evidence, list):
        return evidence
    if isinstance(evidence, dict):
        return evidence.get("evidence", [])
    return []


def get_expense_data() -> Dict[str, Any]:
    """Return normalized expense data dictionary."""

    expense = st.session_state.get("expense") or {}
    if isinstance(expense, dict):
        return expense
    return {}


def compute_kpis() -> List[Dict[str, Any]]:
    """Compute KPI metrics for the case run."""

    evidence_entries = get_evidence_entries()
    expense = get_expense_data()
    metadata = st.session_state.get("metadata") or {}
    objections = st.session_state.get("objections") or []
    citations = st.session_state.get("citations") or []

    blocking = sum(1 for obj in objections if "blocking" in (obj.get("status", "") or "").lower())
    resolved = sum(1 for obj in objections if "resolved" in (obj.get("status", "") or "").lower())
    rounds_completed = int(metadata.get("rounds_completed") or (1 if st.session_state.get("agent_turns") else 0))
    invoice_items = len(expense.get("line_items", []) or [])

    kpis: List[Dict[str, Any]] = [
        {
            "label": "Images analyzed",
            "value": len(evidence_entries),
            "caption": "Auto-tagged by Evidence Curator",
            "icon": "&#128247;",
            "accent": "#6366f1",
        },
        {
            "label": "Blocking objections",
            "value": blocking,
            "caption": f"{resolved} resolved so far" if resolved else "Reviewer open items",
            "icon": "&#128308;" if blocking else "&#9989;",
            "accent": "#ef4444" if blocking else "#10b981",
        },
        {
            "label": "Invoice line items",
            "value": invoice_items,
            "caption": expense.get("vendor", "No vendor detected"),
            "icon": "&#128179;",
            "accent": "#f59e0b",
        },
        {
            "label": "Policy citations",
            "value": len(citations),
            "caption": f"{rounds_completed} collaboration rounds",
            "icon": "&#128218;",
            "accent": "#0ea5e9",
        },
    ]

    return kpis


def render_kpi_cards(kpis: List[Dict[str, Any]]) -> None:
    """Render KPI cards in a single row."""

    if not kpis:
        return

    columns = st.columns(len(kpis))
    for col, metric in zip(columns, kpis):
        col.markdown(
            f"""
            <div class="kpi-card" style="border-top-color:{metric['accent']}">
                <div class="kpi-card__icon" style="color:{metric['accent']}">{metric['icon']}</div>
                <div class="kpi-card__value">{metric['value']}</div>
                <div class="kpi-card__label">{metric['label']}</div>
                <div class="kpi-card__caption">{metric['caption']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def sanitize_newlines(text: str) -> str:
    """Convert literal \\n sequences to actual newlines and trim."""

    if not text:
        return ""
    return text.replace("\\n", "\n").strip()


def format_objection_message_html(text: str) -> str:
    """Format objection message for HTML rendering with <br> breaks."""

    sanitized = sanitize_newlines(text)
    if not sanitized:
        return ""
    return "<br>".join(line.strip() for line in sanitized.splitlines())


def format_objection_message_plain(text: str) -> str:
    """Format objection message for plain text contexts (e.g., memo export)."""

    return sanitize_newlines(text)


def bytes_to_pil(uploaded_file) -> Image.Image:
    try:
        return Image.open(uploaded_file)
    except Exception:
        return Image.open(io.BytesIO(uploaded_file.getvalue()))


def make_badge(text: str, bg: str = "#EDF2FF", fg: str = "#334") -> str:
    return (
        f"<span style=\"background:{bg}; color:{fg}; padding:2px 8px; "
        f"border-radius:10px; font-size:0.8rem\">{text}</span>"
    )


def decision_color(decision: str) -> str:
    return {"Pay": "#16a34a", "Partial": "#f59e0b", "Deny": "#ef4444"}.get(decision, "#3b82f6")


def build_decision_memo() -> str:
    case_id = st.session_state.case_id
    loss_dt = datetime.combine(st.session_state.dol_date, st.session_state.dol_time).isoformat()
    decision = st.session_state.decision or {}
    objections = st.session_state.objections or []
    citations = st.session_state.citations or []
    expense = st.session_state.expense or {}
    evidence = st.session_state.evidence or []
    checklist = st.session_state.get("reviewer_checklist", {})
    clarification_notes = st.session_state.get("clarification_notes", [])

    interpreter_rec = decision.get("interpreter_recommendation")
    final_outcome = decision.get("outcome", "TBD")

    lines = [
        f"# Decision Memo - {case_id}",
        f"**Date of Loss:** {loss_dt}",
        f"**Final Outcome:** {final_outcome}",
        f"**Case Status:** {'Closed' if st.session_state.get('case_closed') else 'Open'}",
    ]

    if interpreter_rec and interpreter_rec != final_outcome:
        lines.append(f"**Interpreter Recommendation:** {interpreter_rec}")

    lines.append(f"**Rationale:** {decision.get('rationale', '(pending)')}")
    lines.append("")

    lines.append("## Objection Log")
    if objections:
        for idx, obj in enumerate(objections, 1):
            lines.append(f"{idx}. **{obj.get('type','Unknown')}** [{obj.get('status','')}]")
            message_plain = format_objection_message_plain(obj.get("message", "")) or "(no additional details)"
            for line in message_plain.splitlines():
                lines.append(f"   {line}")
    else:
        lines.append("_No blocking objections_")

    lines.append("\n## Policy Citations")
    if citations:
        for cit in citations:
            lines.append(f"- {cit.get('policy','?')} - {cit.get('section','?')} (p.{cit.get('page','?')})")
    else:
        lines.append("_No citations provided_")

    if checklist:
        lines.append("\n## Reviewer Checklist")
        for item, completed in checklist.items():
            marker = "[x]" if completed else "[ ]"
            lines.append(f"- {marker} {item}")

    if clarification_notes:
        lines.append("\n## Clarification Highlights")
        for note in clarification_notes:
            lines.append(f"- {note}")

    lines.append("\n## Expense Summary")
    if expense:
        lines.append("```json")
        lines.append(json.dumps(expense, indent=2))
        lines.append("```")
    else:
        lines.append("_No expense data_")

    lines.append("\n## Evidence Snapshot")
    if evidence:
        lines.append("```json")
        lines.append(json.dumps(evidence, indent=2))
        lines.append("```")
    else:
        lines.append("_No image evidence extracted_")

    return "\n".join(lines)


def draw_bbox_preview(img: Image.Image, observations: List[Dict[str, Any]]) -> Image.Image:
    w, h = img.size
    overlay = img.convert("RGBA").copy()
    draw = ImageDraw.Draw(overlay, "RGBA")

    for obs in observations:
        bbox = obs.get("bbox") or {}
        x = bbox.get("x", 0.1)
        y = bbox.get("y", 0.1)
        bw = bbox.get("w", 0.2)
        bh = bbox.get("h", 0.2)

        x0, y0 = int(x * w), int(y * h)
        x1, y1 = int((x + bw) * w), int((y + bh) * h)
        draw.rectangle([x0, y0, x1, y1], outline=(239, 68, 68, 255), width=3)

        label = obs.get("label", "issue")
        draw.rectangle([x0, y0 - 18, x0 + 8 + 8 * len(label), y0], fill=(239, 68, 68, 180))
        draw.text((x0 + 4, y0 - 16), label, fill="white")

    return overlay


def get_photo_file(image_name: str):
    """Find an uploaded or sample photo matching the evidence entry."""

    for file in get_combined_uploads("photos"):
        if getattr(file, "name", "") == image_name:
            return file
    return None


def format_currency(value: Any) -> str:
    """Format numbers as currency, falling back to string."""

    try:
        return f"${float(value):,.2f}"
    except Exception:
        return str(value)


def get_severity_style(severity: str | None) -> Tuple[str, str]:
    """Return background and text colors for a severity level."""

    key = (severity or "").strip().lower()
    if key in SEVERITY_STYLES:
        return SEVERITY_STYLES[key]
    return "#e5e7eb", "#374151"


def render_observation_chips(observations: List[Dict[str, Any]]) -> str:
    """Return HTML string of observation chips."""

    chips: List[str] = []
    for obs in observations:
        label = obs.get("label", "Observation")
        severity = obs.get("severity", "").title()
        bg, fg = get_severity_style(obs.get("severity"))
        chips.append(
            f"<span class='chip' style='background:{bg}; color:{fg};'>{label} ({severity or 'Unknown'})</span>"
        )
    return " ".join(chips)


def render_evidence_gallery(evidence_entries: List[Dict[str, Any]]) -> None:
    """Render the clarification gallery for evidence entries."""

    if not evidence_entries:
        st.caption("Multi‑agent claim review with policy‑backed decisions")
        return

    for entry in evidence_entries:
        image_name = entry.get("image_name", "photo")
        observations = entry.get("observations", []) or []
        with st.expander(f"{image_name} ({len(observations)} observations)", expanded=False):
            photo_file = get_photo_file(image_name)
            if photo_file:
                try:
                    pil_img = bytes_to_pil(photo_file)
                    preview = draw_bbox_preview(pil_img, observations)
                    st.image(preview, caption=f"{image_name} (annotated)", use_container_width=True)
                except Exception:
                    st.image(bytes_to_pil(photo_file), caption=image_name, use_container_width=True)

            chip_html = render_observation_chips(observations[:6])
            if chip_html:
                st.markdown(f"<div class='chip-row'>{chip_html}</div>", unsafe_allow_html=True)

            if observations:
                st.markdown("**Call-outs**")
                for obs in observations:
                    label = obs.get("label", "Observation")
                    severity = obs.get("severity", "Unknown")
                    location = obs.get("location_text", "Location not captured")
                    details = obs.get("explanation") or obs.get("notes") or ""
                    st.markdown(
                        f"- **{label}** ({severity}) at {location}  \n  {details or 'No narrative provided.'}"
                    )

            assessment = entry.get("global_assessment") or {}
            if assessment:
                st.markdown("**Global assessment**")
                st.json(assessment)

            chronology = entry.get("chronology") or {}
            if chronology:
                st.markdown("**Chronology**")
                st.json(chronology)


def render_invoice_summary(expense: Dict[str, Any]) -> None:
    """Render invoice reconciliation summary with pill badges."""

    if not expense:
        st.caption("Multi‑agent claim review with policy‑backed decisions")
        return

    vendor = expense.get("vendor", "Unknown vendor")
    total = format_currency(expense.get("total"))

    st.markdown(
        f"""
        <div class="invoice-card">
            <div class="invoice-card__header">
                <div>
                    <div class="invoice-card__label">Primary vendor</div>
                    <div class="invoice-card__vendor">{vendor}</div>
                </div>
                <div class="invoice-card__total">{total}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    line_items = expense.get("line_items", []) or []
    if not line_items:
        return

    table_rows = [
        "<table class='invoice-table'>",
        "<thead><tr><th>Line item</th><th>Amount</th><th>Status</th></tr></thead>",
        "<tbody>",
    ]

    for item in line_items:
        desc = item.get("description", "Item")
        amount = format_currency(item.get("amount"))
        status = item.get("status", "Pending")
        status_key = (status or "pending").strip().lower()
        if "match" in status_key or "approved" in status_key or "valid" in status_key:
            badge_class = "badge badge--complete"
        elif "pending" in status_key or "review" in status_key:
            badge_class = "badge badge--current"
        else:
            badge_class = "badge badge--alert"
        table_rows.append(
            f"<tr><td>{desc}</td><td>{amount}</td><td><span class='{badge_class}'>{status}</span></td></tr>"
        )

    table_rows.append("</tbody></table>")
    st.markdown("\n".join(table_rows), unsafe_allow_html=True)


def update_clarification_notes(evidence_entries: List[Dict[str, Any]], objections: List[Dict[str, Any]]) -> None:
    """Build short clarification highlights for memo and UI."""

    highlights: List[str] = []
    if evidence_entries:
        top_entry = max(evidence_entries, key=lambda e: len(e.get("observations", []) or []))
        highlights.append(
            f"{len(evidence_entries)} photos analyzed; {len(top_entry.get('observations', []) or [])} findings on {top_entry.get('image_name','photo')}."
        )

    blocking = [obj for obj in objections if "blocking" in (obj.get("status", "") or "").lower()]
    if blocking:
        highlights.append(f"{len(blocking)} blocking objection(s) remain for reviewer follow-up.")
    elif objections:
        highlights.append("Reviewer objections resolved or downgraded.")

    st.session_state.clarification_notes = highlights


def build_rfi_email(case_id: str, selected_items: List[str]) -> str:
    """Create an RFI email draft for the items the user selected."""

    if not selected_items:
        return ""

    loss_dt = datetime.combine(st.session_state.dol_date, st.session_state.dol_time)
    bullet_lines = "\n".join(f"- {sanitize_newlines(item)}" for item in selected_items)
    return (
        f"Subject: Additional documentation for case {case_id}\n\n"
        f"Hello team,\n\n"
        f"We have reviewed case {case_id} (loss date {loss_dt:%b %d, %Y}). "
        "To finalize the coverage decision we still need the following items:\n"
        f"{bullet_lines}\n\n"
        "Please reply with the requested documents or notes on where to locate them. "
        "Once received we will re-run the automated review and share the updated findings.\n\n"
        "Thank you,\n"
        "Coverage Reasoner Demo"
    )


def sync_reviewer_checklist(recommendations: List[str]) -> None:
    """Keep reviewer checklist state aligned with latest recommendations."""

    checklist = st.session_state.setdefault("reviewer_checklist", {})
    existing_keys = set(checklist.keys())
    current = set(recommendations)

    # Remove stale entries
    for item in existing_keys - current:
        checklist.pop(item, None)

    # Add new entries with default unchecked state
    for item in recommendations:
        checklist.setdefault(item, False)


def build_clarification_text(evidence_entries: List[Dict[str, Any]], expense: Dict[str, Any]) -> str:
    """Build a lightweight clarification summary for export."""

    lines: List[str] = ["Clarification Pack Summary", "==========================", ""]
    if not evidence_entries and not expense:
        lines.append("No structured evidence captured yet.")
        return "\n".join(lines)

    if evidence_entries:
        lines.append("1. Evidence Overview")
        for entry in evidence_entries:
            name = entry.get("image_name", "photo")
            observations = entry.get("observations", []) or []
            lines.append(f"   - {name}: {len(observations)} observation(s)")
            for obs in observations[:5]:
                label = obs.get("label", "Observation")
                severity = obs.get("severity", "Unknown")
                location = obs.get("location_text", "n/a")
                lines.append(f"       * {label} ({severity}) at {location}")
            if len(observations) > 5:
                lines.append(f"       * (+{len(observations) - 5} additional observations)")
        lines.append("")

    if expense:
        lines.append("2. Invoice Reconciliation")
        vendor = expense.get("vendor", "Unknown vendor")
        lines.append(f"   - Vendor: {vendor}")
        lines.append(f"   - Total: {format_currency(expense.get('total'))}")
        for line_item in (expense.get("line_items") or [])[:10]:
            desc = line_item.get("description", "Line item")
            amount = format_currency(line_item.get("amount"))
            status = line_item.get("status", "Pending")
            lines.append(f"       * {desc}: {amount} ({status})")

    return "\n".join(lines)


def build_case_packet_bytes() -> bytes:
    """Bundle decision memo, clarification pack, and checklist into a zip."""

    buffer = io.BytesIO()
    evidence_entries = get_evidence_entries()
    expense = get_expense_data()
    decision_memo = build_decision_memo()
    clarification_text = build_clarification_text(evidence_entries, expense)

    checklist = st.session_state.get("reviewer_checklist", {})
    checklist_lines = ["Reviewer Checklist", "==================", ""]
    if not checklist:
        checklist_lines.append("No reviewer recommendations were logged.")
    else:
        for item, completed in checklist.items():
            marker = "[x]" if completed else "[ ]"
            checklist_lines.append(f"{marker} {item}")

    with ZipFile(buffer, "w") as zf:
        case_id = st.session_state.case_id
        zf.writestr(f"{case_id}_decision_memo.md", decision_memo)
        zf.writestr(f"{case_id}_clarification_pack.txt", clarification_text)
        zf.writestr(f"{case_id}_reviewer_checklist.txt", "\n".join(checklist_lines))

    buffer.seek(0)
    return buffer.getvalue()


def compile_story_highlights() -> List[str]:
    """Craft narrated highlights for story mode."""

    evidence_entries = get_evidence_entries()
    expense = get_expense_data()
    decision = st.session_state.get("decision") or {}
    metadata = st.session_state.get("metadata") or {}
    objections = st.session_state.get("objections") or []

    blocking = sum(1 for obj in objections if "blocking" in (obj.get("status", "") or "").lower())
    resolved = sum(1 for obj in objections if "resolved" in (obj.get("status", "") or "").lower())
    rounds_completed = metadata.get("rounds_completed", 0)

    highlights = [
        f"Curator analyzed {len(evidence_entries)} photo(s) and captured {len(expense.get('line_items', []) or [])} invoice line items.",
        f"Interpreter recommended {decision.get('interpreter_recommendation', decision.get('outcome', 'a position'))} with {len(st.session_state.get('citations') or [])} supporting citation(s).",
    ]

    if blocking:
        highlights.append(f"Reviewer paused the run with {blocking} blocking objection(s) for follow-up.")
    elif resolved:
        highlights.append("Reviewer objections were resolved after clarification uploads.")
    else:
        highlights.append("Reviewer approved without additional objections.")

    highlights.append(f"Supervisor completed {rounds_completed} collaboration round(s); final outcome is {decision.get('outcome', 'Pending')}.")

    return highlights


def maybe_run_story_mode() -> None:
    """Auto-run a scripted sample case when story mode is active."""

    if not st.session_state.get("story_mode_active"):
        return
    if st.session_state.get("story_autoplay_done"):
        return

    case_key = st.session_state.get("story_case_key") or "case_a"
    assets = load_sample_case(case_key)
    if assets["photos"] or assets["fnol_files"] or assets["invoices"]:
        st.session_state.sample_fnol_files = assets["fnol_files"]
        st.session_state.sample_photos = assets["photos"]
        st.session_state.sample_invoices = assets["invoices"]

    st.session_state.fnol_files = []
    st.session_state.photos = []
    st.session_state.invoices = []
    st.session_state.ran_once = False

    with st.spinner("Launching story demo and running the multi-agent debate..."):
        try:
            invoke_backend()
        except Exception as exc:
            st.error(f"Story mode failed: {exc}")
            st.session_state.story_mode_active = False
            return

    st.session_state.story_highlights = compile_story_highlights()
    st.session_state.story_cursor = 0
    st.session_state.story_autoplay_done = True


def invoke_backend() -> None:
    """Invoke the backend reasoner with the current uploads."""

    dol_iso = datetime.combine(st.session_state.dol_date, st.session_state.dol_time).isoformat()

    def to_blobs(files) -> List[tuple[str, bytes]]:
        items: List[tuple[str, bytes]] = []
        for file in files or []:
            try:
                name = getattr(file, "name", "file")
                items.append((name, file.getvalue()))
            except Exception as exc:
                st.warning(f"Failed to process {getattr(file, 'name', 'file')}: {exc}")
        return items

    photos = to_blobs(st.session_state.photos) + to_blobs(st.session_state.sample_photos)
    invoices = to_blobs(st.session_state.invoices) + to_blobs(st.session_state.sample_invoices)
    fnol_files = to_blobs(st.session_state.fnol_files) + to_blobs(st.session_state.sample_fnol_files)

    result = run_reasoner(
        fnol_text=st.session_state.fnol_text or "",
        date_of_loss_iso=dol_iso,
        photo_blobs=photos,
        invoice_blobs=invoices,
        fnol_blobs=fnol_files,
        scenario_hint=None,
    )

    st.session_state.agent_turns = result.get("turns", [])
    st.session_state.objections = result.get("objections", [])
    st.session_state.citations = result.get("citations", [])
    st.session_state.decision = result.get("decision", {})
    st.session_state.expense = result.get("expense", {})
    st.session_state.evidence = result.get("evidence", [])
    st.session_state.metadata = result.get("metadata", {})
    st.session_state.resume_state = result.get("resume_state") or {}
    st.session_state.ran_once = True
    recommendations = (st.session_state.metadata or {}).get("recommendations", []) or []
    sync_reviewer_checklist(recommendations)
    update_clarification_notes(get_evidence_entries(), st.session_state.objections)
    st.session_state.rfi_email_draft = ""
    st.session_state.case_closed = False


def _convert_support_uploads(files) -> List[tuple[str, bytes]]:
    blobs: List[tuple[str, bytes]] = []
    for f in files or []:
        try:
            blobs.append((getattr(f, "name", "file"), f.getvalue()))
        except Exception:
            pass
    return blobs


def render_continue_controls() -> None:
    if st.session_state.get("case_closed"):
        return
    metadata = st.session_state.get("metadata", {}) or {}
    paused = metadata.get("paused_for_user", False)
    if not paused:
        return

    st.markdown(
        """
        <div class="cta-card">
            <div class="cta-card__title">Reviewer pause</div>
            <div class="cta-card__body">
                The reviewer flagged outstanding items. Add clarifying evidence and continue to Round 2, or move forward without uploads.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    recs = metadata.get("recommendations", []) or []
    if recs:
        st.markdown("**Reviewer requests**")
        sync_reviewer_checklist(recs)
        for idx, rec in enumerate(recs):
            key = f"resume_rec_{idx}_{abs(hash(rec)) % 10000}"
            default = st.session_state.reviewer_checklist.get(rec, False)
            st.session_state.reviewer_checklist[rec] = st.checkbox(rec, value=default, key=key)
        st.caption("Multi‑agent claim review with policy‑backed decisions")
    else:
        st.caption("Multi‑agent claim review with policy‑backed decisions")

    col1, col2 = st.columns(2)
    with col1:
        support_photos = st.file_uploader(
            "Additional photos", type=ALLOWED_IMAGE_TYPES, accept_multiple_files=True, key="support_photos"
        )
        support_fnol = st.file_uploader(
            "Additional FNOL PDFs", type=["pdf"], accept_multiple_files=True, key="support_fnol"
        )
    with col2:
        support_invoices = st.file_uploader(
            "Additional invoices / documents", type=["pdf"], accept_multiple_files=True, key="support_invoices"
        )
        st.markdown('<div class="small">Upload any clarifications the reviewer asked for above.</div>', unsafe_allow_html=True)

    col_continue, col_skip = st.columns(2)
    continue_clicked = col_continue.button("Continue Review", type="primary")
    skip_clicked = col_skip.button("Continue without uploads")

    if continue_clicked or skip_clicked:
        with st.spinner("Continuing with clarifications and supplemental evidence..." if continue_clicked else "Continuing without new uploads..."):
            dol_iso = datetime.combine(st.session_state.dol_date, st.session_state.dol_time).isoformat()
            support_photo_blobs = _convert_support_uploads(support_photos) if continue_clicked else []
            support_invoice_blobs = _convert_support_uploads(support_invoices) if continue_clicked else []
            support_fnol_blobs = _convert_support_uploads(support_fnol) if continue_clicked else []
            supplied_now = bool(support_photo_blobs or support_invoice_blobs or support_fnol_blobs)
            st.session_state.support_upload_flag = bool(st.session_state.support_upload_flag or supplied_now)

            result = continue_reasoner(
                resume_state=st.session_state.get("resume_state", {}) or {},
                fnol_text=st.session_state.fnol_text or "",
                date_of_loss_iso=dol_iso,
                support_photo_blobs=support_photo_blobs,
                support_invoice_blobs=support_invoice_blobs,
                support_fnol_blobs=support_fnol_blobs,
            )

            st.session_state.agent_turns = result.get("turns", [])
            st.session_state.objections = result.get("objections", [])
            st.session_state.citations = result.get("citations", [])
            st.session_state.decision = result.get("decision", {})
            st.session_state.expense = result.get("expense", {})
            st.session_state.evidence = result.get("evidence", [])
            st.session_state.metadata = result.get("metadata", {})
            st.session_state.resume_state = result.get("resume_state") or {}
            recommendations = (st.session_state.metadata or {}).get("recommendations", []) or []
            sync_reviewer_checklist(recommendations)
            update_clarification_notes(get_evidence_entries(), st.session_state.objections)
            st.session_state.rfi_email_draft = ""
            st.session_state.case_closed = False
            st.success("Round 2 completed.")
            st.rerun()


# --------------------------- STREAMLIT UI ---------------------------

st.set_page_config(page_title=APP_TITLE, layout="wide")
init_state()
maybe_run_story_mode()
step_status = get_step_status()
upload_summary = get_upload_summary()
kpis = compute_kpis() if st.session_state.get("agent_turns") else []

st.markdown(
    """
    <style>
    :root {
        --brand-primary: #FFC20E;
        --brand-secondary: #111827;
        --brand-surface: #ffffff;
        --brand-border: #e5e7eb;
        --brand-danger: #ef4444;
        --brand-success: #16a34a;
    }

    .small { font-size: 0.85rem; color:#58606b; }

    .stepper {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 1rem 1.5rem;
        background: linear-gradient(90deg, rgba(255,194,14,0.12), rgba(17,24,39,0.10));
        border-radius: 16px;
        margin-bottom: 1.5rem;
    }
    .stepper__item {
        display: flex;
        gap: 0.75rem;
        align-items: center;
        background: white;
        padding: 0.75rem 1rem;
        border-radius: 12px;
        min-width: 200px;
        border: 1px solid var(--brand-border);
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
    }
    .stepper__item--complete {
        border-color: rgba(22, 163, 74, 0.3);
    }
    .stepper__item--current {
        border-color: rgba(99, 102, 241, 0.35);
    }
    .stepper__index {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        background: rgba(99,102,241,0.12);
        color: #4338ca;
    }
    .stepper__item--complete .stepper__index {
        background: rgba(22, 163, 74, 0.15);
        color: #166534;
    }
    .stepper__item--current .stepper__index {
        background: rgba(99,102,241,0.18);
        color: #4f46e5;
    }
    .stepper__text { line-height: 1.2; }
    .stepper__title { font-weight: 600; font-size: 0.95rem; color:#1f2937; }
    .stepper__subtitle { font-size: 0.78rem; color:#64748b; }
    .stepper__connector {
        flex: 1;
        height: 2px;
        background: repeating-linear-gradient(90deg, rgba(99,102,241,0.35), rgba(99,102,241,0.35) 12px, transparent 12px, transparent 20px);
    }

    .case-card {
        background: white;
        border-radius: 16px;
        padding: 1rem;
        border: 1px solid var(--brand-border);
        box-shadow: 0 6px 18px rgba(30,64,175,0.06);
        margin-bottom: 1rem;
    }
    .case-card__header {
        display:flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }
    .case-card__label { font-size:0.75rem; text-transform: uppercase; letter-spacing:0.08em; color:#94a3b8; }
    .case-card__value { font-size:1.05rem; font-weight:600; color:#1f2937; }
    .case-card__meta { display:flex; gap:1rem; margin-bottom:1rem; }
    .case-card__meta-label { font-size:0.75rem; color:#9ca3af; }
    .case-card__meta-value { font-size:0.95rem; font-weight:500; color:#1f2937; }
    .case-card__grid {
        display:grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.75rem;
    }
    .case-card__grid div {
        background: var(--brand-surface);
        border-radius: 12px;
        padding: 0.75rem;
        text-align:center;
        border: 1px solid rgba(148,163,184,0.3);
        font-size: 0.8rem;
        color:#475569;
    }
    .case-card__metric {
        display:block;
        font-size:1.25rem;
        font-weight:600;
        color:#0f172a;
    }

    .badge {
        display:inline-flex;
        align-items:center;
        gap:0.35rem;
        padding:0.25rem 0.65rem;
        border-radius:999px;
        font-size:0.78rem;
        font-weight:500;
        border:1px solid transparent;
    }
    .badge--complete {
        background: rgba(22,163,74,0.12);
        color: #166534;
        border-color: rgba(22,163,74,0.2);
    }
    .badge--current {
        background: rgba(99,102,241,0.12);
        color: #4338ca;
        border-color: rgba(99,102,241,0.25);
    }
    .badge--upcoming {
        background: rgba(148,163,184,0.18);
        color: #475569;
        border-color: rgba(148,163,184,0.22);
    }
    .badge--alert {
        background: rgba(239,68,68,0.15);
        color: #b91c1c;
        border-color: rgba(239,68,68,0.25);
    }

    .kpi-card {
        background:white;
        border-radius:16px;
        padding:1rem 1.1rem;
        border:1px solid var(--brand-border);
        box-shadow:0 8px 24px rgba(15,23,42,0.05);
        border-top-width:4px;
    }
    .kpi-card__icon { font-size:1.4rem; }
    .kpi-card__value { font-size:1.6rem; font-weight:600; color:#0f172a; margin-top:0.35rem; }
    .kpi-card__label { font-size:0.85rem; color:#475569; margin-top:0.15rem; }
    .kpi-card__caption { font-size:0.75rem; color:#94a3b8; margin-top:0.25rem; }

    .chip-row { display:flex; flex-wrap:wrap; gap:0.4rem; margin:0.75rem 0; }
    .chip {
        display:inline-flex;
        align-items:center;
        padding:0.25rem 0.65rem;
        border-radius:999px;
        font-size:0.75rem;
        background:#e2e8f0;
        color:#1f2937;
    }

    .invoice-card {
        background:white;
        border-radius:16px;
        padding:1rem 1.25rem;
        border:1px solid var(--brand-border);
        margin:0.5rem 0 1rem;
    }
    .invoice-card__header {
        display:flex;
        justify-content:space-between;
        align-items:center;
    }
    .invoice-card__label { font-size:0.75rem; text-transform:uppercase; letter-spacing:0.08em; color:#94a3b8; }
    .invoice-card__vendor { font-size:1.05rem; font-weight:600; color:#0f172a; }
    .invoice-card__total { font-size:1.4rem; font-weight:600; color:#1f2937; }

    .invoice-table {
        width:100%;
        border-collapse:separate;
        border-spacing:0;
        border:1px solid var(--brand-border);
        border-radius:12px;
        overflow:hidden;
        box-shadow:0 10px 28px rgba(15,23,42,0.05);
    }
    .invoice-table th {
        background:var(--brand-surface);
        text-align:left;
        padding:0.75rem 1rem;
        font-size:0.78rem;
        color:#64748b;
    }
    .invoice-table td {
        padding:0.85rem 1rem;
        font-size:0.85rem;
        border-top:1px solid var(--brand-border);
        color:#1f2937;
    }

    .role-curator { background:rgba(255,194,14,0.10); padding:12px 14px; border-left:4px solid #FFC20E; border-radius:12px; }
    .role-interpreter { background:rgba(17,24,39,0.06); padding:12px 14px; border-left:4px solid #111827; border-radius:12px; }
    .role-reviewer { background:rgba(239,68,68,0.08); padding:12px 14px; border-left:4px solid #ef4444; border-radius:12px; }
    .role-supervisor { background:rgba(34,197,94,0.08); padding:12px 14px; border-left:4px solid #22c55e; border-radius:12px; }

    .story-panel {
        background:linear-gradient(135deg, rgba(99,102,241,0.15), rgba(59,130,246,0.1));
        border-radius:16px;
        padding:1.25rem 1.5rem;
        border:1px solid rgba(99,102,241,0.22);
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:1.25rem;
    }
    .story-panel__info { max-width:70%; color:#1e293b; }
    .story-panel__title { font-weight:600; font-size:1.1rem; }
    .story-panel__caption { font-size:0.85rem; color:#475569; margin-top:0.35rem; }

    .cta-card {
        background:white;
        border:1px dashed rgba(255,194,14,0.55);
        border-radius:16px;
        padding:1rem 1.25rem;
        margin-bottom:1rem;
    }
    .cta-card__title { font-weight:600; color:#1f2937; }
    .cta-card__body { font-size:0.85rem; color:#475569; margin-top:0.35rem; }
    </style>

<style>
/* Tweak expander header to avoid any overlay/clarity issues */
details > summary {
  position: relative;
  z-index: 0;
  background: var(--card-bg);
  color: var(--text-color);
  border: 1px solid var(--brand-border);
  border-radius: 8px;
  padding: 6px 10px;
  font-weight: 600;
}</style>
    """,
    unsafe_allow_html=True,
)

st.image(".streamlit/synechron-logo.png", width=160)
st.title(APP_TITLE)
st.caption("Multi-agent claim review with policy-backed decisions")
render_progress_banner(step_status)

st.markdown(
    """
    <style>
    /* Aptos font stack (falls back if not installed) */
    body, .stApp, .stMarkdown, .stText, .stDataFrame, p, label, input, textarea, button, li, code, pre, th, td {
      font-family: "Aptos", "Segoe UI", system-ui, -apple-system, "Roboto", Arial, sans-serif !important;
    }
    :root { --bg-app:#ffffff; --card-bg:#ffffff; --text-color:#0f172a; }
    .stApp { background-color: var(--bg-app) !important; }
    .case-card, .kpi-card, .invoice-card, .stepper__item { background: var(--card-bg) !important; color: var(--text-color) !important; }
    .case-card__label, .case-card__value, .stepper__title, .stepper__subtitle, .small { color: var(--text-color) !important; }
    </style>

<style>
/* Tweak expander header to avoid any overlay/clarity issues */
details > summary {
  position: relative;
  z-index: 0;
  background: var(--card-bg);
  color: var(--text-color);
  border: 1px solid var(--brand-border);
  border-radius: 8px;
  padding: 6px 10px;
  font-weight: 600;
}</style>
    """,
    unsafe_allow_html=True,
)


# --------------------------- SIDEBAR ---------------------------

with st.sidebar:
    st.header("Case Setup")
    render_case_summary_card(upload_summary, step_status)

    col_d, col_t = st.columns(2)
    with col_d:
        st.session_state.dol_date = st.date_input("Date of Loss", st.session_state.dol_date)
    with col_t:
        st.session_state.dol_time = st.time_input("Time of Loss", st.session_state.dol_time)

    st.divider()
    st.subheader("Upload Evidence")
    st.session_state.fnol_files = st.file_uploader("FNOL PDFs", type=["pdf"], accept_multiple_files=True)
    st.session_state.photos = st.file_uploader(
        "Photos", type=ALLOWED_IMAGE_TYPES, accept_multiple_files=True, key="photos_uploader"
    )
    st.session_state.invoices = st.file_uploader(
        "Invoices / Receipts", type=["pdf"], accept_multiple_files=True, key="invoices_uploader"
    )

    st.text_area("FNOL Narrative", key="fnol_text", height=160, help="Paste or summarize the first notice of loss.")

    st.divider()
    st.subheader("Sample & Story Mode")
    sample_choice = st.selectbox("Load sample case", ["Select..."] + list(SAMPLE_CASES.keys()))
    story_col, load_col = st.columns([1, 1])
    with load_col:
        load_clicked = st.button("Load Sample Data", use_container_width=True)
    with story_col:
        story_clicked = st.button("Play Story Demo", use_container_width=True)

    if load_clicked:
        if sample_choice and sample_choice in SAMPLE_CASES:
            assets = load_sample_case(SAMPLE_CASES[sample_choice])
            st.session_state.sample_fnol_files = assets["fnol_files"]
            st.session_state.sample_photos = assets["photos"]
            st.session_state.sample_invoices = assets["invoices"]
            st.session_state.agent_turns = []
            st.session_state.evidence = []
            st.session_state.expense = {}
            st.session_state.decision = {}
            st.session_state.citations = []
            st.session_state.objections = []
            st.session_state.metadata = {}
            st.session_state.resume_state = {}
            st.session_state.ran_once = False
            st.session_state.story_mode_active = False
            st.session_state.story_case_key = SAMPLE_CASES[sample_choice]
            st.session_state.support_upload_flag = False
            st.session_state.case_closed = False
            st.toast(f"Loaded sample case: {sample_choice}")
            st.rerun()
        else:
            st.warning("Select a sample case first.")

    if story_clicked:
        st.session_state.story_mode_active = True
        st.session_state.story_case_key = SAMPLE_CASES.get(sample_choice) or "case_a"
        st.rerun()

    if st.button("Reset Case"):
        st.session_state.sample_fnol_files = []
        st.session_state.sample_photos = []
        st.session_state.sample_invoices = []
        st.session_state.agent_turns = []
        st.session_state.evidence = []
        st.session_state.expense = {}
        st.session_state.decision = {}
        st.session_state.citations = []
        st.session_state.objections = []
        st.session_state.metadata = {}
        st.session_state.resume_state = {}
        st.session_state.pop("fnol_text", None)
        st.session_state.reviewer_checklist = {}
        st.session_state.rfi_email_draft = ""
        st.session_state.story_mode_active = False
        st.session_state.support_upload_flag = False
        st.session_state.story_highlights = []
        st.session_state.story_autoplay_done = False
        st.session_state.story_cursor = 0
        st.session_state.case_closed = False
        st.session_state.ran_once = False
        st.toast("Case reset")
        st.rerun()

    st.divider()
    if st.button("Start Coverage Review", type="primary"):
        with st.spinner("Processing claim with multi-agent system..."):
            try:
                invoke_backend()
                st.success("Claim processing complete!")
            except Exception as exc:
                st.error(f"Error processing claim: {exc}")
                if not st.session_state.ran_once:
                    st.session_state.ran_once = True

if st.session_state.story_mode_active:
    highlights = st.session_state.get("story_highlights") or []
    cursor = st.session_state.get("story_cursor", 0)
    if highlights:
        story_message = highlights[cursor % len(highlights)]
        st.markdown(
            f"""
            <div class="story-panel">
                <div class="story-panel__info">
                    <div class="story-panel__title">Story mode</div>
                    <div class="story-panel__caption">{story_message}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        story_cols = st.columns([1, 1])
        with story_cols[0]:
            if st.button("Next highlight", key="story_next"):
                st.session_state.story_cursor = (cursor + 1) % len(highlights)
        with story_cols[1]:
            if st.button("Exit story mode", key="story_exit"):
                st.session_state.story_mode_active = False
                st.session_state.story_autoplay_done = False
                st.rerun()
    else:
        st.info("Story mode will populate once the automated run completes.")


# --------------------------- MAIN FLOW ---------------------------

render_continue_controls()

with st.container():
    st.subheader("Step 1 - Evidence Intake")
    st.markdown("Use the sidebar to upload artifacts or load a sample case. Then click **Start Coverage Review**.")

    col_a, col_b = st.columns([1.4, 1])
    with col_a:
        st.markdown("#### Photos & media")
        all_photos = get_combined_uploads("photos")
        if all_photos:
            for photo in all_photos:
                try:
                    img = bytes_to_pil(photo)
                    st.image(img, caption=getattr(photo, "name", "photo"), use_container_width=True)
                except Exception:
                    st.info(f"Preview not available for {getattr(photo, 'name', 'photo')}")
        else:
            st.caption("Multi‑agent claim review with policy‑backed decisions")

        st.markdown("#### Invoices / receipts")
        all_invoices = get_combined_uploads("invoices")
        if all_invoices:
            for invoice in all_invoices:
                st.markdown(f"- {getattr(invoice, 'name', 'invoice.pdf')}")
        else:
            st.caption("Multi‑agent claim review with policy‑backed decisions")

    with col_b:
        st.markdown("#### FNOL narrative")
        narrative = (st.session_state.get("fnol_text") or "").strip() or "(No narrative provided)"
        st.write(narrative)

        st.markdown("#### FNOL attachments")
        all_fnol = get_combined_uploads("fnol_files")
        if all_fnol:
            for fnol in all_fnol:
                st.markdown(f"- {getattr(fnol, 'name', 'fnol.pdf')}")
        else:
            st.caption("Multi‑agent claim review with policy‑backed decisions")

    with st.expander("Structured Evidence (JSON preview)", expanded=False):
        if st.session_state.evidence:
            st.json(st.session_state.evidence)
        else:
            st.caption("Multi‑agent claim review with policy‑backed decisions")

with st.container():
    st.subheader("Step 2 - Agent-to-agent debate")
    if not st.session_state.agent_turns:
        st.info("Start the review to see the multi-agent collaboration timeline.")
    else:
        st.caption("Multi‑agent claim review with policy‑backed decisions")
        if kpis:
            render_kpi_cards(kpis)

        role_styles = {
            "curator": "role-curator",
            "interpreter": "role-interpreter",
            "reviewer": "role-reviewer",
            "supervisor": "role-supervisor",
        }
        role_labels = {
            "curator": "Evidence Curator",
            "interpreter": "Policy Interpreter",
            "reviewer": "Compliance Reviewer",
            "supervisor": "Supervisor",
        }

        for turn in st.session_state.agent_turns:
            role = turn.get("role", "assistant")
            label = role_labels.get(role, role.title())
            with st.chat_message(name=label):
                st.markdown(
                    f'<div class="{role_styles.get(role, "")}">{turn.get("content", "")}</div>',
                    unsafe_allow_html=True,
                )

        conversation_summary = (st.session_state.get("metadata") or {}).get("conversation_summary")
        if conversation_summary:
            with st.expander("Conversation summary"):
                st.json(conversation_summary)

with st.container():
    st.subheader("Step 3 - Decision review")
    if not st.session_state.decision:
        st.info("Start the review to generate a decision.")
    else:
        decision = st.session_state.decision
        metadata = st.session_state.get("metadata") or {}
        objections = st.session_state.get("objections") or []
        citations = st.session_state.get("citations") or []
        expense = get_expense_data()
        evidence_entries = get_evidence_entries()

        color = decision_color(decision.get("outcome", "TBD"))
        interpreter_rec = decision.get("interpreter_recommendation")
        final_outcome = decision.get("outcome", "TBD")
        rationale = decision.get("rationale", "")

        if interpreter_rec and interpreter_rec != final_outcome:
            interp_color = decision_color(interpreter_rec)
            decision_html = f'''
                <div class="case-card" style="border:1px solid rgba(99,102,241,0.25);">
                    <div class="case-card__header">
                        <div>
                            <div class="case-card__label">Final outcome</div>
                            <div class="case-card__value" style="color:{color};">{final_outcome}</div>
                        </div>
                        <span class="badge badge--current">Interpreter suggested {interpreter_rec}</span>
                    </div>
                    <div style="font-size:0.9rem; color:#475569;">{rationale}</div>
                    <div style="margin-top:0.75rem; padding:0.75rem; border-radius:10px; background:rgba(99,102,241,0.07); color:{interp_color}; font-size:0.82rem;">
                        Interpreter recommendation: {interpreter_rec}
                    </div>
                </div>
            '''
        else:
            decision_html = f'''
                <div class="case-card" style="border:1px solid rgba(99,102,241,0.25);">
                    <div class="case-card__label">Final outcome</div>
                    <div class="case-card__value" style="color:{color}; margin-bottom:0.5rem;">{final_outcome}</div>
                    <div style="font-size:0.9rem; color:#475569;">{rationale}</div>
                </div>
            '''

        st.markdown(decision_html, unsafe_allow_html=True)

        if kpis:
            st.markdown("#### Progress metrics")
            render_kpi_cards(kpis)

        insights = st.session_state.get("clarification_notes") or []
        st.markdown("#### Top clarification insights")
        if insights:
            insight_items = "".join(f"<li>{note}</li>" for note in insights)
            st.markdown(
                f"<div class='cta-card'><div class='cta-card__title'>What changed this round</div><ul>{insight_items}</ul></div>",
                unsafe_allow_html=True,
            )
        else:
            st.caption("Clarification insights will appear after the curator processes evidence.")

        st.markdown("#### Clarification pack")
        render_evidence_gallery(evidence_entries)

        st.markdown("#### Invoice reconciliation")
        render_invoice_summary(expense)

        st.markdown("#### Objection log")
        if objections:
            for obj in objections:
                status = obj.get("status", "")
                badge_class = "badge badge--alert" if "blocking" in status.lower() else "badge badge--current"
                message_html = format_objection_message_html(obj.get("message", ""))
                detail_html = ""
                if message_html:
                    detail_html = f"<br><span style='margin-left:1.5rem; color:#475569;'>{message_html}</span>"
                st.markdown(
                    f"- **{obj.get('type','Unknown')}** <span class='{badge_class}'>{status}</span>{detail_html}",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("No blocking objections.")

        st.markdown("#### Policy citations")
        if citations:
            for cit in citations:
                st.markdown(
                    f"- {cit.get('policy','?')} - {cit.get('section','?')} (p.{cit.get('page','?')})"
                )
        else:
            st.caption("No citations supplied.")

        recommendations = metadata.get("recommendations", []) or []
        if recommendations:
            st.markdown("#### Reviewer checklist")
            sync_reviewer_checklist(recommendations)
            for idx, rec in enumerate(recommendations):
                key = f"reviewer_rec_{idx}_{abs(hash(rec)) % 10000}"
                default_value = st.session_state.reviewer_checklist.get(rec, False)
                updated_value = st.checkbox(rec, value=default_value, key=key)
                st.session_state.reviewer_checklist[rec] = updated_value
            st.caption("Select items to include in the RFI email request.")
        else:
            st.caption("Reviewer called no follow-ups for this run.")

        selected_items = [item for item, done in st.session_state.reviewer_checklist.items() if done]
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("Generate RFI email", key="generate_rfi"):
                st.session_state.rfi_email_draft = build_rfi_email(st.session_state.case_id, selected_items)
        with action_col2:
            packet_bytes = build_case_packet_bytes()
            st.download_button(
                "Download case packet (ZIP)",
                packet_bytes,
                file_name=f"{st.session_state.case_id}_packet.zip",
                mime="application/zip",
            )

        if st.session_state.rfi_email_draft:
            st.markdown("#### RFI email draft")
            st.code(st.session_state.rfi_email_draft, language="markdown")

        resolved_count = sum(1 for obj in objections if "resolved" in (obj.get("status", "") or "").lower())
        rounds_completed = metadata.get("rounds_completed", 0)
        time_saved = max(5, len(evidence_entries) * 2 + len(expense.get("line_items", []) or []) + rounds_completed * 3)
        confidence = min(95, 60 + len(citations) * 5)
        metrics_cols = st.columns(3)
        metrics_cols[0].metric("Estimated time saved", f"{time_saved} min")
        metrics_cols[1].metric("Objections resolved", resolved_count)
        metrics_cols[2].metric("Confidence uplift", f"{confidence}%")

        case_state_cols = st.columns([1, 1, 1])
        with case_state_cols[0]:
            if st.session_state.get("case_closed"):
                st.success("Case closed. Decision review locked in.")
            else:
                st.info("Case remains open. Close it once you're comfortable with the decision.")

        case_state_cols[1].markdown("")

        with case_state_cols[2]:
            if st.session_state.get("case_closed"):
                if st.button("Reopen Case", key="reopen_case"):
                    st.session_state.case_closed = False
                    st.toast("Case reopened.")
                    st.rerun()
            else:
                if st.button("Close Case", key="close_case", type="primary"):
                    st.session_state.case_closed = True
                    st.toast("Case marked as closed.")
                    st.rerun()

st.markdown(
    '<div class="small">Tip: uploads and results live in session state for this browser session.</div>',
    unsafe_allow_html=True,
)







