# Ideas: Claims Coverage Reasoner

## High level requirements
- Develop an POC level application for AWS AI Agent hackathon demo that can run with steamlit and python modules.
- The app should be run locally first, with feasibility to deloy to AWS hackathon judge for review.
- The App should contain agentic and innovation ideas.
- The App should use AWS resources as much as needed.
- No database is needed for this POC, data file should be uploaded to S3.



## Agents to be included in the App:
1. Agents
Evidence Curator – gathers & normalizes facts from FNOL, photos, invoices, and notes.
Policy Interpreter – maps facts to specific policy clauses (coverage, exclusions, conditions) with citations.
Compliance/Fairness Reviewer – adversarially challenges the Interpreter; checks disclosures & fraud flags.
Supervisor - to manage turn-taking, round limits, and stop conditions.

2. Stop rule
If the Interpreter reaches a coverage position and the Reviewer has no blocking objections (or runs out of objection budget), the case closes—no further review. You’re right: if the fact set clearly fits the policy, the loop ends quickly.

Public sample data you can use today
Forms / FNOL / Proof of Loss
ACORD Property Loss Notice specimen (widely used for FNOL). Good for parsing policy #, loss time, cause, etc. 

Sworn Proof of Loss (multiple specimen versions for property). Use to test numeric fields and statements. 

Consumer sample letters (post-loss notices, etc.)—great for realistic free-form text the Curator must summarize. 

Invoices / Estimates
Auto repair invoice & estimate templates (PDF/Word/Sheets). Use them to extract line items, parts, labor, taxes. 

Images for evidence
Vehicle damage datasets (thousands of labeled photos) for “new vs. pre-existing damage” challenges. 

Water / flood damage image sets for property claims (walls, ceilings, flood scenes).

Actual policy text (specimen forms)
Homeowners HO-3 specimen policies (ISO-style). Use for “sudden & accidental discharge” vs. long-term seepage, wear & tear, etc. 

Personal Auto Policy (PP 00 01 09 18) specimen (collision/comp). Great for coverage vs. exclusions and appraisal clause tests. 

Adjuster notes / documentation norms
What should be in adjuster notes (structure, diary, contacts)—useful to synthesize realistic “loss notes.” 

## End-to-end flow (non-linear)
Curator ingests:
FNOL/Proof of Loss PDFs → structured fields (policy #, DoL, peril, location).
Photos (EXIF if available), invoices/estimates line items, and free-text “loss notes.”
Produces a fact map (claims, evidence pointer, confidence).

Interpreter cites policy clauses (e.g., HO-3 Coverage A, exclusions for wear-and-tear/long-term seepage; PAP Physical Damage, appraisal clause) and drafts coverage position with clause references. 

Reviewer challenges: missing facts, misapplied clauses, potential fraud, unfair language; requests new evidence from Curator (e.g., “need invoice photo to confirm pre-loss condition”), or asks Interpreter to re-analyze.

Loop until no blocking flags or max rounds. 

Output bundle: coverage decision + cited clauses + objection log + remaining questions.

## Three concrete scenarios (with downloadable artifacts)
(A) Burst pipe vs. long-term seepage (HO-3)
Artifacts:
ACORD Property Loss Notice (FNOL) with “kitchen ceiling leak,” time of loss supplied. 
FLDFS
Photos of wet drywall/ceiling (use water-damage/flood image sets). 

Contractor estimate PDF (line items: cut-out, dry-out, replace drywall, paint).
HO-3 specimen policy (coverage vs. exclusions for constant or repeated seepage, wear & tear). 

A2A debate:
Interpreter: “Covered—sudden & accidental discharge from plumbing.” (cites HO-3 language) 

Reviewer: “Photos show prior staining—could be long-term seepage (excluded). Curator, fetch earlier ceiling photos or inspection notes.” 

Curator: Adds pre-loss realtor photos / inspection snippet; updates fact map.
Interpreter: Revises: “Partial coverage for acute burst; deny pre-existing damage; apply mold sublimit if any.” (with clause cites) 

Stop: No further objections → issue decision + rationale.

(B) Collision with suspected pre-existing damage (PAP)
Artifacts:
FNOL with date/time, intersection. 
FLDFS
Photos from vehicle damage dataset (damaged bumper + unrelated old scrape photo). 
Body-shop estimate template + invoice. 
PAP PP 00 01 09 18 specimen (collision coverage; appraisal clause; other insurance provisions). 

A2A debate:
Interpreter: “Collision damage to rear bumper covered under Collision; depreciation rules apply.” (cites PP 00 01) 

Reviewer: “Invoice includes repaint of front quarter panel—not in the accident description. Curator, verify timestamp/EXIF & adjuster notes.”

Curator: Confirms EXIF dates differ; flags line item as pre-existing.

Interpreter: Approve covered repairs; deny unrelated items; mention appraisal clause path if disputed. 

(C) Catastrophe wind claim with contents schedule dispute (HO-3)
Artifacts:
Post-loss letter + Proof of Loss specimen; contents schedule worksheet (items, age, ACV). 

Wind-damaged property photos from flood/wind datasets (use for visual corroboration). 

HO-3 specimen policy (Coverage C, special limits, ACV/RCV conditions). 

A2A debate:
Interpreter: “Coverage C applies; special limit on jewelry; apply ACV unless RCV conditions met.” (cites HO-3) 

Reviewer: “Two high-value items lack purchase docs. Curator, request alternate proof (bank stmt, photos).”

Curator: Adds alternative proofs; updates fact confidence.

Interpreter: Accept some items at sublimit; deny those failing conditions; explain appeal path.

### What each agent must “know” and the tools to give them
Evidence Curator
Tools: PDF form parser (FNOL/Proof of Loss), image analyzer (basic CV or external tagger), invoice OCR, EXIF reader.
Heuristics: Build a fact map: claim → evidence pointers → confidence. If Reviewer calls “missing proof,” Curator either (a) fetches another artifact or (b) marks a residual uncertainty.
Policy Interpreter
Tools: RAG over HO-3 and PAP specimens (plus endorsements you add later). Anchor every statement with section/page. 

Output: Coverage position + citations + what would change the decision (explicitly list missing facts).

Compliance/Fairness Reviewer
Tools: Check for promissory language, missing disclosures, and scope creep in invoices; run light fraud hygiene (timestamp/EXIF mismatch, duplicate photos).
Playbook: Objection types = “Missing Evidence,” “Misapplied Clause,” “Inconsistent Narrative,” “Invoice Scope Mismatch,” “Potential Fraud Signal.”
Supervisor (if you include one)
Manages rounds (e.g., max 3), who speaks next, and stop conditions (“no blocking flags” or “objection budget exhausted”).
Deliverables produced by the pod
Decision memo (Pay / Partial / Deny) with clause citations (HO-3/PAP pages/sections). 

Objection log (each Reviewer challenge, resolution, and remaining residual risk).
Evidence bundle (links to FNOL fields, invoice rows, and photos used).
What would change the decision (explicit missing proofs).

## Minimal test plan (so you can demo quickly)
Case 1 (should auto-close fast):
FNOL: “Pipe burst 10/10/2025 19:30, kitchen.”
Photos: fresh wet drywall, no prior staining.
Estimate: cut-out + dry-out + restore.
Expected: Interpreter: Covered; Reviewer: no blocking flags → 1 pass, done. (Cite HO-3 “sudden & accidental discharge”.) 

Case 2 (forces debate):
Same as Case 1, but include one old photo showing prior stain and an estimate line for unrelated room.
Expected: Reviewer flags “seepage exclusion?” + “scope mismatch”; Curator fetches proof; Interpreter partially approves, denies unrelated work, documents rationale with citations. 

Case 3 (auto collision, mixed scope):
FNOL + rear-end photos + invoice that bundles front-panel repaint.
Expected: Reviewer requests EXIF/time; Curator confirms mismatch; Interpreter approves collision items, denies unrelated, references appraisal clause if disputed.

Implementation nits (Bedrock + AgentCore)
Create a policy RAG index with the HO-3 and PP 00 01 specimen PDFs above; store page anchors so the Interpreter can cite page/section. 

Normalize artifacts to a common evidence schema (source, extracted fields, confidence, hash, timestamp, EXIF).
Encode Reviewer objections with a severity label (blocking / non-blocking) + required action (ask Curator vs. ask Interpreter).
Stop when no blocking or max rounds = 3; expose a “request human review” outcome if residual uncertainty > threshold.

## What the judge sees 
Streamlit one-page app (fastest to demo)
Left: Upload panel for FNOL/Proof of Loss, photos, invoices/estimates.
Middle: Conversation timeline between the three agents (Curator ↔ Interpreter ↔ Reviewer) showing who challenged what and why.
Right: Decision card (Pay / Partial / Deny), policy citations, Objection Log, and Evidence Map (which files/lines the decision relied on).
Why Streamlit? You get a working web UI quickly with minimal glue; perfect for a hackathon demo.

## User flow (end-to-end)
Start a case → user uploads:
FNOL/Proof of Loss PDF (or pastes text)
Photos (vehicle/property damage)
Invoices/estimates (PDF/PNG)
Click “Run Reasoner” → the Supervisor invokes the agents:
Evidence Curator parses forms & invoices and tags photos.
Invoices/receipts parsed by Amazon Textract – AnalyzeExpense to extract totals, vendors, line items (part, labor, taxes). 

Damage photos labeled by Amazon Rekognition DetectLabels (and optionally Custom Labels if we pretrain a “pre-existing rust/stain” class).

Policy Interpreter runs retrieval over specimen policy PDFs (HO-3, PAP). We index those with Knowledge Bases for Amazon Bedrock on OpenSearch Serverless so the agent can cite clause/page. 

Compliance/Fairness Reviewer challenges unsupported claims (e.g., seepage vs. sudden burst, invoice scope mismatch) and can bounce control back to Curator or Interpreter.
Orchestration uses Amazon Bedrock Multi-Agent Collaboration (Supervisor + 2–4 collaborators) and AgentCore patterns so agents can talk to each other, not just run in a pipeline. 

See the debate → The timeline shows Reviewer objections (“invoice includes front-panel repaint; accident says rear bumper”) and how Curator/Interpreter resolved them.
Result → Decision card + clause citations + Objection Log + Evidence Map. You can download a decision memo (PDF/Markdown).

(Optional) The judge can toggle Case 1/2/3 sample scenarios to reproduce deterministic outcomes.

## Data flow & components (holistic view)
Frontend
Streamlit uploads → directly to Amazon S3 (pre-signed URL).
UI for agent turns and renders the A2A conversation and artifacts.

Backend
Supervisor: Bedrock multi-agent collab supervisor coordinates turns and stop rules (max N rounds, or “no blocking objections”). 

## Evidence Curator tools
Textract AnalyzeExpense for invoices/receipts → JSON line items, totals, taxes. 

Rekognition DetectLabels for photo tags (e.g., dent, scratch, water stain, pipe, ceiling). Custom Labels optional for domain-specific cues like “old stain.”
(Simple EXIF check is done in code; we don’t need a managed service for that.)

Policy Interpreter tools
Knowledge Bases for Bedrock connected to OpenSearch Serverless (or your own vector store) to retrieve HO-3, PAP specimen policies with page/section anchors for citations. 

Compliance/Fairness Reviewer
Lightweight rule checks (promissory language, missing disclosures, scope mismatch between estimate and FNOL narrative).

Agent runtime
Bedrock agents + AgentCore sample scaffolding (GitHub) for A2A messaging, tool calls, and traces. 

Storage & state
S3: raw artifacts (PDFs, images), the generated memo, and per-case JSON transcripts.
DynamoDB: case metadata & agent turn logs (fast, cheap, serverless).
OpenSearch Serverless: vector index used by Knowledge Bases for policy RAG (private collection; allow Bedrock via network policy). 

## Demo datasets & scenarios (bundled in the app)
We’ll include three buttons in the UI to auto-load sample artifacts:
Case A — “Burst pipe” (should auto-close)
FNOL: single acute event (date/time), photos show clean fresh wet drywall, estimate matches scope.
Expected: Interpreter cites “sudden & accidental discharge”; Reviewer has no blocking flags → stop in 1 pass. (Agents still run, but the debate ends immediately per stop rule.)
Case B — “Seepage suspicion” (forces debate)
Same as A + one older photo with visible stain; estimate includes an unrelated room.
Reviewer raises “long-term seepage?” and “scope mismatch”; Curator proves timestamps; Interpreter issues partial coverage with clause citations and denies unrelated items.
Case C — “Rear-end collision w/ unrelated repaint”
FNOL and rear bumper photos; invoice bundles front panel repaint.
Reviewer requests EXIF; Curator surfaces mismatch; Interpreter approves collision items, denies unrelated, references appraisal clause for disputes.
(All three use public specimen policies in the RAG index and generic sample invoices/photos parsed by Textract and Rekognition.) 

## Why this is “true multi-agent”, not just a pipeline
We use Bedrock Multi-Agent Collaboration with a Supervisor that can send turns to Curator or Interpreter based on Reviewer challenges, including loopbacks and early stops. You can associate multiple collaborators with a supervisor and deploy/invoke as one agent team. 

AgentCore sample repos provide runnable scaffolding and show how to plug tools and traces into the agent team so they exchange messages (A2A) rather than just run sequentially. 

Judge checklist (what we’ll point out in the demo)
Uploads → Evidence Map: show how Textract extracted invoice totals/lines and how Rekognition labeled images (“bumper”, “scratch”, “water stain”).

Citations: Interpreter’s decision includes policy clause/page pulled via Knowledge Bases on OpenSearch Serverless. 

A2A Objection Log: Reviewer’s blocking vs. non-blocking objections, with loopbacks.
Stop rule: Case A ends in one round because Reviewer has no blocking flags—exactly the behavior you asked to confirm.

Downloadable memo with sources, timestamps, and what evidence would change the decision.
Security & data handling (brief)

Artifacts in S3 with server-side encryption; case metadata in DynamoDB; vector index in OpenSearch Serverless with private collection + Bedrock network policy.

