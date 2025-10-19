"""FastAPI frontend for the Claims Coverage Reasoner demo."""

from __future__ import annotations

import base64
import io
import os
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)
from fastapi.encoders import jsonable_encoder
from fastapi.responses import (
    HTMLResponse,
    JSONResponse,
    RedirectResponse,
    StreamingResponse,
    Response,
)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageDraw

from backend.reasoner import continue_reasoner, run_reasoner


APP_TITLE = "AegisAgent - Guardrails for Coverage Calls"
ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "webp"}
ALLOWED_DOC_TYPES = {"pdf", "txt"}
SAMPLE_CASES = {
    "case_a": "Case A - Burst Pipe (should auto-close)",
    "case_b": "Case B - Seepage Suspicion (forces debate)",
    "case_c": "Case C - Rear-End Collision (invoice scrutiny)",
}
SAMPLE_CASE_DIR = os.path.join("data", "sample_cases")

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_TOTAL_MB = int(os.getenv("MAX_TOTAL_MB", "50"))
MAX_FILES_PER_TYPE = int(os.getenv("MAX_FILES_PER_TYPE", "10"))
UPLOAD_LIMIT_BYTES = MAX_TOTAL_MB * 1024 * 1024


@dataclass
class StoredUpload:
    """In-memory representation of an uploaded file."""

    filename: str
    content_type: str
    data: bytes
    size: int


@dataclass
class JobRecord:
    """State tracker for a coverage review job."""

    job_id: str
    case_id: str
    fnol_text: str
    date_of_loss_iso: str
    scenario_hint: Optional[str]
    uploads: Dict[str, List[StoredUpload]] = field(
        default_factory=lambda: {"photos": [], "invoices": [], "fnol": []}
    )
    support_upload_flag: bool = False
    story_mode: bool = False
    story_highlights: List[str] = field(default_factory=list)
    story_index: int = 0
    checklist: Dict[str, bool] = field(default_factory=dict)
    case_closed: bool = False
    status: str = "queued"
    message: str = "Queued for processing"
    result: Optional[Dict[str, Any]] = None
    resume_state: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


app = FastAPI(title=APP_TITLE)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

jobs: Dict[str, JobRecord] = {}
jobs_lock = threading.Lock()


def _now() -> datetime:
    return datetime.utcnow()


def _format_currency(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return str(value)


@lru_cache(maxsize=1)
def _load_favicon() -> bytes:
    """Generate a favicon, preferring the existing Synechron logo asset."""

    logo_path = os.path.join("static", "synechron-logo.png")
    buffer = io.BytesIO()
    try:
        with Image.open(logo_path) as img:
            icon = img.convert("RGBA")
            icon.thumbnail((32, 32), Image.LANCZOS)
            icon.save(buffer, format="ICO", sizes=[(32, 32), (16, 16)])
    except Exception:
        fallback = Image.new("RGBA", (32, 32), (24, 24, 27, 255))
        draw = ImageDraw.Draw(fallback)
        draw.rounded_rectangle((2, 2, 30, 30), radius=6, fill=(8, 145, 178, 255))
        draw.text((9, 6), "A", fill=(255, 255, 255, 255))
        fallback.save(buffer, format="ICO")
    return buffer.getvalue()


def _draw_bbox_preview(img: Image.Image, observations: List[Dict[str, Any]]) -> Image.Image:
    """Draw bounding boxes over a photo using observation metadata."""

    width, height = img.size
    overlay = img.convert("RGBA").copy()
    draw = ImageDraw.Draw(overlay, "RGBA")

    for obs in observations:
        bbox = obs.get("bbox") or {}
        x = bbox.get("x", 0.1)
        y = bbox.get("y", 0.1)
        bw = bbox.get("w", 0.2)
        bh = bbox.get("h", 0.2)

        x0, y0 = int(x * width), int(y * height)
        x1, y1 = int((x + bw) * width), int((y + bh) * height)
        draw.rectangle([x0, y0, x1, y1], outline=(239, 68, 68, 255), width=3)

        label = obs.get("label", "issue")
        draw.rectangle(
            [x0, y0 - 18, x0 + 8 + 8 * len(label), y0], fill=(239, 68, 68, 180)
        )
        draw.text((x0 + 4, y0 - 16), label, fill="white")

    return overlay


def _encoded_image(data: bytes, content_type: str) -> str:
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:{content_type};base64,{b64}"


def _to_reasoner_tuple(files: List[StoredUpload]) -> List[Tuple[str, bytes]]:
    return [(item.filename, item.data) for item in files]


def _build_kpis(job: JobRecord) -> List[Dict[str, Any]]:
    result = job.result or {}
    evidence_entries = result.get("evidence") or []
    expense = result.get("expense") or {}
    metadata = result.get("metadata") or {}
    objections = result.get("objections") or []
    citations = result.get("citations") or []

    blocking = sum(
        1 for obj in objections if "blocking" in (obj.get("status", "") or "").lower()
    )
    resolved = sum(
        1 for obj in objections if "resolved" in (obj.get("status", "") or "").lower()
    )
    rounds_completed = int(
        metadata.get("rounds_completed") or (1 if result.get("turns") else 0)
    )
    invoice_items = len(expense.get("line_items", []) or [])

    return [
        {
            "label": "Images analyzed",
            "value": len(evidence_entries),
            "caption": "Auto-tagged by Evidence Curator",
            "icon": "camera",
            "accent": "#6366f1",
        },
        {
            "label": "Blocking objections",
            "value": blocking,
            "caption": f"{resolved} resolved so far" if resolved else "Reviewer open items",
            "icon": "alert",
            "accent": "#ef4444" if blocking else "#10b981",
        },
        {
            "label": "Invoice line items",
            "value": invoice_items,
            "caption": expense.get("vendor", "No vendor detected"),
            "icon": "receipt",
            "accent": "#f59e0b",
        },
        {
            "label": "Policy citations",
            "value": len(citations),
            "caption": f"{rounds_completed} collaboration rounds",
            "icon": "book",
            "accent": "#0ea5e9",
        },
    ]


def _clarification_notes(job: JobRecord) -> List[str]:
    result = job.result or {}
    evidence_entries = result.get("evidence") or []
    objections = result.get("objections") or []
    notes: List[str] = []

    if evidence_entries:
        top_entry = max(
            evidence_entries,
            key=lambda e: len(e.get("observations", []) or []),
        )
        notes.append(
            f"{len(evidence_entries)} photos analyzed; "
            f"{len(top_entry.get('observations', []) or [])} "
            f"findings on {top_entry.get('image_name', 'photo')}."
        )

    blocking = [
        obj
        for obj in objections
        if "blocking" in (obj.get("status", "") or "").lower()
    ]
    if blocking:
        notes.append(f"{len(blocking)} blocking objection(s) remain for reviewer follow-up.")
    elif objections:
        notes.append("Reviewer objections resolved or downgraded.")

    return notes


def _story_highlights(job: JobRecord) -> List[str]:
    result = job.result or {}
    evidence_entries = result.get("evidence") or []
    expense = result.get("expense") or {}
    decision = result.get("decision") or {}
    metadata = result.get("metadata") or {}
    objections = result.get("objections") or []

    blocking = sum(
        1 for obj in objections if "blocking" in (obj.get("status", "") or "").lower()
    )
    resolved = sum(
        1 for obj in objections if "resolved" in (obj.get("status", "") or "").lower()
    )
    rounds_completed = metadata.get("rounds_completed", 0)

    highlights = [
        f"Curator analyzed {len(evidence_entries)} photo(s) and captured "
        f"{len(expense.get('line_items', []) or [])} invoice line items.",
        f"Interpreter recommended "
        f"{decision.get('interpreter_recommendation', decision.get('outcome', 'a position'))} "
        f"with {len(result.get('citations') or [])} supporting citation(s).",
    ]

    if blocking:
        highlights.append(
            f"Reviewer paused the run with {blocking} blocking objection(s) for follow-up."
        )
    elif resolved:
        highlights.append("Reviewer objections were resolved after clarification uploads.")
    else:
        highlights.append("Reviewer approved without additional objections.")

    highlights.append(
        f"Supervisor completed {rounds_completed} collaboration round(s); "
        f"final outcome is {decision.get('outcome', 'Pending')}."
    )

    return highlights


def _decision_metrics(job: JobRecord) -> Dict[str, Any]:
    result = job.result or {}
    evidence_entries = result.get("evidence") or []
    expense = result.get("expense") or {}
    metadata = result.get("metadata") or {}
    objections = result.get("objections") or []
    citations = result.get("citations") or []

    resolved_count = sum(
        1 for obj in objections if "resolved" in (obj.get("status", "") or "").lower()
    )
    rounds_completed = metadata.get("rounds_completed", 0)
    time_saved = max(
        5,
        len(evidence_entries) * 2
        + len(expense.get("line_items", []) or [])
        + rounds_completed * 3,
    )
    confidence = min(95, 60 + len(citations) * 5)

    return {
        "time_saved": time_saved,
        "resolved_objections": resolved_count,
        "confidence": confidence,
    }


def _annotated_evidence(job: JobRecord) -> Dict[str, str]:
    result = job.result or {}
    evidence_entries = result.get("evidence") or []
    photo_lookup = {
        upload.filename: upload for upload in job.uploads.get("photos", [])
    }

    previews: Dict[str, str] = {}
    for entry in evidence_entries:
        name = entry.get("image_name")
        observations = entry.get("observations", []) or []
        if not name or name not in photo_lookup:
            continue

        upload = photo_lookup[name]
        try:
            image = Image.open(io.BytesIO(upload.data))
            preview = _draw_bbox_preview(image, observations)
            buffer = io.BytesIO()
            preview.convert("RGB").save(buffer, format="PNG")
            previews[name] = _encoded_image(buffer.getvalue(), "image/png")
        except Exception:
            previews[name] = _encoded_image(upload.data, upload.content_type)

    return previews


def _build_packet(job: JobRecord) -> bytes:
    import json as json_module
    from zipfile import ZipFile

    buffer = io.BytesIO()
    result = job.result or {}
    evidence_entries = result.get("evidence") or []
    expense = result.get("expense") or {}
    decision = result.get("decision") or {}
    metadata = result.get("metadata") or {}
    objections = result.get("objections") or []
    citations = result.get("citations") or []

    loss_dt = job.date_of_loss_iso
    interpreter_rec = decision.get("interpreter_recommendation")
    final_outcome = decision.get("outcome", "TBD")

    lines = [
        f"# Decision Memo - {job.case_id}",
        f"**Date of Loss:** {loss_dt}",
        f"**Final Outcome:** {final_outcome}",
        f"**Case Status:** {'Closed' if job.case_closed else 'Open'}",
    ]
    if interpreter_rec and interpreter_rec != final_outcome:
        lines.append(f"**Interpreter Recommendation:** {interpreter_rec}")
    lines.append(f"**Rationale:** {decision.get('rationale', '(pending)')}")
    lines.append("")

    lines.append("## Objection Log")
    if objections:
        for idx, obj in enumerate(objections, 1):
            lines.append(
                f"{idx}. **{obj.get('type', 'Unknown')}** [{obj.get('status', '')}]"
            )
            message = (obj.get("message") or "").replace("\\n", "\n").strip()
            message = message or "(no additional details)"
            for part in message.splitlines():
                lines.append(f"   {part}")
    else:
        lines.append("_No blocking objections_")

    lines.append("\n## Policy Citations")
    if citations:
        for cit in citations:
            lines.append(
                f"- {cit.get('policy', '?')} - {cit.get('section', '?')} "
                f"(p.{cit.get('page', '?')})"
            )
    else:
        lines.append("_No citations provided_")

    if job.checklist:
        lines.append("\n## Reviewer Checklist")
        for item, completed in job.checklist.items():
            marker = "[x]" if completed else "[ ]"
            lines.append(f"- {marker} {item}")

    notes = _clarification_notes(job)
    if notes:
        lines.append("\n## Clarification Highlights")
        for note in notes:
            lines.append(f"- {note}")

    lines.append("\n## Expense Summary")
    if expense:
        lines.append("```json")
        lines.append(json_module.dumps(expense, indent=2))
        lines.append("```")
    else:
        lines.append("_No expense data_")

    lines.append("\n## Evidence Snapshot")
    if evidence_entries:
        lines.append("```json")
        lines.append(json_module.dumps(evidence_entries, indent=2))
        lines.append("```")
    else:
        lines.append("_No image evidence extracted_")

    clarification_lines = ["Clarification Pack Summary", "==========================", ""]
    if not evidence_entries and not expense:
        clarification_lines.append("No structured evidence captured yet.")
    else:
        if evidence_entries:
            clarification_lines.append("1. Evidence Overview")
            for entry in evidence_entries:
                name = entry.get("image_name", "photo")
                observations = entry.get("observations", []) or []
                clarification_lines.append(
                    f"   - {name}: {len(observations)} observation(s)"
                )
            clarification_lines.append("")
        if expense:
            clarification_lines.append("2. Invoice Reconciliation")
            vendor = expense.get("vendor", "Unknown vendor")
            clarification_lines.append(f"   - Vendor: {vendor}")
            clarification_lines.append(
                f"   - Total: {_format_currency(expense.get('total'))}"
            )
            for item in (expense.get("line_items") or [])[:10]:
                desc = item.get("description", "Line item")
                amount = _format_currency(item.get("amount"))
                status = item.get("status", "Pending")
                clarification_lines.append(
                    f"       * {desc}: {amount} ({status})"
                )

    checklist_lines = ["Reviewer Checklist", "==================", ""]
    if not job.checklist:
        checklist_lines.append("No reviewer recommendations were logged.")
    else:
        for item, completed in job.checklist.items():
            marker = "[x]" if completed else "[ ]"
            checklist_lines.append(f"{marker} {item}")

    with ZipFile(buffer, "w") as zf:
        zf.writestr(f"{job.case_id}_decision_memo.md", "\n".join(lines))
        zf.writestr(
            f"{job.case_id}_clarification_pack.txt", "\n".join(clarification_lines)
        )
        zf.writestr(
            f"{job.case_id}_reviewer_checklist.txt", "\n".join(checklist_lines)
        )

    buffer.seek(0)
    return buffer.getvalue()


def _read_upload(file: UploadFile) -> StoredUpload:
    data = file.file.read()
    size = len(data)
    if size == 0:
        raise HTTPException(status_code=400, detail=f"{file.filename} is empty.")
    return StoredUpload(
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        size=size,
    )


def _validate_uploads(groups: Dict[str, List[StoredUpload]]) -> None:
    total_size = 0
    for key, items in groups.items():
        if len(items) > MAX_FILES_PER_TYPE:
            raise HTTPException(
                status_code=400,
                detail=f"Too many files for {key}. Max {MAX_FILES_PER_TYPE} allowed.",
            )
        for item in items:
            if item.size > MAX_FILE_SIZE_MB * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"{item.filename} exceeds the per-file limit "
                        f"of {MAX_FILE_SIZE_MB} MB."
                    ),
                )
            total_size += item.size
    if total_size > UPLOAD_LIMIT_BYTES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Combined upload size exceeds limit "
                f"of {MAX_TOTAL_MB} MB."
            ),
        )


def _register_job(job: JobRecord) -> JobRecord:
    with jobs_lock:
        jobs[job.job_id] = job
    return job


def _get_job(job_id: str) -> JobRecord:
    with jobs_lock:
        job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


def _update_job(job: JobRecord, **changes: Any) -> None:
    for key, value in changes.items():
        setattr(job, key, value)
    job.updated_at = _now()


def _sync_reviewer_checklist(job: JobRecord) -> None:
    metadata = (job.result or {}).get("metadata") or {}
    recommendations = (metadata.get("recommendations") or [])[:50]
    existing = set(job.checklist.keys())
    current = set(recommendations)

    for stale in existing - current:
        job.checklist.pop(stale, None)
    for rec in recommendations:
        job.checklist.setdefault(rec, False)


def _process_job(job_id: str) -> None:
    job = _get_job(job_id)
    _update_job(job, status="running", message="Processing claim...")

    try:
        result = run_reasoner(
            fnol_text=job.fnol_text,
            date_of_loss_iso=job.date_of_loss_iso,
            photo_blobs=_to_reasoner_tuple(job.uploads["photos"]),
            invoice_blobs=_to_reasoner_tuple(job.uploads["invoices"]),
            fnol_blobs=_to_reasoner_tuple(job.uploads["fnol"]),
            scenario_hint=job.scenario_hint,
        )

        _update_job(
            job,
            status=(
                "needs_user_uploads"
                if result.get("metadata", {}).get("paused_for_user")
                else "completed"
            ),
            message="Awaiting reviewer input"
            if result.get("metadata", {}).get("paused_for_user")
            else "Review completed",
            result=result,
            resume_state=result.get("resume_state"),
            story_highlights=_story_highlights(job),
            story_index=0,
            support_upload_flag=False,
        )
        _sync_reviewer_checklist(job)
    except Exception as exc:  # pylint: disable=broad-except
        _update_job(
            job,
            status="error",
            message="Processing failed",
            error=str(exc),
        )


def _continue_job(job_id: str, uploads: Dict[str, List[StoredUpload]]) -> None:
    job = _get_job(job_id)
    if not job.resume_state:
        raise HTTPException(status_code=400, detail="Job cannot be resumed.")

    support_flag = any(uploads[key] for key in uploads)
    try:
        result = continue_reasoner(
            resume_state=job.resume_state,
            fnol_text=job.fnol_text,
            date_of_loss_iso=job.date_of_loss_iso,
            support_photo_blobs=_to_reasoner_tuple(uploads["photos"]),
            support_invoice_blobs=_to_reasoner_tuple(uploads["invoices"]),
            support_fnol_blobs=_to_reasoner_tuple(uploads["fnol"]),
        )

        job.uploads["photos"].extend(uploads["photos"])
        job.uploads["invoices"].extend(uploads["invoices"])
        job.uploads["fnol"].extend(uploads["fnol"])

        _update_job(
            job,
            status=(
                "needs_user_uploads"
                if result.get("metadata", {}).get("paused_for_user")
                else "completed"
            ),
            message="Awaiting reviewer input"
            if result.get("metadata", {}).get("paused_for_user")
            else "Review completed",
            result=result,
            resume_state=result.get("resume_state"),
            support_upload_flag=bool(job.support_upload_flag or support_flag),
            story_highlights=_story_highlights(job),
            story_index=0,
        )
        _sync_reviewer_checklist(job)
    except Exception as exc:  # pylint: disable=broad-except
        _update_job(
            job,
            status="error",
            message="Resume failed",
            error=str(exc),
        )


def _load_sample_case(case_key: str) -> Dict[str, List[StoredUpload]]:
    path = os.path.join(SAMPLE_CASE_DIR, case_key)
    if not os.path.isdir(path):
        raise HTTPException(status_code=404, detail="Sample case not found.")

    uploads = {"photos": [], "invoices": [], "fnol": []}
    for name in os.listdir(path):
        full_path = os.path.join(path, name)
        if not os.path.isfile(full_path):
            continue
        with open(full_path, "rb") as handle:
            data = handle.read()
        content_type = "application/octet-stream"
        suffix = name.split(".")[-1].lower()
        if suffix in ALLOWED_IMAGE_TYPES:
            content_type = f"image/{'jpeg' if suffix == 'jpg' else suffix}"
            uploads["photos"].append(
                StoredUpload(name, content_type, data, size=len(data))
            )
        elif suffix in {"pdf", "txt"}:
            content_type = "application/pdf" if suffix == "pdf" else "text/plain"
            if name.startswith("invoice"):
                uploads["invoices"].append(
                    StoredUpload(name, content_type, data, size=len(data))
                )
            elif name.startswith("fnol"):
                uploads["fnol"].append(
                    StoredUpload(name, content_type, data, size=len(data))
                )
    return uploads


def _serialize_upload(upload: StoredUpload, include_data: bool = False) -> Dict[str, Any]:
    payload = {
        "filename": upload.filename,
        "content_type": upload.content_type,
        "size": upload.size,
    }
    if include_data and upload.content_type.startswith("image/"):
        payload["preview"] = _encoded_image(upload.data, upload.content_type)
    return payload


def _job_payload(job: JobRecord) -> Dict[str, Any]:
    result = job.result or {}
    metadata = result.get("metadata") or {}
    decision = result.get("decision") or {}

    return {
        "job": {
            "id": job.job_id,
            "case_id": job.case_id,
            "status": job.status,
            "message": job.message,
            "error": job.error,
            "case_closed": job.case_closed,
            "created_at": job.created_at.isoformat() + "Z",
            "updated_at": job.updated_at.isoformat() + "Z",
            "support_upload_flag": job.support_upload_flag,
            "story_mode": job.story_mode,
            "story_highlights": job.story_highlights,
            "story_index": job.story_index,
        },
        "inputs": {
            "fnol_text": job.fnol_text,
            "date_of_loss_iso": job.date_of_loss_iso,
            "scenario_hint": job.scenario_hint,
        },
        "uploads": {
            "photos": [
                _serialize_upload(upload, include_data=True)
                for upload in job.uploads.get("photos", [])
            ],
            "invoices": [
                _serialize_upload(upload)
                for upload in job.uploads.get("invoices", [])
            ],
            "fnol": [
                _serialize_upload(upload)
                for upload in job.uploads.get("fnol", [])
            ],
        },
        "result": result,
        "resume_available": job.resume_state is not None,
        "metadata": {
            "paused_for_user": metadata.get("paused_for_user", False),
            "approval": metadata.get("approval"),
            "recommendations": metadata.get("recommendations") or [],
        },
        "decision": decision,
        "kpis": _build_kpis(job) if job.result else [],
        "clarification_notes": _clarification_notes(job) if job.result else [],
        "metrics": _decision_metrics(job) if job.result else {},
        "annotated_evidence": _annotated_evidence(job) if job.result else {},
        "checklist": job.checklist,
    }


@app.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Serve a cached favicon to satisfy browser requests."""

    return Response(content=_load_favicon(), media_type="image/x-icon")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    sample_options = [
        {"value": key, "label": label} for key, label in SAMPLE_CASES.items()
    ]
    context = {
        "request": request,
        "case_id": case_id,
        "app_title": APP_TITLE,
        "max_file_size": MAX_FILE_SIZE_MB,
        "max_total_size": MAX_TOTAL_MB,
        "max_files_per_type": MAX_FILES_PER_TYPE,
        "sample_cases": sample_options,
    }
    return templates.TemplateResponse("index.html", context)


@app.post("/submit")
async def submit_claim(
    request: Request,
    background_tasks: BackgroundTasks,
) -> RedirectResponse:
    form = await request.form()
    case_id = form.get("case_id") or f"CASE-{uuid.uuid4().hex[:8].upper()}"
    fnol_text = form.get("fnol_text", "")
    date_of_loss = form.get("date_of_loss") or datetime.utcnow().isoformat()
    scenario_hint = form.get("scenario_hint") or None

    uploads = {"photos": [], "invoices": [], "fnol": []}
    for key, bucket in [("photos", "photos"), ("invoices", "invoices"), ("fnol_files", "fnol")]:
        files = form.getlist(key)
        for file in files:
            uploads[bucket].append(_read_upload(file))

    _validate_uploads(uploads)
    job = JobRecord(
        job_id=str(uuid.uuid4()),
        case_id=case_id,
        fnol_text=fnol_text,
        date_of_loss_iso=date_of_loss,
        scenario_hint=scenario_hint,
        uploads=uploads,
    )
    _register_job(job)
    background_tasks.add_task(_process_job, job.job_id)

    return RedirectResponse(url=f"/jobs/{job.job_id}", status_code=303)


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
async def job_detail(job_id: str, request: Request) -> HTMLResponse:
    job = _get_job(job_id)
    context = {
        "request": request,
        "job_id": job.job_id,
        "case_id": job.case_id,
        "app_title": APP_TITLE,
    }
    return templates.TemplateResponse("job.html", context)


@app.get("/api/claims/{job_id}")
async def job_status(job_id: str) -> JSONResponse:
    job = _get_job(job_id)
    payload = _job_payload(job)
    return JSONResponse(jsonable_encoder(payload))


@app.post("/api/claims/{job_id}/continue")
async def resume_claim(
    job_id: str,
    background_tasks: BackgroundTasks,
    photos: List[UploadFile] = File(default=[]),
    invoices: List[UploadFile] = File(default=[]),
    fnol_files: List[UploadFile] = File(default=[]),
) -> JSONResponse:
    uploads = {"photos": [], "invoices": [], "fnol": []}
    for file in photos:
        uploads["photos"].append(_read_upload(file))
    for file in invoices:
        uploads["invoices"].append(_read_upload(file))
    for file in fnol_files:
        uploads["fnol"].append(_read_upload(file))

    _validate_uploads(uploads)
    background_tasks.add_task(_continue_job, job_id, uploads)
    return JSONResponse({"status": "accepted"})


@app.post("/api/claims/{job_id}/checklist")
async def update_checklist(
    job_id: str,
    items: List[str] = Form(default=[]),
) -> JSONResponse:
    job = _get_job(job_id)
    new_state = {item: True for item in items}
    for key in list(job.checklist.keys()):
        job.checklist[key] = new_state.get(key, False)
    _update_job(job)
    return JSONResponse({"status": "ok", "checklist": job.checklist})


@app.post("/api/claims/{job_id}/close")
async def close_case(job_id: str) -> JSONResponse:
    job = _get_job(job_id)
    job.case_closed = True
    _update_job(job, message="Case closed")
    return JSONResponse({"status": "ok"})


@app.post("/api/claims/{job_id}/reopen")
async def reopen_case(job_id: str) -> JSONResponse:
    job = _get_job(job_id)
    job.case_closed = False
    _update_job(job, message="Case reopened")
    return JSONResponse({"status": "ok"})


@app.post("/api/claims/{job_id}/email")
async def generate_email(job_id: str) -> JSONResponse:
    job = _get_job(job_id)
    selected = [item for item, done in job.checklist.items() if done]
    if not selected:
        raise HTTPException(
            status_code=400, detail="Select at least one checklist item."
        )
    loss_dt = job.date_of_loss_iso
    bullet_lines = "\n".join(f"- {item}" for item in selected)
    email = (
        f"Subject: Additional documentation for case {job.case_id}\n\n"
        f"Hello team,\n\n"
        f"We have reviewed case {job.case_id} (loss date {loss_dt}). "
        "To finalize the coverage decision we still need the following items:\n"
        f"{bullet_lines}\n\n"
        "Please reply with the requested documents or notes on where to locate them. "
        "Once received we will re-run the automated review and share the updated findings.\n\n"
        "Thank you,\n"
        "Coverage Reasoner Demo"
    )
    _update_job(job)
    return JSONResponse({"email": email})


@app.get("/api/claims/{job_id}/packet")
async def download_packet(job_id: str) -> StreamingResponse:
    job = _get_job(job_id)
    if not job.result:
        raise HTTPException(status_code=400, detail="Decision packet unavailable.")
    archive = _build_packet(job)
    filename = f"{job.case_id}_packet.zip"
    return StreamingResponse(
        io.BytesIO(archive),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/demo/sample")
async def run_sample(
    background_tasks: BackgroundTasks,
    case_key: str = Form(...),
) -> RedirectResponse:
    if case_key not in SAMPLE_CASES:
        raise HTTPException(status_code=404, detail="Sample not available.")
    uploads = _load_sample_case(case_key)
    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    job = JobRecord(
        job_id=str(uuid.uuid4()),
        case_id=case_id,
        fnol_text="",
        date_of_loss_iso=datetime.utcnow().isoformat(),
        scenario_hint=case_key,
        uploads=uploads,
        story_mode=False,
    )
    _register_job(job)
    background_tasks.add_task(_process_job, job.job_id)
    return RedirectResponse(url=f"/jobs/{job.job_id}", status_code=303)


@app.post("/demo/story")
async def run_story(
    background_tasks: BackgroundTasks,
    case_key: str = Form("case_a"),
) -> RedirectResponse:
    uploads = _load_sample_case(case_key)
    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    job = JobRecord(
        job_id=str(uuid.uuid4()),
        case_id=case_id,
        fnol_text="",
        date_of_loss_iso=datetime.utcnow().isoformat(),
        scenario_hint=case_key,
        uploads=uploads,
        story_mode=True,
    )
    _register_job(job)
    background_tasks.add_task(_process_job, job.job_id)
    return RedirectResponse(url=f"/jobs/{job.job_id}", status_code=303)


@app.post("/api/story/{job_id}/next")
async def story_next(job_id: str) -> JSONResponse:
    job = _get_job(job_id)
    if not job.story_highlights:
        raise HTTPException(status_code=400, detail="Story highlights unavailable.")
    job.story_index = (job.story_index + 1) % len(job.story_highlights)
    _update_job(job)
    return JSONResponse({"index": job.story_index})


@app.post("/api/story/{job_id}/reset")
async def story_reset(job_id: str) -> JSONResponse:
    job = _get_job(job_id)
    job.story_index = 0
    _update_job(job)
    return JSONResponse({"index": job.story_index})


@app.get("/healthz")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}
