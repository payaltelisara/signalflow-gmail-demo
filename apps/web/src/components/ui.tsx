import { ReactNode } from "react";
import { WorkflowJob } from "../api";

export function label(value?: string | null) { return (value || "not available").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
export function formatTime(value?: string) { if (!value) return "Not recorded"; const date = new Date(value); return Number.isNaN(date.getTime()) ? "Not recorded" : date.toLocaleString(); }

export function Status({ value }: { value?: string | null }) { return <span className={`status status-${value || "unknown"}`}>{label(value)}</span>; }
export function PageHeader({ title, description, actions }: { title: string; description: string; actions?: ReactNode }) { return <header className="page-header"><div><h2>{title}</h2><p>{description}</p></div>{actions && <div className="page-actions">{actions}</div>}</header>; }
export function EmptyState({ title, body, action }: { title: string; body: string; action?: ReactNode }) { return <div className="empty-state"><h3>{title}</h3><p>{body}</p>{action}</div>; }
export function Skeleton({ lines = 4 }: { lines?: number }) { return <div className="skeleton" aria-label="Loading">{Array.from({ length: lines }, (_, index) => <i key={index} style={{ width: `${88 - index * 11}%` }} />)}</div>; }

export function JobMeter({ job, onCancel, onRetry }: { job: WorkflowJob; onCancel?: () => void; onRetry?: () => void }) {
  const counters = job.counters || {}; const total = counters.total || 0; const processed = counters.processed || 0;
  return <article className="job-row"><div className="job-row-main"><div><strong>{job.name}</strong><p>{label(job.phase)}. {total ? `${processed} of ${total} records processed.` : "Waiting for worker progress."}</p></div><Status value={job.status} /></div><div className="job-stats"><span>{job.progress_percent === null || job.progress_percent === undefined ? "Progress pending" : `${job.progress_percent}%`}</span><span>Attempt {job.attempt}</span><span>{formatTime(job.updated_at)}</span>{onCancel && !["completed", "partially_completed", "failed", "cancelled"].includes(job.status) && <button className="button-quiet" onClick={onCancel}>Cancel job</button>}{onRetry && ["failed", "cancelled", "partially_completed"].includes(job.status) && <button className="button-quiet" onClick={onRetry}>Retry job</button>}</div>{job.error_message && <p className="inline-error">{job.error_message}</p>}{job.logs?.[0] && <p className="job-log">{job.logs[0].message}</p>}</article>;
}
