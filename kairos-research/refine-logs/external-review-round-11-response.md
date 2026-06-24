# Response to GPT-5.5 External Review (Round 11)

> **Date**: 2026-06-23
> **From**: fantinli (paper author) + AI co-author
> **To**: GPT-5.5 (external reviewer)
> **Re**: Round 11 review (3/10 — Reject) of the v2 manuscript
> **Goal**: Re-calibrate the review baseline, respond point-by-point, and request a Round 12 review focused on the theoretical contribution rather than submission-readiness.

---

## 0. TL;DR

Thank you for the thorough review. We accept most of the theoretical criticisms and have already aligned with several of them in our internal v2 rewrite plan. However, **we believe the 3/10 score is calibrated against the wrong baseline**: the manuscript you reviewed is a **theory-first draft with explicit experimental placeholders** (`DATA_NEEDED`, `Expected`), not a submission candidate. The placeholders are **disclosed as placeholders by design**, not hidden as overstated results.

We are asking you to **re-review the manuscript as a theoretical contribution + experimental protocol**, not as a CCS/S&P submission. Our specific requests are listed in §4.

---

## 1. Status Clarification (please re-calibrate)

### 1.1 What this manuscript actually is right now

| Aspect | Current state | Will be ready when |
|--------|---------------|--------------------|
| Theoretical framework (chain-level paradigm + Φ metric + dual benign-data usage) | **Drafted, v2 rewrite in progress** | Now |
| Experimental protocol (datasets, baselines, metrics, ablations) | **Specified, not yet executed** | After BP3 (2026-11-30) |
| Metric validation results (benign vs random AUC, elbow curve, etc.) | **Placeholder `DATA_NEEDED`** | After BP1 (2026-07-31) |
| End-to-end results (P/R/F1, investigation cost, throughput) | **Placeholder `DATA_NEEDED`** | After BP3 (2026-11-30) |
| Cross-dataset generalization (E3 ↔ E5) | **Placeholder `DATA_NEEDED`** | After BP3 (2026-11-30) |
| Ablation studies (6 variants) | **Listed, not run** | After BP3 (2026-11-30) |

The Timeline (Memory.md §8) targets **CCS 2026 deadline ≈ 2027-01-end**, so we are roughly 7 months ahead of submission.

### 1.2 Why the abstract / intro currently contain numeric claims

You correctly flagged that abstract/intro contain `>50× cost reduction`, `>10% F1`, `144× real-time`. **These are explicit forward-looking targets, not reported results**, and the current text does not adequately mark them as such. We accept this is a real writing flaw (CRITICAL 1) and will fix it in the next revision: every numeric claim before BP1/BP3 will either be removed or prefixed with **"target:"** / **"design goal:"** explicitly.

### 1.3 The recalibration we ask for

We are not asking you to lower the bar. We are asking you to evaluate against a different, more useful question:

- **Original implicit question (gives 3/10):** "Is this manuscript ready for CCS/S&P submission today?" → No.
- **Question we want answered (Round 12):** "Assuming all flagged numeric claims are de-asserted to forward-looking targets, **and given that experiments are scheduled for the next 5 months**, is the theoretical contribution (chain-level paradigm + three-pillar causal validity argument + dual benign-data usage) sound enough to be worth executing, and what theoretical revisions are required before experiments start so that the experiments will be meaningful?"

This re-framing matters because **the value of an external review at this stage is to prevent us from running 5 months of experiments on a flawed theoretical foundation**, not to assert that experiments are missing (we know).

---

## 2. Point-by-Point Response to Theoretical Criticisms

### 2.1 CRITICAL 1 — Experimental claims overstated → **ACCEPT**

We will:
- Remove every numeric claim in abstract/intro/conclusion that is not yet measured.
- Where forward-looking targets are useful for paper structure, prefix them with **"target:"** or move them to a dedicated "Design Goals" subsection.
- Replace `Expected: …` cells in result tables with **"To be reported"** placeholders.

This is purely a writing fix, no theoretical revision. We will land it before requesting Round 12.

### 2.2 CRITICAL 2 — "kernel-observed = causality" is too strong → **PARTIALLY ACCEPT**

Our v1/v2 wording already restricts the semantic to **dependency causality** (not Pearl interventional causality). However, we agree the abstract and §1 still over-promise.

**Action plan:**
- Downgrade abstract phrasing from "kernel-observed causality" to **"kernel-mediated dependency evidence under a stated audit model"**.
- Add a new §3.1 (Threat Model and Audit Assumptions) that explicitly states:
  - Audit subsystem = Linux audit framework (CADETS) / equivalent kernel-level provenance collector
  - Recorded event types: `EVENT_EXECUTE, EVENT_READ, EVENT_WRITE, EVENT_FORK, EVENT_SENDTO, EVENT_RECVFROM, EVENT_OPEN, EVENT_CLOSE`
  - Known incompleteness: dropped records under buffer overflow, mmap/shared-mem partial coverage, container namespace boundaries, no payload, no file offset
  - PID reuse handled via `(pid, pid_creation_time)` tuple
- Add an explicit **event semantics table** (one row per edge type: source, destination, time semantic, dependency direction, observability caveat).

**Question for you (Round 12):** is this scope of audit-model declaration sufficient, or do you want a more formal threat-model paragraph in the style of CamFlow/SPADE?

### 2.3 CRITICAL 3 — process bridge "probability one" doesn't hold → **ACCEPT**

You are right that same PID ≠ dependency causality in long-lived daemons / multithreaded servers / event-loop processes. Our v1 §4.4.2 wording "probability 1, exact, not approximated" is too strong.

**Action plan:**
- Demote case-1 wording from **"exact dependency"** to **"high-confidence identity continuity"**.
- Add **conditioning factors** to case-1 φ:
  - Same TID (where audit logs include thread ID) → φ stays high.
  - Crossing exec boundary → φ resets / drops.
  - Cross-thread within same PID → apply mild temporal decay even within the same process.
  - Long-lived process (lifetime > threshold, e.g. 1 hour) → apply additional decay or require co-evidence (e.g., shared FD, parent-child ancestry).
- Add an experiment to §5 (metric validation): **false-link rate of process bridge across long-lived daemons** (sshd, cron, browser, server processes), measured on benign data.
- Update the abstract/intro language: process bridge no longer presented as "exact", but as "the strongest among three φ cases under stated continuity conditions".

### 2.4 CRITICAL 4 — Poisson interference unvalidated and oversimplified → **ACCEPT**

We agree shared-resource access in real systems is bursty/diurnal/correlated, not homogeneous Poisson. The Poisson model in v1 was meant as a **first-order survival approximation**, not a validated closed-form.

**Action plan:**
- Demote Poisson from **"closed-form probability estimate"** to **"first-order baseline hazard model, validated empirically per resource class"**.
- Add Resource-class differentiation:
  - **File**: write-only interference model + offset/append awareness
  - **Pipe**: ordered consumption, single-reader assumption
  - **Unix socket / network socket**: connection-state model (not Poisson)
  - **Shared memory**: explicit "out of model" disclosure in §7 limitations
- Add a metric-validation experiment in §5: **goodness-of-fit (Poisson vs empirical survival)** per resource class on benign DARPA E3 data.
- If goodness-of-fit fails for some classes, switch those classes to **empirical survival function** (Kaplan-Meier on benign inter-event intervals).
- Acknowledge in §7 limitations: "absence of intervening write" is **necessary but not sufficient** for dependency (offset, partial read, cached read all break sufficiency); we currently treat φ as a **monotone proxy**, not a probability.

### 2.5 CRITICAL 5 — Probability composition with arithmetic mean is wrong → **ACCEPT**

This is the most decisive theoretical point. We accept that arithmetic mean over per-link survival probabilities **is not a valid probabilistic composition**.

**Action plan:**
- Stop calling Φ a "probability" or "probabilistic estimator" anywhere in the paper.
- Switch chain-level aggregation from **arithmetic mean** to **mean log-φ**:

\[
  \log \Phi(C) = \frac{1}{n-1} \sum_{i} \log \phi(e_i, e_{i+1})
\]

This:
- Makes a single broken link (φ=0 → log φ = −∞) **dominate** the chain score (no more masking).
- Allows a **smoothing floor** `φ_min > 0` for missing-event robustness.
- Has a defensible interpretation: "mean log-likelihood of pairwise dependency under a calibrated model".
- Does not claim to be a probability estimator, only a coherence score on log scale.

For Φ_bw (with branch penalty):
- Already aligned with our v2 decision **D4** (Branch-Weighted Coherence demoted to deployment-time refinement, not part of causal coherence definition itself).
- We will additionally rename it explicitly as **deployment prior**, never "core metric", in abstract/intro/contribution.

### 2.6 MAJOR 1 — "zero attack-side prior" overstated → **ACCEPT**

**Action plan:**
- Change abstract/intro phrasing from **"zero attack-side prior"** to **"no attack labels and no attack-pattern templates"**.
- Disclose path-sensitivity feature list (`/etc/passwd`, `authorized_keys`, `/root/`, etc.) as a **deployment-tunable security prior** (Node Profiler features), not as part of the core method.
- Add an ablation: **remove path-sensitivity features + branch penalty** → measure performance delta. This isolates how much of our score is "structural causal coherence" vs "deployment prior".

### 2.7 MAJOR 2 — Pipeline still seed-bound, contradicts criticism of post-hoc methods → **ACCEPT (with framing change)**

You're right that we cannot claim to escape upstream-detector dependence. Our true contribution is **what we do with seeds**, not eliminating them.

**Action plan:**
- Reframe in §1 / §3 / §7: We do **not** eliminate the upstream detector; we **amplify edge-level alerts into chain-level evidence** by extracting causally-coherent neighborhoods around each seed. Our value over SLOT/CAGE/EdgeTrace is **before-extraction quality measurement** (Φ guides the extraction itself), not "no upstream needed".
- Add experiments:
  - **Oracle-seed**: replace TGN seeds with ground-truth attack edges → upper bound of our extractor + sequence model.
  - **Seed threshold sensitivity**: 90th / 95th / 97th / 99th / adaptive percentile.
  - **Seed recall / seed precision / chain recall** decomposition reported separately.
- Explicitly state in §7 limitations: pipeline recall ≤ seed-scorer recall.

### 2.8 MAJOR 3 — Calibration protocol has circularity → **ACCEPT**

The current 4-step protocol description has an algorithmic ambiguity (which params are fixed, which vary, in what order). We will rewrite it as **deterministic pseudocode**.

**Action plan:**
- Rewrite §4.4.3 as a single algorithm box with:
  - Inputs: benign corpus, K (number of process-lifecycle seeds), parameter grids
  - Step 1: fix loose `(α₀, β₀, d_max,0)`, extract K chains
  - Step 2: vary d_max only, holding `(α₀, β₀)` fixed → find d_max* via inflection
  - Step 3: fix d_max*, vary β only → find β* via inflection
  - Step 4: fix `(d_max*, β*)`, validate α* on held-out benign chains
- Report stability: bootstrap CI for `(d_max*, β*)` across K ∈ {100, 500, 1000}, days ∈ {benign-day-1, benign-day-2}, random seeds ∈ {3 seeds}.
- Add sensitivity analysis: ± 20% deviation from inflection → performance delta on held-out attacks.
- Remove the phrase "any knee heuristic suffices".

### 2.9 MAJOR 4 — Procedural symmetry incomplete (training anchors ≠ online seeds) → **PARTIALLY ACCEPT**

You're right that "uniform random across event types" (training) ≠ "TGN high-loss percentile" (online). However, we deliberately chose random training anchors to **avoid teaching the sequence model to ignore TGN-flagged regions** (which would happen if training anchors are also high-loss seeds — the model would learn benign high-loss patterns and refuse to flag them at test time).

**Action plan (mixture training):**
- Adopt **mixture training**: 50% random anchors + 50% benign high-loss anchors (TGN-scored on benign days).
- Report three configurations in ablation:
  1. Random-only (current v2)
  2. Seed-matched only (your suggestion)
  3. Mixture (proposed compromise)
- Document the trade-off: random covers benign distribution broadly; seed-matched matches online covariate distribution; mixture balances.
- Same mixture for eCDF calibration corpus.

**Question for you (Round 12):** does the mixture compromise address the symmetry concern, or do you still consider it weaker than full seed-matched?

### 2.10 MAJOR 5 — Baseline fairness and chain-level matching metric undefined → **ACCEPT**

**Action plan:**
- **Two baseline groups:**
  1. **Controlled-segmentation group**: same sequence model (our autoregressive Transformer), differ only in segmentation strategy (window vs node-level vs naive BFS vs our Φ-guided extraction). Isolates segmentation contribution.
  2. **Original-system group**: KAIROS, MAGIC, PROGRAPHER, EagleEye, SLOT, CAGE, GET-AID, EdgeTrace each evaluated using their **published implementations** (or faithful reimplementation), with chain-level outputs derived per their original protocols.
- **Chain-level matching metric** (new §6.X subsection):
  - Primary: **edge-IoU vs ground-truth attack chain** (bidirectional set match)
  - Secondary: **node recall** (does chain include critical attack nodes?)
  - Tertiary: **temporal-overlap** of chain timespan vs attack window
  - Investigation cost: **#nodes/edges analyst must inspect to recover full attack** (Holmes-style)
  - Stopping criterion: top-K chains by score, K reported as 10 / 50 / 100
- For node-level / window-level baselines (KAIROS, MAGIC), define **synthetic chain construction**: for each flagged node/window, construct chain via 1-hop / 2-hop BFS from flagged element; report under same metric.

### 2.11 MAJOR 6 — Self-containedness → **ACCEPT (already partially v2)**

Reproducibility subsection will be added covering:
- Dataset preprocessing (DARPA CDM JSON → PostgreSQL → graph format)
- Audit event normalization
- Graph construction (node-feature hashing, edge encoding)
- Seed scorer training (TGN hyperparams, training days)
- Chain extraction parameters (d_max*, β*, α*, branch penalty λ)
- Hardware/software environment
- Random seeds (we will pre-register 3 seeds)
- Code release plan (BP3 / submission)

Architecture figure, result tables, CI bands → blocked on actual experiments (BP1–BP3).

### 2.12 MINOR — Typos, dimension arithmetic, missing citations → **ACCEPT, fix in next pass**

- bib typo `eagleye2024 → eagleeye2024`: fix immediately
- Placeholder bib entries (`EdgeTrace Authors` etc.): replace with real author names from published papers
- SLEUTH: add citation (Hossain et al., USENIX Security 2017)
- **75-dim feature arithmetic**: we will recheck. Current breakdown:
  - src_node 24 (node2higvec 16 + node_type 3 + IDF 1 + sensitivity 1 + deg_anomaly 1 + community 1 + bridge_cent 1) ✓
  - edge 20: text says one-hot 7 + time 8 + d_embed 4 + bridge_flag 3 + was_seed 1 = **23**, not 20 ❌
  - dst_node 24 ✓
  - structure 3 ✓
  - **24+23+24+3 = 74**, not 75
  - **Likely fix**: bridge_flag should be 1-dim (boolean) not 3-dim, then edge=21, total=72 — we will reconcile against code
- Missing references to add: SLEUTH, NoDoze, PrioTracker, Winnower, DEPIMPACT, SPADE, CamFlow, LPM, Hi-Fi, BackTracker, Taser, OpTC eval papers

---

## 3. Items Where We Disagree (or want clarification)

### 3.1 The "experiments missing" → 3/10 score

We respectfully disagree that "experiments missing" alone justifies 3/10. **The manuscript explicitly marks all unfinished results as `DATA_NEEDED` / `Expected`**, and the timeline (Memory.md §8, BP1–BP4) is publicly stated. A score that conflates "theory + experiment plan" with "submission" loses signal about the theoretical contribution itself.

**Concrete request**: in Round 12, please provide **two scores**:
- **Score A**: theoretical contribution + experimental protocol, conditional on the rewrites in §2 above being executed.
- **Score B**: submission readiness as of the manuscript reviewed (3/10 is reasonable here).

### 3.2 Process lifecycle ≠ causal closure (your §6 wording)

You wrote: "process lifecycle ≠ causal closure. It is identity closure, not all events depend on each other." We agree completely. Our v1 §4.4.3 wording **"process lifecycles as natural causal units"** is too strong.

**Action plan (already integrated into 2.3 above):**
- Rewrite as **"process lifecycles as natural identity-continuity scopes that bound the maximum reachable causal horizon"**.
- The calibration uses lifecycles to **upper-bound d_max**, not to claim every intra-lifecycle event pair is causally linked.

### 3.3 Whether arithmetic mean → log-mean is sufficient

You suggested log-likelihood form. We propose to go with mean-log (§2.5 above) rather than sum-log because chains have variable length (n=3 to n=64) and a sum would create a length bias. Please confirm whether mean-log addresses your concern, or whether you require length-normalized sum-log + a separate length term.

---

## 4. Specific Asks for Round 12

1. **Re-review with the dual-score framing** (§3.1): theoretical-contribution score + submission-readiness score, separately.
2. **Confirm the theoretical revision plan in §2** is sufficient. Specifically:
   - Is the threat-model + event-semantics table addition (§2.2) enough?
   - Is mean-log Φ + smoothing floor (§2.5) a defensible probabilistic interpretation, or should we abandon probabilistic language entirely?
   - Is mixture training (§2.9) an acceptable resolution of procedural symmetry?
3. **Answer the open questions** marked "**Question for you (Round 12)**" in §2.2, §2.9, §3.3.
4. **Identify any remaining theoretical gaps** that we have not addressed in §2.
5. **Do not re-criticize the missing experiments** unless you find a theoretical claim that can only be settled by an experiment we did not plan.

---

## 5. What Happens After Round 12

If Round 12 yields a theoretical-contribution score ≥ 7/10 with no fundamental theoretical gap, we proceed to:
- Execute the v2 + Round 12 rewrites in the manuscript.
- Run BP1 metric-validation experiments (2026-07-31).
- Return for Round 13 with BP1 results.

If Round 12 still identifies fundamental theoretical gaps, we will revise the framework before running any experiments.

---

## 6. Appendix: Cross-reference to v2 Rewrite Plan

The following Round-11 criticisms were already independently identified in our v2 rewrite (PAPER_REWRITE_PLAN.md):

| Round 11 critique | v2 decision | Status |
|-------------------|-------------|--------|
| C5 (Φ_bw not a probability) | D4 (BW demoted to deployment-time refinement) | Aligned |
| C2 (causality language too strong) | D3 (dependency causality in abstract) | Aligned, will strengthen further |
| Cross-platform overclaim | D5 (cross-dataset, not cross-platform) | Aligned |
| Elbow over-emphasized | D6 (elbow demoted to implementation note) | Aligned |
| Contribution list misframed | D7 (contributions reordered around paradigm + dual usage) | Aligned |

This convergence increases our confidence that the v2 direction is correct; Round 11's main contribution to us is **deepening the theoretical rigor of the φ definition (C3, C4, C5), procedural symmetry of training (M4), and pipeline recall framing (M2)** — none of which were on our v2 radar.

---

*End of Round 11 response. Awaiting Round 12 review with the dual-score framing requested in §4.*
