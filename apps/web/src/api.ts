const base = "/api/v1";

let csrfToken = "";
export const setCsrf = (value: string) => { csrfToken = value; };
export const restoreCsrfFromCookie = () => {
  const match = document.cookie.split("; ").find((cookie) => cookie.startsWith("signalflow_csrf="));
  csrfToken = match ? decodeURIComponent(match.slice("signalflow_csrf=".length)) : "";
};

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (csrfToken && !["GET", "HEAD"].includes(options.method || "GET")) headers.set("X-CSRF-Token", csrfToken);
  const response = await fetch(`${base}${path}`, { ...options, headers, credentials: "include" });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Request failed");
  }
  return response.json() as Promise<T>;
}

export const api = {
  login: (email: string, password: string) => request<{ csrf_token: string }>("/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) }),
  session: () => request<Session>("/auth/session"),
  logout: () => request("/auth/logout", { method: "POST" }),
  createImport: (workspaceId: string, file: File, importKind: "leads" | "accounts") => {
    const body = new FormData(); body.append("file", file);
    return request<ImportRecord>(`/imports?workspace_id=${encodeURIComponent(workspaceId)}&import_kind=${importKind}`, { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body });
  },
  saveMapping: (id: string, workspaceId: string, mapping: Record<string, string>) => request<ImportRecord>(`/imports/${id}/mapping?workspace_id=${encodeURIComponent(workspaceId)}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mapping }) }),
  startImport: (id: string, workspaceId: string) => request<ImportRecord>(`/imports/${id}/start`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  importStatus: (id: string, workspaceId: string) => request<ImportRecord>(`/imports/${id}?workspace_id=${encodeURIComponent(workspaceId)}`),
  importErrors: (id: string, workspaceId: string) => request<RowError[]>(`/imports/${id}/errors?workspace_id=${encodeURIComponent(workspaceId)}`),
  leads: (workspaceId: string, filter = "") => request<Lead[]>(`/leads?workspace_id=${encodeURIComponent(workspaceId)}${filter}`),
  companies: (workspaceId: string) => request<Company[]>(`/companies?workspace_id=${encodeURIComponent(workspaceId)}`),
  recalculateCompanies: (workspaceId: string) => request<{ accounts_recalculated: number; qualified_accounts: number }>("/companies/recalculate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  queueAccountResearch: (workspaceId: string) => request<{ queued: number }>("/companies/ai-research", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  lead: (id: string, workspaceId: string) => request<LeadDetail>(`/leads/${id}?workspace_id=${encodeURIComponent(workspaceId)}`),
  retryLeadAi: (id: string, workspaceId: string) => request<{ lead_id: string; status: string }>(`/leads/${id}/ai-retry`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  outreachDrafts: (workspaceId: string, status = "") => request<OutreachDraft[]>(`/outreach-drafts?workspace_id=${encodeURIComponent(workspaceId)}${status ? `&status_filter=${status}` : ""}`),
  replies: (workspaceId: string) => request<Reply[]>(`/outreach-inbox?workspace_id=${encodeURIComponent(workspaceId)}`),
  analytics: (workspaceId: string) => request<Analytics>(`/analytics/overview?workspace_id=${encodeURIComponent(workspaceId)}`),
  reviewOutreachDraft: (id: string, workspaceId: string, status: "approved" | "rejected", reason: string) => request<OutreachDraft>(`/outreach-drafts/${id}/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId, status, reason }) }),
  export: (workspaceId: string, kind: string) => request<{ download_url: string; row_count: number }>("/exports", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId, kind }) }),
  audit: (workspaceId: string) => request<Audit[]>(`/audit-logs?workspace_id=${encodeURIComponent(workspaceId)}`),
  ollama: () => request<{ required: boolean; ready: boolean; configured_model: string | null; detail: string }>("/integrations/ollama/test"),
  jobs: (workspaceId: string, resourceId = "") => request<WorkflowJob[]>(`/jobs?workspace_id=${encodeURIComponent(workspaceId)}${resourceId ? `&resource_id=${encodeURIComponent(resourceId)}` : ""}`),
  cancelJob: (id: string, workspaceId: string) => request<WorkflowJob>(`/jobs/${id}/cancel`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  retryJob: (id: string, workspaceId: string) => request<WorkflowJob>(`/jobs/${id}/retry`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  campaigns: (workspaceId: string) => request<Campaign[]>(`/campaigns?workspace_id=${encodeURIComponent(workspaceId)}`),
  campaign: (id: string, workspaceId: string) => request<Campaign>(`/campaigns/${id}?workspace_id=${encodeURIComponent(workspaceId)}`),
  campaignWorkspace: (id: string, workspaceId: string) => request<CampaignWorkspace>(`/campaigns/${id}/workspace?workspace_id=${encodeURIComponent(workspaceId)}`),
  importCampaignAudience: (id: string, workspaceId: string, file: File, kind: "auto" | "accounts" | "leads" = "auto") => { const body = new FormData(); body.append("file", file); return request<{ import: ImportRecord; job?: WorkflowJob; detected_kind: string }>(`/campaigns/${id}/audience/import?workspace_id=${encodeURIComponent(workspaceId)}&kind=${kind}`, { method: "POST", headers: { "Idempotency-Key": crypto.randomUUID() }, body }); },
  prepareCampaign: (id: string, workspaceId: string) => request<CampaignWorkspace>(`/campaigns/${id}/prepare`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  updateCampaignSequence: (id: string, payload: CampaignSequencePayload) => request<CampaignWorkspace>(`/campaigns/${id}/sequence`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  generateCampaignSequence: (id: string, payload: CampaignSequenceBrief) => request<CampaignWorkspace>(`/campaigns/${id}/sequence/generate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  updateCampaignDelivery: (id: string, payload: CampaignDeliveryPayload) => request<CampaignWorkspace>(`/campaigns/${id}/delivery`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  setCampaignAudienceMember: (id: string, memberId: string, workspaceId: string, action: "include" | "exclude") => request<CampaignWorkspace>(`/campaigns/${id}/audience/${memberId}/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  createCampaign: (payload: CampaignInput) => request<Campaign>("/campaigns", { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify(payload) }),
  campaignAction: (id: string, workspaceId: string, action: "approve" | "pause" | "resume" | "cancel") => request<Campaign>(`/campaigns/${id}/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  testCampaign: (id: string, workspaceId: string, testRecipient?: string) => request<{ status: string; recipient: string }>(`/campaigns/${id}/test`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId, test_recipient: testRecipient || null }) }),
  activateCampaign: (id: string, workspaceId: string) => request<{ campaign: Campaign; job: WorkflowJob }>(`/campaigns/${id}/activate`, { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  gmail: (workspaceId: string) => request<GmailIntegration>(`/integrations/gmail?workspace_id=${encodeURIComponent(workspaceId)}`),
  connectSmtpImap: (workspaceId: string) => request<{ mailbox: Mailbox }>("/integrations/smtp-imap/connect", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  connectGmail: (workspaceId: string) => request<{ authorization_url: string }>("/integrations/gmail/connect", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  syncGmail: (mailboxId: string, workspaceId: string) => request<{ job: WorkflowJob }>(`/integrations/gmail/${mailboxId}/sync`, { method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  disconnectGmail: (mailboxId: string, workspaceId: string) => request<{ id: string; status: string }>(`/integrations/gmail/${mailboxId}/disconnect`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId }) }),
  suppressions: (workspaceId: string) => request<Suppression[]>(`/suppressions?workspace_id=${encodeURIComponent(workspaceId)}`),
  createSuppression: (workspaceId: string, email: string, reason: string) => request<Suppression>("/suppressions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ workspace_id: workspaceId, email, reason }) }),
};

export type Session = { user: { id: string; email: string }; workspaces: { id: string; name: string; role: string }[] };
export type ImportRecord = { id: string; kind: "leads" | "accounts"; filename: string; status: string; counters: Record<string, number>; mapping: Record<string, string>; error_message?: string };
export type RowError = { row_number: number; outcome: string; errors: { message: string }[] };
export type Lead = { id: string; name?: string; email?: string; title?: string; source?: string; score: number; qualification: string; next_action: string; owner_id?: string; territory?: string };
export type OutreachDraft = { id: string; lead_id: string; lead_name?: string; lead_email?: string; subject: string; body: string; sequence: { step: number; timing: string; subject: string; body: string; cta: string; facts_used: string[] }[]; rationale: Record<string, unknown>; status: string; version: number; created_at: string; reviewed_at?: string };
export type LeadDetail = { lead: Lead & { raw_data: Record<string, unknown> }; decisions: { kind: string; result: Record<string, unknown>; created_at: string }[]; ai_suggestions: { id: string; status: string; model?: string; output: Record<string, unknown>; reviewer_status: string; error_message?: string }[]; outreach_drafts: OutreachDraft[]; events: Audit[] };
export type Audit = { action: string; resource_type: string; resource_id: string; payload: Record<string, unknown>; created_at: string };
export type Company = { id: string; name?: string; domain?: string; industry?: string; employee_band?: string; score: number; qualification: string; next_action: string; owner_id?: string; profile_data: Record<string, unknown>; enrichment_data: Record<string, unknown> };
export type WorkflowJob = { id: string; type: string; name: string; status: string; phase: string; resource_type?: string; resource_id?: string; counters: Record<string, number>; progress_percent?: number | null; error_message?: string; idempotency_key: string; attempt: number; cancellation_requested: boolean; queued_at: string; started_at?: string; completed_at?: string; updated_at: string; logs: { level: string; message: string; context: Record<string, unknown>; created_at: string }[] };
export type CampaignStep = { id?: string; position: number; delay_hours: number; subject: string; body: string; facts_used: string[] };
export type Campaign = { id: string; name: string; status: string; mailbox_id?: string; audience_filter: Record<string, unknown>; timezone: string; business_hours: Record<string, unknown>; daily_limit: number; per_domain_limit: number; test_sent_at?: string; approved_at?: string; activated_at?: string; created_at: string; updated_at: string; steps: CampaignStep[]; enrollment_counts: Record<string, number>; enrollment_total: number; jobs?: WorkflowJob[]; scheduled_messages?: { id: string; status: string; step_position: number; send_at: string; error_message?: string }[] };
export type CampaignInput = { workspace_id: string; name: string; mailbox_id?: string; audience_filter: Record<string, unknown>; timezone: string; business_hours: Record<string, unknown>; daily_limit: number; per_domain_limit: number; steps: Omit<CampaignStep, "id">[] };
export type CampaignSequenceBrief = { workspace_id: string; goal: string; offer: string; target_persona: string; cta: string; proof: string; preset: "value_first" | "problem_proof" | "short_direct" };
export type CampaignSequencePayload = CampaignSequenceBrief & { steps: Omit<CampaignStep, "id">[] };
export type CampaignDeliveryPayload = { workspace_id: string; mailbox_id?: string; timezone: string; business_hours: Record<string, unknown>; daily_limit: number; per_domain_limit: number };
export type CampaignAudienceMember = { id: string; lead_id?: string; selected: boolean; readiness: string; warning?: string; exclusion_reason?: string; name?: string; email?: string; company_id?: string; score?: number };
export type CampaignWorkspace = Campaign & { audience: CampaignAudienceMember[]; audience_summary: Record<string, number>; imports: ImportRecord[]; mailbox?: Mailbox; readiness: { blockers: string[]; can_launch: boolean }; results: Record<string, number>; activity: { action: string; created_at: string; payload: Record<string, unknown> }[] };
export type Mailbox = { id: string; provider: string; email: string; status: string; scopes: string[]; last_history_id?: string; last_sync_at?: string; last_error?: string; created_at: string };
export type GmailIntegration = { configured: boolean; redirect_uri: string; connections: Mailbox[]; setup_required: string[]; smtp_imap_configured: boolean; smtp_imap_setup_required: string[] };
export type Suppression = { id: string; email: string; reason: string; created_at?: string };
export type Reply = { id: string; campaign_id?: string; lead_id?: string; gmail_thread_id?: string; subject: string; classification: string; received_at: string };
export type Analytics = { accounts: number; leads: number; qualified: number; campaign_ready: number; campaigns: number; enrolled: number; sent: number; replied: number; interested: number; bounced: number; unsubscribed: number; delivery_note: string };
