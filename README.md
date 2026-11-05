# SignalFlow Outbound Workspace Demo

An intentionally small, in-memory outbound send lane for SDRs and BDRs. It presents a prioritized prospect queue, a personalized first-touch composer, basic send-readiness checks, and a real Gmail SMTP handoff.

## Run locally

```bash
python -m pip install -r requirements.txt
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`.

## Sending configuration

The API only sends when all of the following are configured:

```bash
export SHOWCASE_ADMIN_TOKEN='use-a-long-random-value'
export SMTP_USERNAME='sender@your-domain.com'
export SMTP_PASSWORD='your-app-password'
export SMTP_DRY_RUN='true' # optional: records activity without sending
```

Optional SMTP settings: `SMTP_HOST` (defaults to `smtp.gmail.com`), `SMTP_PORT` (defaults to `587`), and `SMTP_USE_SSL=true`.

## Product boundary

This is a demo send lane, not a production sales-engagement platform. Sample prospect signals, fit scores, sequence steps, and metrics live in the browser. Campaigns and activity are in memory and disappear on restart. It does not yet have durable storage, Gmail inbox sync, unsubscribe management, CRM synchronization, enrichment, send scheduling, per-recipient personalization rendering, tracking, or deliverability controls.
