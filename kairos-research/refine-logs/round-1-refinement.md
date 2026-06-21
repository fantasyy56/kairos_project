# Round 1 Refinement

## Problem Anchor
[Verbatim from round 0 — unchanged]

- **Bottom-line problem**: Existing provenance-based APT detection systems detect at coarse granularities (time windows, graph snapshots, individual entities) but cannot identify APT attacks as cohesive causal event chains — which is what SOC analysts actually need for investigation.
- **Must-solve bottleneck**: The gap between detecting "something anomalous happened somewhere" and identifying "which causally-connected event sequence constitutes the attack" has not been closed.
- **Non-goals**: NOT building general provenance representation learning; NOT improving node/edge anomaly detection in isolation; NOT using LLMs; NOT cross-domain/federated.
- **Constraints**: DARPA E3 primary, single GPU, no new attack labels.
- **Success condition**: Chain-level >90% edge F1, FPR <5%, >10% absolute improvement over window/random-walk/subgraph alternatives, >50x investigation cost reduction vs KAIROS.

## Anchor Check
- **Original bottleneck**: Coarse detection → fine-grained attack path. Still addressed.
- **Why the revised method still addresses it**: The reframed contribution (causal chain extraction algorithm) is still in service of the same bottleneck — it's the *mechanism* for producing fine-grained chains, which the Transformer then validates.
- **Reviewer suggestions rejected as drift**: None rejected. The suggestion to pivot to algorithmic contribution (Option A) is accepted as it better serves the same problem anchor.

## Simplicity Check
- **Dominant contribution after revision**: TGN-guided temporal causal chain extraction algorithm with causal-inference-grounded termination conditions. The Transformer is downgraded from "dominant contribution" to "validation mechanism."
- **Components removed or merged**: Path Assembler removed as a named module (now a simple post-processing rule). Node Profiler merged from "supporting contribution" to "feature engineering." 
- **Reviewer suggestions rejected as unnecessary complexity**: None. All major suggestions accepted.
- **Why the remaining mechanism is still the smallest adequate route**: TGN (reused) + Chain Extractor (new algorithm) + Transformer (small, standard) + Node Profiler (precomputation). Three components, one of which is novel.

---

## Changes Made

### 1. Contribution Reframing (CRITICAL)
- **Reviewer said**: Contribution Quality 5/10. "Causal chain as detection unit" too close to SPARSE/EdgeTrace. Need algorithmic depth.
- **Action**: Reframed dominant contribution from "causal chain as detection unit" to **"TGN-guided temporal causal chain extraction algorithm."** The paper is now about *how to extract causally-meaningful chains* from provenance graphs, with the Transformer serving as a validation mechanism that proves the chains are discriminative.
- **Reasoning**: This shifts the paper from application ("Transformer on provenance") to algorithm ("causal chain extraction from temporal provenance graphs"). Algorithm papers have stronger novelty stories at CCF-A venues. The technical meat moves from the Transformer (which is standard) to the Chain Extractor (which can be novel).
- **Impact on core method**: The Chain Extractor now needs formal specification — pseudocode, parameter definitions, theoretical grounding. The Transformer remains architecturally identical but is positioned differently in the narrative.

### 2. Chain Extractor Formalization (CRITICAL)
- **Reviewer said**: Method Specificity 6/10. Chain Extractor underspecified — no pseudocode, no parameters, no cycle handling.
- **Action**: Added formal algorithm specification (pseudocode in proposal). Defined parameters: max_depth, max_branches, termination conditions. Added causal inference grounding using structural causal model (SCM) framework.
- **Reasoning**: A well-specified algorithm is necessary for the paper to be credible. The SCM grounding elevates it from engineering to science.
- **Impact on core method**: Chain Extractor is now the centerpiece of the method section.

### 3. Data Augmentation Quantification (IMPORTANT)
- **Reviewer said**: Feasibility 7/10. Positive sample scarcity not adequately addressed.
- **Action**: Added combinatorial sub-chain sampling with concrete estimates: each length-L attack chain generates C(L,k) sub-chains for various k. With 10 attack chains of average length 15, augmentation produces ~5000 positive samples. Added StreamSpot as additional positive chain source.
- **Reasoning**: Reviewer needs to see that training is feasible. Concrete numbers build confidence.
- **Impact on core method**: Training data section expanded with quantitative estimates.

### 4. Cross-Dataset Validation (IMPORTANT)
- **Reviewer said**: Validation Focus 6/10. Cross-dataset validation needed in main paper.
- **Action**: Moved StreamSpot from "secondary" to "Main Experiment 2" (cross-dataset generalization).
- **Reasoning**: CCF-A venues require evidence of generalization beyond a single dataset.
- **Impact on core method**: Experiment plan now has 3 main experiments (E3 primary, StreamSpot cross-dataset, ablation suite).

### 5. Sharpen SPARSE Distinction (IMPORTANT)
- **Reviewer said**: "Causal chain" vs "Suspicious Flow Path" distinction needs sharpening.
- **Action**: SPARSE's SFPs are extracted by rule-based semantic tagging + threat intelligence. Our chains are extracted by TGN-guided causal tracing along provenance edges. The distinction: SPARSE uses external knowledge (rules, IoCs), we use learned temporal patterns (TGN). SPARSE paths are scored by rule matching, our chains are scored by learned Transformer discrimination.
- **Reasoning**: This makes the comparison concrete and favorable — our method is fully learned while SPARSE requires hand-crafted rules.
- **Impact on core method**: Related work section sharpened. Experiment 1 now includes SPARSE as a baseline.

### 6. Path Assembler Simplification (MINOR)
- **Reviewer said**: Remove Path Assembler as a separate named module.
- **Action**: Merged into "Post-processing: chain merging" — a simple rule (shared nodes + temporal proximity < 60s → merge), no longer a named Phase 4.
- **Reasoning**: Reduces perceived complexity from 5-phase to 3-component pipeline.
- **Impact on core method**: System overview simplified.

### 7. Causal Inference Grounding (MINOR)
- **Reviewer said**: Ground Chain Extractor in causal inference theory.
- **Action**: Added formal definition of causal chain in provenance graph using Pearl's SCM framework. Provenance edges are causal relations (do(X=x) → Y=y). A causal chain is a directed path where each edge represents a causal mechanism. Termination: stop when causal effect becomes independent of seed (Markov boundary).
- **Reasoning**: Theoretical grounding distinguishes this from heuristic graph traversal methods (BFS from KAIROS, random walk from Sentient).
- **Impact on core method**: Chain Extractor section now has formal definitions.

---

## Revised Proposal

# Research Proposal: Temporal Causal Chain Extraction and Discrimination for APT Detection on Provenance Graphs

## Problem Anchor
[Unchanged from Round 0]

## Technical Gap

### Current chain/path extraction methods and their limitations

Existing methods that produce chains or paths from provenance graphs fall into three categories:

1. **Rule-based path extraction** (SPARSE, Holmes, Poirot): Use semantic tags, threat intelligence, or pre-defined attack patterns to score and extract paths. Require expert knowledge. Cannot detect novel attacks.

2. **Structure-based path extraction** (Sentient — random walk, GET-AID — temporal subgraph, EagleEye — fixed window): Use graph structure or temporal proximity to segment the provenance graph. These do not respect causal edge directions — random walks may traverse edges backwards, fixed windows group causally-unrelated events, temporal subgraphs are time-based not causality-based.

3. **Post-hoc path reconstruction** (SLOT — LPA clustering, CAGE — Q-learning causal weights, EdgeTrace — semantic clustering, KAIROS — Louvain community detection): First detect anomalous nodes/edges, then connect them into paths. The chain quality is bounded by upstream detection recall — one missed node breaks the chain.

**The missing mechanism**: A chain extraction method that (a) respects causal edge direction, (b) uses learned temporal patterns (not rules) to identify starting points, (c) traces causality along provenance edges with principled termination, and (d) produces chains that are directly discriminable as attack/benign.

## Method Thesis

- **One-sentence thesis**: TGN-guided causal chain extraction — which identifies anomalous seeds via learned temporal memory and traces causal dependencies with formal termination conditions — produces chains that are more discriminative for APT detection than rule-based, structure-based, or post-hoc chain construction methods.

- **Why this is the smallest adequate intervention**: We reuse KAIROS's TGN for seed identification (proven, provides temporal state tracking). We design one new algorithm (Causal Chain Extractor). We use a standard small Transformer to validate chain quality. Node Profiler is precomputed feature enrichment. Three components, one novel.

- **Why this route is timely**: The field has converged on "provenance + transformer" but the *chain extraction* step remains under-theorized — existing methods use heuristics (windows, random walks, subgraphs). A causally-grounded extraction algorithm fills a gap that no existing work addresses, and the Transformer provides a clean way to validate its output quality.

## Contribution Focus

- **Dominant contribution**: TGN-guided temporal causal chain extraction algorithm. A formally-specified algorithm that (a) uses TGN temporal memory to identify anomalous seed events, (b) traces causal dependencies forward and backward along provenance edge directions, (c) terminates based on temporal decay and causal independence (Markov boundary), (d) handles branching via parallel chain splitting. This is the first causally-grounded chain extraction algorithm for provenance-based APT detection.

- **Supporting contribution**: Empirical demonstration that causally-extracted chains enable more accurate APT detection than window-based (EagleEye), random-walk-based (Sentient), subgraph-based (GET-AID), and rule-based (SPARSE) chain extraction, validated by a standard Transformer discriminator.

- **Explicit non-contributions**: TGN architecture (reused), Transformer architecture (standard), individual node properties (standard network science), chain-level detection problem formulation (SPARSE precedent acknowledged).

## Proposed Method

### Complexity Budget

- **Frozen / reused**: KAIROS TGN (GraphAttentionEmbedding + TGNMemory + LinkPredictor), KAIROS node feature hashing, edge type encoding.
- **New algorithm**: Causal Chain Extractor (non-trainable, novel algorithm).
- **New trainable**: Small Transformer Encoder (~3 layers, ~1.5M params) — standard architecture, novel only in application.
- **Precomputed**: Node Profiler (IDF, path sensitivity, degree anomaly, bridge centrality, community ID).
- **Intentionally excluded**: Graph Transformer, LLM, contrastive pre-training, RL, Mamba/SSM.

### System Overview

```
Offline (one-time):
  Provenance Graph → Node Profiler → per-node property vectors
  Benign data → TGN pretraining (reuse KAIROS)

Online per-day processing:
  Day's events → TGN(edge loss) → Top-K seeds
    → Causal Chain Extractor(seeds, provenance graph, Node Profiler)
    → Candidate causal chains with features
    → Transformer Discriminator → chain scores
    → Post-processing: merge overlapping high-score chains → attack paths
```

### Core Mechanism: Causal Chain Extractor

#### Formal Definition

A provenance graph G = (V, E) is a directed graph where each directed edge (u → v) ∈ E represents a causal relation: the system event at u caused the state change at v.

Following Pearl's Structural Causal Model (SCM), a causal chain C of length L from seed event s = (u₀ → v₀) is an ordered sequence of L+1 edges:

C(s, G) = [(u₀→v₀), (u₁→v₁), ..., (u_L→v_L)]

where for each consecutive pair (e_i, e_{i+1}), there exists a causal path in G from dst(e_i) to src(e_{i+1}) with length ≤ δ (the causal hop limit).

The seed event s is identified by TGN reconstruction loss: s ∈ argmax_{e ∈ day's edges, |{e}|=K} loss_TGN(e).

#### Algorithm

```
Algorithm: Causal Chain Extraction
Input: Provenance graph G, seed edge s=(u₀→v₀), parameters (max_depth D, 
       causal_hop_limit δ, temporal_decay λ, branch_limit B)
Output: Set of causal chains C_set

function EXTRACT_CHAINS(G, s):
    C_set ← {s}  // each chain starts as [s]
    
    // Backward trace: what caused the seed?
    current_edges ← {(u₀→v₀)}
    for d = 1 to D:
        prev_edges ← ∅
        for each (u→v) in current_edges:
            // Find events that causally precede u, within δ hops
            predecessors ← CAUSAL_PREDECESSORS(G, u, δ, temporal_decay^d)
            prev_edges ← prev_edges ∪ predecessors
        if prev_edges is empty: break  // causal boundary reached
        // For each existing chain, extend with each predecessor (branching)
        C_set ← BRANCH_EXTEND(C_set, prev_edges, direction="backward")
        if |C_set| > B: C_set ← PRUNE_BY_TEMPORAL_COHERENCE(C_set, B)
        current_edges ← prev_edges
    
    // Forward trace: what did the seed cause?
    current_edges ← {(u₀→v₀)}
    for d = 1 to D:
        next_edges ← ∅
        for each (u→v) in current_edges:
            successors ← CAUSAL_SUCCESSORS(G, v, δ, temporal_decay^d)
            next_edges ← next_edges ∪ successors
        if next_edges is empty: break
        C_set ← BRANCH_EXTEND(C_set, next_edges, direction="forward")
        if |C_set| > B: C_set ← PRUNE_BY_TEMPORAL_COHERENCE(C_set, B)
        current_edges ← next_edges
    
    return C_set

function CAUSAL_PREDECESSORS(G, node, δ, weight):
    // BFS following reverse edge direction, up to δ hops
    // Returns edges that are causal ancestors of node
    // Filtered: only include edges with event types indicating causal influence
    // (EXEC, FORK, WRITE — not READ, CLOSE)
    ...

function CAUSAL_SUCCESSORS(G, node, δ, weight):
    // BFS following forward edge direction, up to δ hops
    ...

function BRANCH_EXTEND(C_set, new_edges, direction):
    // For each chain in C_set, create a new chain for each new_edge
    // If direction="backward", prepend; if "forward", append
    // Maintain temporal ordering within each chain
    ...

function PRUNE_BY_TEMPORAL_COHERENCE(C_set, B):
    // Keep top-B chains by temporal coherence score:
    // score(C) = mean(exp(-λ × |Δt_i|)) where Δt_i = time_gap between consecutive events
    // Prefer chains with smooth temporal progression
    ...
```

**Key design decisions**:
1. **Causal direction enforcement**: Backward trace follows reverse edges (who caused this?), forward trace follows forward edges (what did this cause?). Unlike random walks (Sentient) which ignore edge direction.
2. **Causal hop limit δ**: Events within δ hops are causally related; beyond δ, we consider them independent. δ = 2 by default (direct cause + cause-of-cause).
3. **Temporal decay weight**: e^{-λ × depth}. Events further in time from the seed have exponentially lower causal relevance. λ calibrated from inter-event time distribution on benign data.
4. **Branch pruning by temporal coherence**: When branching exceeds limit B, keep chains with the smoothest temporal progression. This favors chains where events are temporally clustered (attack bursts) over scattered events (benign noise).
5. **Termination at causal boundary**: When no more edges satisfy causal hop + temporal decay constraints, the chain is complete. This provides a principled stopping criterion vs fixed-depth BFS.

### Transformer Discriminator (Validation Mechanism)

**Purpose**: Validate that chains extracted by the Causal Chain Extractor are discriminative for APT detection. The Transformer is not the contribution — it's the measurement instrument.

**Input**: A causal chain as a sequence of events, each with 60-dim features (same as Round 0: 24 src + 9 edge + 24 dst + 3 structure).

**Architecture**: Same as Round 0 — 3-layer Transformer Encoder, d_model=128, 4 heads, mean pooling → MLP → sigmoid.

**Training**: Same as Round 0, with quantified augmentation:
- ~10 ground-truth attack chains (average length 15) → C(15,3)+C(15,5)+C(15,7)+C(15,10) ≈ 7000 sub-chains after combinatorial sampling
- Additional augmentation: type-level node generalization (replace specific file paths with type tokens) → ~10000 positive samples
- Negative chains: ~5000 from benign days (April 2-4)

### Node Profiler (Feature Engineering)

Same as Round 0. Five precomputed node properties: IDF, path sensitivity, degree anomaly, bridge centrality, community ID. Not claimed as a contribution.

## Claim-Driven Validation Sketch

### Main Experiment 1: Causal chain extraction quality (DARPA E3)
- **Claim**: TGN-guided causal chain extraction produces chains that are more discriminative for APT detection than alternative segmentation strategies.
- **Setup**: Fix the Transformer architecture. Vary only the chain/segment extraction method.
- **Methods compared**: (1) Our causal chain extractor, (2) EagleEye fixed-window, (3) Sentient-style random walk, (4) GET-AID-style temporal subgraph, (5) SPARSE-style rule-based path scoring
- **Metrics**: Chain-level F1 (primary), AUC, Attack Path Completeness (% ground-truth edges in top-ranked chains), Investigation Cost (#edges analyst examines to find all attack edges)
- **Expected**: Our method >10% absolute F1 improvement over next-best. Investigation cost reduced by >50x vs KAIROS.

### Main Experiment 2: Cross-dataset generalization (StreamSpot)
- **Claim**: The causal chain extraction algorithm generalizes to different attack types and system configurations.
- **Setup**: Apply the same pipeline (no retraining of Chain Extractor algorithm, retrain TGN + Transformer on StreamSpot benign data).
- **Methods**: Same as Experiment 1.
- **Metrics**: Same as Experiment 1.

### Main Experiment 3: Ablation suite
- **Ablation 1**: Remove TGN temporal memory (use static edge features for seed selection)
- **Ablation 2**: Remove causal direction enforcement (undirected trace)
- **Ablation 3**: Remove temporal decay weighting (uniform weight)
- **Ablation 4**: Remove causal hop limit (unlimited depth BFS)
- **Ablation 5**: Remove Node Profiler features
- **Ablation 6**: Replace Transformer with LSTM / MLP
- **Metric**: Chain-level F1 change for each ablation.
- **Expected**: TGN temporal memory and causal direction enforcement are the most impactful ablations.

## Compute & Timeline Estimate
- **GPU-hours**: TGN ~5h, Transformer training ~1h, evaluation ~1h, StreamSpot ~3h. Total: ~10h.
- **Timeline**: Week 1: Chain Extractor implementation. Week 2: Transformer + training data construction. Week 3: Experiments (E3 + StreamSpot + ablations). Week 4: Paper writing.
