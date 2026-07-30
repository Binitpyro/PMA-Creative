# Evidence Checklist (mapped to devpost submission requirements)

Collect these continuously, not at the end. Most can't be reconstructed
after the fact.

- [ ] **GitHub repo** — this one. Share with testing@devpost.com and
      judging@hacker.fund before submitting.
- [ ] **3-minute video** — show the copilot answering a real question in
      a real Houdini session, AND show the trial-triage agent making a
      live decision (screen-record `logs/agent_decisions.jsonl` growing,
      or a small dashboard over it).
- [ ] **Written narrative (500–1000 words)** — draft after Day 20 once
      real usage exists to describe truthfully. Cover: what AI does vs.
      what you do day-to-day, jobs/economic opportunity this creates for
      others, the build story.
- [ ] **Revenue evidence** — Stripe dashboard export or bank statement +
      P&L (template linked in the challenge page). Needs at least one
      real transaction.
- [ ] **Expenses** — total marketing/customer-acquisition spend during the
      hackathon period, disclosed even if $0.
- [ ] **Product evidence** — `logs/agent_decisions.jsonl` (agent execution
      log), API usage records, screenshots of the copilot in use.
- [ ] **Customer evidence** — name, email, phone for real customers, plus
      any testimonial/feedback they give permission to share.

## Logging discipline

Every agent decision (triage, onboarding note, anything Gemini decides
autonomously) must append to `logs/agent_decisions.jsonl` via
`backend/store.py::log_agent_decision`. This file *is* your product
evidence — don't let it go stale.
