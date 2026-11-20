# Deployment

Public demo: [https://regnav-onlvzgx6fq-ts.a.run.app](https://regnav-onlvzgx6fq-ts.a.run.app)

Not legal advice. The service is a portfolio demonstration. Evaluation numbers elsewhere in this repo stay **provisional**.

## What is running

Cloud Run in `australia-southeast1`, 2 vCPU and 4 GiB, scale-to-zero (`min-instances` 0, `max-instances` 1). The container listens on the port Cloud Run sets. The image bakes the corpus and the Chroma index (`idx-2185d086e9c4`) and starts `configs/prod.yaml`.

That config calls Groq model `qwen/qwen3.8-27b` only. There is no local Ollama fallback on the demo. If Groq is unavailable the app abstains. MLflow is not deployed.

A cold start is about **1.5 minutes** (image pull and process start). The first answer after that is slower again, because the embedding model and the cross-encoder load on the first question. Later questions in the same instance are faster. The free tier sleeps when idle, so the next visitor can pay the cold start again.

## Guardrails and logging

The demo turns these on with `REGNAV_PUBLIC_DEMO=1`. Local `docker compose` leaves them off.

* Banner: not legal advice; do not enter personal, customer, or confidential information; questions are logged to Langfuse.
* Session cap of 20 questions and a 500-character limit.
* The retrieval config is locked. Visitors cannot switch to the local model.
* No password is set. An optional password gate stays off unless a password is configured.
* Langfuse traces are tagged `env:prod`, with the config name and index version. A tracing failure does not stop an answer.

## Secrets and deploy

Groq and Langfuse keys live in Secret Manager. They are not in git, the image, or the workflow logs.

Deploy is a manual GitHub Action, **Deploy Cloud Run** (`.github/workflows/deploy-cloudrun.yml`). It does not run on push. GitHub authenticates to Google with OIDC (Workload Identity Federation), so there is no JSON key. After CI is green on `main`:

1. Actions → **Deploy Cloud Run** → **Run workflow**.
2. Leave the ref empty to build the commit selected in that screen.

Rollback is the same workflow with the ref set to an older full commit SHA. That rebuilds and deploys that commit. It does not change retrieval or generation thresholds.

A billing budget alert is set at **A$30**.

## Known limits

* Cold start about 1.5 minutes, then a slower first answer.
* Groq is the free tier of `qwen/qwen3.8-27b` only. A limit or outage becomes a safe abstention. One full answer can use the per-minute token budget. The 20-question session cap does not cap the daily token quota.
* APP 11 statutory text is not in the index. A question about APP 11 can only be answered from guidance that mentions it, and that guidance stays under Regulator expects.
* The corpus is a November 2026 snapshot. It is not monitored for amendments.
* Eval metrics in `docs/results.md` are provisional. The live smoke check is not an evaluation.
