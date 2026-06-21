# Round 2 Refinement

## Problem Anchor
[Unchanged]

## Anchor Check
- Original bottleneck still addressed. The theoretical additions (causal coherence metric, Markov condition) serve the same bottleneck — ensuring extracted chains are causally meaningful.
- No drift.

## Simplicity Check
- **Single contribution paper**: Removed "supporting contribution" framing. One paper, one contribution: causal chain extraction algorithm.
- **Reduced SCM formalism**: Switched from full Pearl framework to simpler causal sufficiency assumption (provenance graphs already satisfy this by construction).
- **Added causal coherence metric**: Lightweight intrinsic evaluation — doesn't require additional experiments, can be computed during chain extraction.

---

## Changes Made

### 1. Single Contribution Focus
- **Purpose**: "One paper, one dominant contribution."
- **Change**: Removed "Node Profiler as supporting contribution." Node Profiler is now feature engineering only. Removed "Transformer as validation mechanism" from contribution — it's just the evaluation instrument.
- **Impact**: Paper now has one clear thesis: "We propose a causally-grounded chain extraction algorithm. It works better than alternatives."

### 2. Causal Coherence Metric (Addressing Gap 2)
- **Purpose**: Provide intrinsic chain quality evaluation independent of Transformer.
- **Change**: Added definition — causal coherence of chain C = fraction of consecutive edge pairs (e_i, e_{i+1}) where dst(e_i) and src(e_{i+1}) share a causal path of length ≤ δ with temporal gap ≤ τ. Estimated from inter-event statistics on benign data. Used to calibrate δ and λ parameters.
- **Impact**: Chain Extractor parameters can now be tuned without training the Transformer. Stronger experimental story: "chains are causally coherent by construction, not just by Transformer preference."

### 3. Connection to Causal Representation Learning (Addressing Modernization)
- **Purpose**: Provide theoretical motivation for cross-dataset generalization.
- **Change**: Added paragraph connecting to Schölkopf's causal representation learning: causally-extracted features (chains following causal edges) should be more invariant to distribution shift than correlation-based features (windows, random walks). This predicts that our chains will transfer better to StreamSpot than EagleEye windows or Sentient scenarios.
- **Impact**: The cross-dataset experiment now has a theoretical prediction behind it, not just "let's see if it works."

### 4. Lightweight Causal Sufficiency Statement (Addressing Gap 1)
- **Purpose**: Provide formal grounding without over-formalizing.
- **Change**: Added "Causal Sufficiency in Provenance Graphs" paragraph: provenance graphs, by construction from kernel-level audit logs, observe all system entities and events. Therefore common causes are observed (causal sufficiency holds). Under causal sufficiency, temporal order + causal edge direction → causal relation. This justifies why following edge direction with temporal decay is causally meaningful.
- **Impact**: Theoretical grounding without heavy math. Accessible to security reviewers.

---

## Final Revised Proposal

# Research Proposal: Temporal Causal Chain Extraction for APT Detection on Provenance Graphs

## Problem Anchor
[Unchanged from Round 0]

## Technical Gap

Existing methods produce chains/paths from provenance graphs using:
1. **Rules + external knowledge** (SPARSE, Holmes) — cannot detect novel attacks
2. **Structure heuristics** — fixed windows (EagleEye), random walks (Sentient), temporal subgraphs (GET-AID) — don't respect causal edge direction
3. **Post-hoc reconstruction** (SLOT, CAGE, EdgeTrace) — chain quality bounded by upstream detection recall

**The missing piece**: A chain extraction method that respects causal structure, uses learned (not rule-based) signals, and produces chains with quantifiable causal coherence.

## Method Thesis

**One sentence**: We propose a causally-grounded temporal chain extraction algorithm for provenance graphs — using TGN temporal memory for seed identification and causal edge tracing with principled termination — and demonstrate that causally-extracted chains are more discriminative for APT detection than chains from heuristic, rule-based, or post-hoc methods.

## Contribution Focus

**Single contribution**: A temporal causal chain extraction algorithm for provenance graphs, characterized by:
1. TGN-guided seed identification using learned temporal state
2. Causal-direction-respecting forward/backward tracing with formal termination
3. Temporal decay weighting for causal relevance decay over time
4. Branch management via temporal coherence pruning
5. Intrinsic evaluation via causal coherence metric (model-free)

**Not claimed as contributions**: TGN (reused), Transformer (standard architecture), Node Profiler (feature engineering), chain-level detection framing (SPARSE acknowledged).

## Proposed Method

### Causal Sufficiency in Provenance Graphs

Provenance graphs constructed from kernel-level audit logs observe all system entities (processes, files, sockets) and all system events (system calls). By construction, there are no unobserved confounders — causal sufficiency holds.

Under causal sufficiency, for any two events e_i=(u→v) and e_j=(x→y) where: (a) v shares identity with x or there exists a directed path v→...→x, (b) time(e_i) < time(e_j), and (c) time(e_j) - time(e_i) < τ (temporal proximity threshold) — the edge direction (u→v→...→x→y) represents a causal relation.

This justifies our design: follow causal edge directions, weight by temporal proximity.

### Causal Coherence Metric

For a chain C = [e₁, e₂, ..., eₙ], define:

coherence(C) = (1/(n-1)) × Σᵢ₌₁ⁿ⁻¹ 𝟙[causal_path_exists(dst(eᵢ), src(eᵢ₊₁), δ) ∧ time_gap ≤ τ]

where causal_path_exists(a, b, δ) returns true if there exists a directed path from a to b of length ≤ δ.

This metric is **model-free** — computable directly from the provenance graph without any trained model. It measures whether the extracted chain respects the causal structure of the underlying system.

Used for:
- Calibrating δ and λ on benign data (maximize coherence of benign chains → parameters that capture normal causal structure)
- Diagnosing chain quality before training the Transformer

### Chain Extractor Algorithm
[Same pseudocode as Round 1, with parameters now calibrated via causal coherence on benign data]

### Transformer Discriminator
[Same as Round 1 — standard 3-layer Transformer, 1.5M params, no novelty claimed]

### Node Profiler
[Same as Round 1 — feature engineering only, 5 precomputed node properties]

## Claim-Driven Validation Sketch

### Experiment 1: Chain extraction quality (DARPA E3)
- **Setup**: Fix Transformer. Vary only chain extraction method.
- **Compared**: (1) Our causal extractor, (2) EagleEye fixed-window, (3) Sentient random-walk, (4) GET-AID temporal-subgraph, (5) SPARSE rule-based
- **Metrics**: Chain-level F1, causal coherence, investigation cost
- **Expected**: >10% F1 improvement. Our chains have highest causal coherence.

### Experiment 2: Cross-dataset generalization (StreamSpot)
- **Setup**: Same pipeline. TGN + Transformer retrained on StreamSpot. Chain Extractor parameters (δ, λ, τ) recalibrated via causal coherence on StreamSpot benign data — no manual tuning.
- **Theoretical prediction**: Causal features generalize better under distribution shift than correlation-based features (causal representation learning).
- **Expected**: Our method degrades less than EagleEye/Sentient alternatives.

### Experiment 3: Ablation suite
Same 6 ablations as Round 1. Key new ablation: remove causal direction enforcement → random walk within δ hops. Expected: largest F1 drop.

## Compute & Timeline
Same as Round 1. ~10 GPU-hours. 4-week timeline.
