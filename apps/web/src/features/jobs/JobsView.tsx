import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../../api";
import { EmptyState, JobMeter, PageHeader, Skeleton } from "../../components/ui";

export function JobsView({ workspaceId }: { workspaceId: string }) {
  const jobs = useQuery({ queryKey: ["jobs", workspaceId], queryFn: () => api.jobs(workspaceId), refetchInterval: 3000 });
  const activeIds = jobs.data?.filter((job) => ["queued", "running", "retrying"].includes(job.status)).map((job) => job.id).join(",") || "";
  useEffect(() => {
    const streams = activeIds.split(",").filter(Boolean).map((id) => {
      const stream = new EventSource(`/api/v1/jobs/${id}/events?workspace_id=${encodeURIComponent(workspaceId)}`);
      stream.addEventListener("job", () => jobs.refetch());
      stream.onerror = () => stream.close();
      return stream;
    });
    return () => streams.forEach((stream) => stream.close());
  }, [activeIds, workspaceId]);
  return <section><PageHeader title="Jobs" description="Every import, analysis, enrollment, and mailbox sync is observable and recoverable." />{jobs.isLoading ? <Skeleton lines={6} /> : jobs.data?.length ? <div className="job-list">{jobs.data.map((job) => <JobMeter key={job.id} job={job} onCancel={() => api.cancelJob(job.id, workspaceId).then(() => jobs.refetch())} onRetry={() => api.retryJob(job.id, workspaceId).then(() => jobs.refetch())} />)}</div> : <EmptyState title="No jobs yet" body="Start with an import, account research run, Gmail sync, or campaign activation." />}</section>;
}
