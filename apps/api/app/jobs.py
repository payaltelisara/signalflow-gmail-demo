from typing import Any

from sqlalchemy.orm import Session

from .models import WorkflowJob, WorkflowJobLog, utcnow


def job_data(job: WorkflowJob, logs: list[WorkflowJobLog] | None = None) -> dict[str, Any]:
    total = int((job.counters or {}).get("total", 0) or 0)
    processed = int((job.counters or {}).get("processed", 0) or 0)
    return {
        "id": job.id, "type": job.job_type, "name": job.name, "status": job.status, "phase": job.phase,
        "resource_type": job.resource_type, "resource_id": job.resource_id, "counters": job.counters or {},
        "progress_percent": min(100, round(processed * 100 / total)) if total else None,
        "error_message": job.error_message, "idempotency_key": job.idempotency_key, "attempt": job.attempt,
        "cancellation_requested": job.cancellation_requested, "queued_at": job.queued_at, "started_at": job.started_at,
        "completed_at": job.completed_at, "updated_at": job.updated_at,
        "logs": [{"level": item.level, "message": item.message, "context": item.context or {}, "created_at": item.created_at} for item in logs or []],
    }


def create_job(db: Session, *, workspace_id: str, created_by: str | None, job_type: str, name: str, idempotency_key: str, resource_type: str | None = None, resource_id: str | None = None, counters: dict | None = None, details: dict | None = None) -> WorkflowJob:
    existing = db.query(WorkflowJob).filter(WorkflowJob.workspace_id == workspace_id, WorkflowJob.idempotency_key == idempotency_key).first()
    if existing:
        return existing
    job = WorkflowJob(workspace_id=workspace_id, created_by=created_by, job_type=job_type, name=name, resource_type=resource_type, resource_id=resource_id, idempotency_key=idempotency_key, counters=counters or {}, details=details or {})
    db.add(job); db.flush()
    log_job(db, job, "Queued", {"phase": "queued"})
    return job


def log_job(db: Session, job: WorkflowJob, message: str, context: dict | None = None, level: str = "info") -> None:
    db.add(WorkflowJobLog(job_id=job.id, level=level, message=message, context=context or {}))


def update_job(db: Session, job: WorkflowJob, *, status: str | None = None, phase: str | None = None, counters: dict | None = None, error_message: str | None = None, message: str | None = None, context: dict | None = None) -> WorkflowJob:
    if status:
        job.status = status
        if status == "running" and not job.started_at:
            job.started_at = utcnow()
        if status in {"completed", "partially_completed", "failed", "cancelled"}:
            job.completed_at = utcnow()
    if phase:
        job.phase = phase
    if counters is not None:
        job.counters = counters
    if error_message is not None:
        job.error_message = error_message
    if message:
        log_job(db, job, message, context, "error" if status == "failed" else "info")
    return job


def job_cancelled(job: WorkflowJob | None) -> bool:
    return bool(job and job.cancellation_requested)
