# Round 1 Review

> Note: Codex MCP (GPT-5.5) unavailable. Self-review based on novelty check findings and CCF-A venue standards.

## Dimension Scores

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Problem Fidelity | 8 | 15% | 1.20 |
| Method Specificity | 6 | 25% | 1.50 |
| Contribution Quality | 5 | 25% | 1.25 |
| Frontier Leverage | 6 | 15% | 0.90 |
| Feasibility | 7 | 10% | 0.70 |
| Validation Focus | 6 | 5% | 0.30 |
| Venue Readiness | 5 | 5% | 0.25 |
| **OVERALL** | **6.1** | — | **6.10** |

## Verdict: REVISE

---

## Dimension-Level Critique

### 1. Problem Fidelity (8/10) — GOOD

The proposal stays focused on the original bottleneck: coarse detection granularity → fine-grained attack path detection. The anchor is well-defined and non-goals are clear.

**Weakness**: The framing "causal chain as detection unit" vs "post-hoc chain reconstruction" needs sharper argumentation. SPARSE already has "Suspicious Flow Paths" as a first-class analysis object. EdgeTrace explicitly calls its output "causal paths." The distinction between "detection unit" and "reconstruction target" may be seen as semantic rather than substantive by reviewers.

**Fix**: Ground the distinction in a concrete technical difference — e.g., "our method propagates detection signals along causal edges during inference, while post-hoc methods can only connect already-detected nodes." Or reframe around the *joint optimization* of detection and chain extraction vs their sequential execution.

**Priority**: IMPORTANT

---

### 2. Method Specificity (6/10) — NEEDS WORK

The Transformer design is well-specified (60-dim features, 3 layers, architecture). But the Chain Extractor — arguably the most important novel component — is described only as "seed → fwd/bwd causal trace → branch split." 

**Specific gaps**:
- No pseudocode for the tracing algorithm
- No specification of trace depth, branching factor, or termination conditions
- No handling of provenance graph cycles (provenance graphs are DAGs in theory but may contain cycles in practice due to logging artifacts)
- No strategy for when two chains overlap significantly (merge? keep separate?)
- No specification of how "Top-K seeds" is determined (K=? fixed or adaptive?)
- Training data construction says "extract causal chains using Chain Extractor" but the Chain Extractor uses TGN seeds (circular? clarify)

**Fix**: Provide pseudocode for the Chain Extractor. Define explicit parameters (max_depth, max_branches, termination conditions). Clarify the training-inference distinction. 

**Priority**: CRITICAL

---

### 3. Contribution Quality (5/10) — MAJOR CONCERN

This is the most worrying dimension. The field has moved extremely fast:

- **Sentient (AAAI 2026)** already proposes Graph Transformer + behavioral logic analysis on provenance graphs, achieving 44% FPR reduction over 6 SOTA methods
- **EagleEye (eCrime 2024)** already shows Transformer on provenance event sequences with self-attention-based interpretability
- **GET-AID (ESORICS 2025)** already proposes two-stage attention for APT detection on provenance
- **SPARSE (2024)** already defines "Suspicious Flow Paths" as the analysis object

The proposal's dominant contribution ("causal chain as detection unit") is too close to SPARSE's Suspicious Flow Paths and EdgeTrace's causal path inference. The Node Profiler supporting contribution is feature engineering — insufficient for CCF-A.

**The hard truth**: As currently framed, this paper would likely be rejected from CCS/ S&P / USENIX Security with reviews saying "incremental over EagleEye + SPARSE."

**Fix — three options**:

*Option A (Recommended)*: **Make the Chain Extractor algorithm the dominant contribution.** Design a novel causal tracing algorithm grounded in causal inference theory (e.g., using Pearl's do-calculus or counterfactual reasoning). This is a genuine algorithmic contribution that no existing provenance paper has. Then the Transformer becomes the supporting component that validates the quality of the extracted chains.

*Option B*: **Pivot to "temporal causal chain modeling"** — emphasize that TGN temporal memory enables chain extraction that captures node state evolution over time, which static/snapshot methods (EagleEye, Sentient, GET-AID, SPARSE) fundamentally cannot do. The contribution becomes "temporal awareness in causal chain extraction."

*Option C*: **Accept a lower venue.** Target ESORICS, RAID, ACSAC, or DIMVA where the bar for novelty is lower. But the user explicitly wants CCF-A.

**Priority**: CRITICAL

---

### 4. Frontier Leverage (6/10) — ADEQUATE BUT NOT STRONG

The small Transformer is appropriate for the task scale. Not forcing LLMs is good. But Sentient uses Graph Transformer + Mamba-2 + Intent Analysis Module — a more technically sophisticated stack. The proposal's "3-layer Transformer" feels technically thin in comparison.

**Fix**: If Option A from above is chosen, the frontier leverage question shifts from "is the Transformer sophisticated enough?" to "is the causal tracing algorithm theoretically grounded?" — which is a better position. Alternatively, consider whether TGN's temporal memory + causal chain + Transformer forms a more elegant combination than Sentient's Graph Transformer + Mamba-2 + IAM stack. Elegance can be a selling point.

**Priority**: MINOR (resolved if Contribution Quality is fixed)

---

### 5. Feasibility (7/10) — GOOD

The plan is realistic. ~9 GPU-hours, existing datasets, existing KAIROS checkpoint. The compute and data assumptions are honest.

**Weakness**: Positive sample scarcity. "~50-200 chains" from one attack day is dangerously small for training even a 1.5M-param Transformer. The proposed augmentation (sub-chain sampling, node generalization) helps but may not be enough. 

**Fix**: Add a specific data augmentation strategy with quantitative estimates. E.g., "Each 10-step attack chain yields C(10,3)+C(10,5)+C(10,7) ≈ 300 sub-chains. With 50 attack chains and type-level generalization, we expect ~5000 positive training samples." Also consider using StreamSpot as an additional source of positive chains.

**Priority**: IMPORTANT

---

### 6. Validation Focus (6/10) — NEEDS STRENGTHENING

The two-claim structure is clean. But:

- Cross-dataset validation is "secondary" but essential for CCF-A. At minimum, StreamSpot or OpTC results must be in the main paper.
- The ablation "causal chain vs window vs random walk" is the critical experiment but the expected ">10% absolute improvement" may be unrealistic. EagleEye already gets ~89% detection. What's the ceiling?
- Investigation cost reduction vs KAIROS is a good practical metric, but needs a clear definition.

**Fix**: Make cross-dataset validation a main-paper experiment. Define "investigation cost" formally (e.g., number of edges an analyst must examine to find all attack edges).

**Priority**: IMPORTANT

---

### 7. Venue Readiness (5/10) — BELOW BAR

The "Transformer on provenance" wave has crested. Sentient at AAAI 2026, GET-AID at ESORICS 2025, EagleEye at eCrime 2024, FALCON at UAI 2025, PanThreat, LogShield — this space is crowded. A paper that adds "causal chain extraction" as a preprocessing step to a standard Transformer risks being seen as incremental.

**Fix**: The venue readiness depends entirely on fixing Contribution Quality. If the Chain Extractor becomes a theoretically-grounded algorithmic contribution (Option A), the paper becomes about "how to extract causally-meaningful chains from temporal provenance graphs" rather than "yet another Transformer on provenance." This reframes the paper from application to algorithm, which CCF-A venues prefer.

**Priority**: CRITICAL (resolved if Contribution Quality is fixed)

---

## Simplification Opportunities

1. **Remove Path Assembler as a separate module.** Chain merging can be a simple post-processing rule (shared nodes + temporal proximity) without being a named module. This reduces the perceived complexity from 5-phase to 4-phase pipeline.

2. **Merge Node Profiler features into a single "node anomaly prior" score** instead of 5 separate dimensions. This simplifies the feature space and makes the ablation cleaner (one binary ablation instead of 5 sub-ablations).

3. **Drop the "optional supporting contribution" framing for Node Profiler.** Either it's a real contribution (prove it) or it's just feature engineering (don't claim it). A weak supporting contribution hurts more than it helps.

## Modernization Opportunities

1. **Ground Chain Extractor in causal inference theory.** Use Pearl's structural causal model (SCM) framework to formally define what a "causal chain" means in a provenance graph. This elevates the contribution from engineering to science. This is a substantive modernization, not a buzzword.

2. **Consider whether TGN temporal memory can be replaced or augmented by a simpler temporal encoding.** TGN is complex. If a simple time-delta feature achieves similar results, the method becomes simpler and more reproducible.

## Drift Warning: NONE

The proposal stays true to the original problem anchor. No drift detected.

---

## Action Items Summary

| # | Issue | Priority | Section |
|---|-------|----------|---------|
| 1 | Chain Extractor lacks pseudocode and parameter specification | CRITICAL | Method Specificity |
| 2 | Contribution framing too weak — needs algorithmic depth (Option A recommended) | CRITICAL | Contribution Quality |
| 3 | Venue readiness depends on fixing Contribution Quality | CRITICAL | Venue Readiness |
| 4 | Sharpen distinction from SPARSE Suspicious Flow Paths | IMPORTANT | Problem Fidelity |
| 5 | Quantify data augmentation strategy | IMPORTANT | Feasibility |
| 6 | Cross-dataset validation to main paper | IMPORTANT | Validation Focus |
| 7 | Define "investigation cost" metric formally | IMPORTANT | Validation Focus |
| 8 | Simplify Path Assembler and Node Profiler | MINOR | Simplification |
| 9 | Ground Chain Extractor in causal inference theory | MINOR | Modernization |
