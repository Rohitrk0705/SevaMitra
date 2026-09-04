# backend/rti — Escalation clause corpus and renderers

> **Do NOT add any clause to `clauses.json` that is not verifiable against a
> public government source. Every rendered RTI cites only entries from this
> file.**

## Purpose

This module is the Escalation Agent's backbone. When the Monitor Agent
detects that a scheme application has been pending past its Citizen Charter
timeline, `renderer.py` produces two filing-ready legal documents:

1. A **Tier-1 escalation email** to the department's grievance officer,
   citing the department's own (non-statutory) Citizen Charter timeline and
   warning that a formal RTI follows in 15 days if there's no response.
2. A **Tier-2 formal RTI application** under Section 6(1) of the RTI Act,
   2005 — a statutory, legally enforceable request.

The renderer only ever inserts case-specific facts (applicant name, Aadhaar
last 4, scheme, days elapsed, department, application ID) into the two
pre-approved Jinja2 skeletons in `templates/`. It does not paraphrase
statutory text and does not add clauses beyond what's declared here.

Tamil Nadu has **no** Right to Services Act — the state relies on
departmental Citizen Charters, which are non-statutory. The corpus therefore
rests on two sources: the central RTI Act, 2005 (statutory, enforceable) and
TN departmental Citizen Charters (non-statutory, timeline source only).

## Clause corpus (`clauses.json` → `"clauses"`)

| Clause ID | Section | Title | Verification status |
|---|---|---|---|
| `RTI-2005-S6-1` | 6(1) | Application for obtaining information | verified |
| `RTI-2005-S7-1` | 7(1) | Disposal of request (30-day deadline) | verified |
| `RTI-2005-S7-6` | 7(6) | Free information on delayed response | verified |
| `RTI-2005-S4-1-b` | 4(1)(b) | Proactive disclosure obligations | verified |
| `RTI-2005-S19-1` | 19(1) | First appeal | verified |
| `RTI-2005-S20-1` | 20(1) | Penalty for delay | verified |
| `RTI-2005-S6-3` | 6(3) | Transfer of misdirected application | needs_verification |
| `RTI-2005-S7-5` | 7(5) | Fee for printed/electronic access, BPL exemption | needs_verification |

The first six entries were supplied with verbatim statutory text and are
marked `verified`. `RTI-2005-S6-3` and `RTI-2005-S7-5` were added because the
RTI application template unconditionally cites Section 6(3) (transfer
clause) and, for BPL applicants, Section 7(5) (fee exemption) — omitting
either from the corpus would mean the template cites statutory language not
backed by this file, which breaks the no-invented-language rule. Their text
was reconstructed from memory of the Act rather than sourced fresh from
`rti.gov.in`, so they're flagged `needs_verification` pending manual
sign-off, same as the Citizen Charter entries below.

## Citizen Charters (`clauses.json` → `"citizen_charters"`)

| Charter ID | Department | Default days | Verification status |
|---|---|---|---|
| `TN-AGRI-CHARTER` | Dept. of Agriculture and Farmers Welfare, TN | 60 | needs_verification |
| `TN-EDU-CHARTER` | Dept. of Higher Education, TN | 45 | needs_verification |
| `TN-SOCWEL-CHARTER` | Dept. of Social Welfare and Women Empowerment, TN | 90 | needs_verification |

## Verification checklist (manual, before demo)

For each of the following, Rohit needs to:
1. Open the department's `url_hint`.
2. Locate the published Citizen Charter PDF (or equivalent service-timeline
   document).
3. Replace `stipulated_days_default` with the real number from the
   Charter.
4. Update `verification_status` to `"verified"` once confirmed.

- [ ] `TN-AGRI-CHARTER` — https://www.tnagrisnet.tn.gov.in/
- [ ] `TN-EDU-CHARTER` — https://tnhighereducation.org/
- [ ] `TN-SOCWEL-CHARTER` — https://www.tn.gov.in/department/22

Additionally, confirm the exact statutory text of these two clauses against
the official Gazette copy at https://rti.gov.in/rti-act.pdf and flip
`verification_status` to `"verified"` once confirmed:

- [ ] `RTI-2005-S6-3` (Section 6(3) — transfer of misdirected application)
- [ ] `RTI-2005-S7-5` (Section 7(5) — fee / BPL exemption)
