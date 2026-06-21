# Research Proposal: Causal Chain Discrimination for APT Detection on Provenance Graphs

## Problem Anchor

- **Bottom-line problem**: Existing provenance-based APT detection systems detect at coarse granularities (time windows, graph snapshots, individual entities) but cannot identify APT attacks as cohesive causal event chains — which is what SOC analysts actually need for investigation. Recent transformer-on-provenance methods (EagleEye eCrime 2024, Sentient AAAI 2026, GET-AID ESORICS 2025) have improved detection but still operate on fixed windows, random-walk segments, or temporal subgraphs rather than causally-meaningful event chains.

- **Must-solve bottleneck**: The gap between (a) detecting that "something anomalous happened somewhere in this window/graph" and (b) identifying exactly "which sequence of causally-connected events constitutes the attack" has not been closed. Post-hoc chain reconstruction (SLOT, CAGE, EdgeTrace) depends on upstream detection quality — one missed node breaks the chain. What's missing is a method that treats the causal chain itself as the detection unit, not the reconstruction target.

- **Non-goals**:
  - NOT building a general-purpose provenance graph representation learning method
  - NOT improving node-level or edge-level anomaly detection in isolation
  - NOT using LLMs for attack report generation or RAG-based investigation
  - NOT handling cross-domain or federated scenarios

- **Constraints**:
  - Primary dataset: DARPA TC E3 (CADETS) — 268K nodes, 29.7M edges, single attack day (April 6)
  - No additional attack labels beyond existing DARPA ground truth
  - Compute: single GPU (RTX 2080 Ti / 3090 level), training in hours not days
  - Must be comparable against KAIROS, MAGIC, EagleEye, Sentient, GET-AID

- **Success condition**: On DARPA E3, the method identifies the ground-truth attack causal chain with >90% edge F1 at the chain level, with chain-level false positive rate <5%, and produces attack narratives that are more actionable (fewer edges to investigate) than Sentinel/SLOT/KAIROS. Ablation shows causal chain extraction outperforms fixed-window (EagleEye) and random-walk (Sentient) alternatives by >10% absolute F1.

## Technical Gap

### Where current methods fail

1. **EagleEye (eCrime 2024)**: Linearizes provenance events into fixed-size windows, uses Transformer for classification. But fixed windows break causal dependencies across window boundaries and mix causally-unrelated events. The Transformer sees a bag of co-occurring events, not a causal chain.

2. **Sentient (AAAI 2026)**: Uses Graph Transformer with random-walk scenario segmentation. Graph Transformer operates on the entire subgraph (graph-native attention), not on causal sequences. Random-walk scenarios may include causally-irrelevant nodes. The Intent Analysis Module captures behavioral logic but at the scenario level, not the individual causal chain level.

3. **GET-AID (ESORICS 2025)**: Two-stage graph-native attention (node-level + event-level TransformerConv). Still operates in graph space, not sequence space. Temporal subgraphs are time-based partitions, not causality-based partitions.

4. **KAIROS/MAGIC/Unicorn**: Operate at window/entity/snapshot level, not chain level.

### Why naive fixes are insufficient

- "Just post-process KAIROS/KAIROS's output into chains": Chain quality bounded by upstream detection FN rate.
- "Just replace EagleEye's fixed window with causal chains": This is partly what we're doing, but (a) the chain extraction algorithm is non-trivial, (b) temporal memory (TGN) provides node state tracking that EagleEye's static features miss, (c) Node Profiler injects global context that EagleEye's local features lack.
- "Just use a larger Transformer / LLM": Not needed for ~50-step sequences; small Transformer is more efficient and less prone to overfitting.

### The missing mechanism

A **temporal-graph-aware causal chain extractor** that uses TGN's temporal memory to identify anomalous seed events, then traces causal dependencies to produce causally-coherent event chains — coupled with a **sequence Transformer** that discriminates attack chains from benign chains by learning inter-event corroboration patterns, enriched by **globally-precomputed node properties** (Node Profiler) that no existing Transformer-on-provenance method provides.

## Method Thesis

- **One-sentence thesis**: Causal chain extraction from temporally-aware provenance graphs, combined with sequence-level Transformer discrimination enriched by global node properties, achieves finer-grained and more actionable APT detection than window-based, subgraph-based, or post-hoc chain reconstruction methods.

- **Why this is the smallest adequate intervention**: We reuse KAIROS's TGN backbone (proven effective, provides temporal memory). We add one new extractor (Chain Extractor — causal tracing) and one new discriminator (small Transformer). Node Profiler is a precomputation, not a trainable module. This is a focused 3-component pipeline, not a sprawling system.

- **Why this route is timely**: The field has rapidly converged on "Transformer + provenance" (EagleEye 2024, Sentient 2026, GET-AID 2025, FALCON 2025), but no method has combined (a) TGN temporal memory, (b) explicit causal chain extraction, and (c) global node property injection. This specific combination fills the gap between "transformer on windows" and "post-hoc chain reconstruction."

## Contribution Focus

- **Dominant contribution**: Causal chain as the detection unit — formulating APT detection as end-to-end discrimination of causally-extracted event sequences, and demonstrating that this formulation outperforms window-based (EagleEye), random-walk-scenario-based (Sentient), and post-hoc-chain-reconstruction-based (SLOT, CAGE) alternatives.

- **Optional supporting contribution**: Node Profiler — a systematic framework for injecting global provenance graph statistics (IDF, centrality, community, degree anomaly, path sensitivity) into sequence Transformer token features. This bridges global graph topology and local sequence modeling in a way no existing provenance Transformer method does.

- **Explicit non-contributions**:
  - NOT claiming novelty in TGN backbone (reused from KAIROS)
  - NOT claiming novelty in Transformer architecture (standard encoder)
  - NOT claiming novelty in individual node properties (IDF from KAIROS, centrality from network science)
  - NOT claiming to be the first to use Transformer on provenance (EagleEye, Sentient precede us)

## Proposed Method

### Complexity Budget

- **Frozen / reused backbone**: KAIROS TGN (GraphAttentionEmbedding + TGNMemory + LinkPredictor), pretrained on benign data. Node feature hashing from KAIROS (path hierarchy hash). Edge type one-hot encoding from KAIROS.

- **New trainable components**: 
  1. Chain Extractor (algorithmic, non-trainable — but novel algorithm)
  2. Small Transformer Encoder (~3 layers, d_model=128, 4 heads, ~1.5M params)
  3. Node Profiler (precomputation, non-trainable)

- **Tempting additions intentionally not used**:
  - No Graph Transformer / graph-native attention (Sentient/GET-AID already do this; we deliberately go sequence route)
  - No LLM for attack report generation
  - No contrastive pre-training (can be added later but not core)
  - No reinforcement learning for chain extraction (CAGE, SLOT already do this)
  - No Mamba/SSM for long sequences (chains are short, ~10-50 events)
  - No federated learning (FALCON's domain)

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        OFFLINE / ONE-TIME                        │
│                                                                  │
│  Provenance Graph ──→ Node Profiler ──→ Node Property Vectors   │
│  (full dataset)        (IDF, centrality,      (per node)         │
│                         degree anomaly,                          │
│                         community ID,                            │
│                         path sensitivity)                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                        ONLINE / STREAMING                        │
│                                                                  │
│  Incoming Events                                                 │
│       │                                                          │
│       ▼                                                          │
│  ┌─────────┐     ┌──────────────┐     ┌──────────────────┐      │
│  │  TGN    │────→│   Chain      │────→│  Transformer     │────→ │
│  │  Filter │     │  Extractor   │     │  Discriminator   │      │
│  │         │     │              │     │                  │      │
│  │ edge    │     │ seed→fwd/bwd │     │ 3-layer encoder  │      │
│  │ loss    │     │ causal trace │     │ self-attention   │      │
│  │ Top-K   │     │ branch split │     │ chain score      │      │
│  └─────────┘     └──────────────┘     └──────────────────┘      │
│       │               │                      │                  │
│       │          ┌────┴────┐            ┌────┴────┐            │
│       │          │ Node    │            │ Path    │            │
│       │          │ Profiler│            │Assembler│            │
│       │          │ vectors │            │         │            │
│       │          └─────────┘            │ overlap │            │
│       │                                 │ + time  │            │
│       │                                 │ merge   │            │
│       │                                 └────┬────┘            │
│       │                                      │                  │
│       │                                      ▼                  │
│       │                              Attack Causal Path        │
└─────────────────────────────────────────────────────────────────┘
```

### Core Mechanism: Causal Chain Discriminator

**Input**: A causal chain = ordered sequence of events [e₁, e₂, ..., eₙ], where each event eᵢ is a provenance graph edge (src_node → dst_node) with:
- src_node features: [node2higvec (16) | node_type (3) | IDF (1) | sensitivity (1) | degree_anomaly (1) | community_id (1) | bridge_centrality (1)] = 24 dims
- edge features: [edge_type_onehot (7) | time_delta_from_prev (1) | was_seed (1)] = 9 dims
- dst_node features: [same 24 dims as src]
- structure markers: [is_branch_point (1) | is_merge_point (1) | depth_from_seed (1)] = 3 dims

Total per-event feature: 24 + 9 + 24 + 3 = 60 dimensions

**Output**: Chain-level anomaly score ∈ [0, 1]

**Architecture**: 
- Linear projection: 60 → 128
- Positional encoding (sinusoidal, by event index in chain)
- 3-layer Transformer Encoder (d_model=128, nhead=4, d_ff=512, dropout=0.1)
- Mean pooling over sequence → Linear 128 → 64 → 1 → Sigmoid

**Training signal**: Binary cross-entropy loss. Positive chains = ground-truth attack chains (extracted from known attack nodes). Negative chains = chains extracted from TGN seeds on benign days (April 2-4).

**Why this is the main novelty**: Unlike EagleEye (Transformer on fixed windows), our Transformer operates on causally-connected events only. Unlike Sentient (Graph Transformer on subgraphs), our Transformer operates in sequence space where causal ordering is explicit. Unlike GET-AID (graph-native attention), our self-attention directly models inter-event corroboration along causal direction. Unlike SLOT/CAGE (post-hoc chain assembly), our chain is the detection unit, not the output.

### Optional Supporting Component: Node Profiler

**Input**: Full provenance graph (all days, all nodes, all edges)

**Computation** (one-time, offline):
1. **IDF**: log(total_time_windows / time_windows_containing_node) — higher = rarer
2. **Path Sensitivity**: whether node path contains sensitive keywords (/etc/passwd, /etc/shadow, /root/, authorized_keys, etc.) — binary or multi-level
3. **Degree Anomaly**: |degree(node) - mean_degree(node_type)| / std_degree(node_type)
4. **Bridge Centrality**: betweenness centrality normalized by node type
5. **Community ID**: Louvain community assignment on the undirected version of the provenance graph

**Output**: Per-node 5-dim vector, concatenated with KAIROS's existing 16-dim node2higvec

**Why it does not create contribution sprawl**: Node Profiler is a feature engineering module, not a trainable component. Its properties are standard network science metrics adapted to provenance graphs. The contribution is the *integration* — showing that these global properties significantly improve Transformer chain discrimination.

### Training Plan

**Stage 1: TGN Pretraining** (reuse KAIROS)
- Train on April 2-4 benign data
- Task: edge type prediction
- Loss: CrossEntropyLoss
- ~50 epochs, already done by KAIROS

**Stage 2: Training Data Construction**
- Positive chains: From ground-truth attack nodes on April 6, extract all causal chains using Chain Extractor. Expected: ~50-200 chains.
- Negative chains: Run TGN + Chain Extractor on April 2-4 (benign days). Extract chains from Top-K seeds. Expected: ~2000-5000 chains.
- Data augmentation for positive chains:
  - Sub-chain sampling (take consecutive subsequences of attack chains)
  - Node generalization (replace specific file paths with type-level tokens for some samples)
  - Expected after augmentation: ~500-2000 positive chains

**Stage 3: Transformer Training**
- 80/20 train/val split (stratified by chain)
- Class-weighted BCE loss (weight_positive = n_negative / n_positive)
- Adam optimizer, lr=1e-4, weight_decay=1e-4
- Early stopping on val loss, patience=10
- ~100 epochs, <1 hour on single GPU

**Stage 4: Path Assembly (inference only)**
- High-scoring chains (>0.5) with shared nodes + temporal proximity → merge
- Output: complete attack path as a connected subgraph

### Failure Modes and Diagnostics

- **Failure mode 1**: Chain Extractor misses a critical attack event (e.g., the FORK that spawned the malicious process)
  - **Detect**: Check if ground-truth attack nodes are absent from extracted chains
  - **Mitigation**: Lower the loss threshold for seeds; expand trace depth

- **Failure mode 2**: Transformer overfits to the single attack pattern in E3
  - **Detect**: Test on StreamSpot or OpTC; check if only one type of attack chain gets high scores
  - **Mitigation**: Stronger data augmentation; type-level features vs instance-level

- **Failure mode 3**: Negative chain contamination (April 2-4 may contain unknown attacks)
  - **Detect**: Inspect high-scoring "negative" chains manually
  - **Mitigation**: Use multiple benign days for negative mining; filter by IDF

### Novelty and Elegance Argument

**Closest work and exact difference**:

| Closest Work | What They Do | What We Do Differently |
|---|---|---|
| EagleEye | Fixed-window Transformer | Causal-chain Transformer + TGN temporal memory + Node Profiler |
| Sentient | Graph Transformer + random-walk scenarios | Sequence Transformer + causal tracing + Node Profiler |
| GET-AID | Two-stage graph-native attention | TGN filter + sequence Transformer (graph→sequence hybrid) |
| CAGE/SLOT | Post-hoc attack path reconstruction | Chain as detection unit (end-to-end) |

**Why this is a focused mechanism-level contribution**: We make one core change to the detection paradigm (from windows/subgraphs to causal chains) and support it with two enabling components (TGN temporal memory for seed selection, Node Profiler for feature enrichment). The architecture is minimal — TGN (reused) + causal trace (algorithm) + small Transformer (~1.5M params) + precomputed features. There is no module bloat.

## Claim-Driven Validation Sketch

### Claim 1: Causal chain detection outperforms window-based and subgraph-based alternatives

- **Minimal experiment**: Compare chain-level F1 of our method vs (a) EagleEye-style fixed-window Transformer, (b) Sentient-style random-walk scenario + Transformer, (c) GET-AID-style temporal subgraph + Transformer, all using the same Transformer architecture and features but different input segmentation strategies.
- **Baselines / ablations**: EagleEye (fixed window), Sentient-style (random walk), GET-AID-style (temporal subgraph), KAIROS (window-level), MAGIC (entity-level), SLOT (post-hoc chain)
- **Metric**: Chain-level Precision / Recall / F1, Attack Path Completeness (fraction of ground-truth attack edges recovered), Analysts' Investigation Cost (#edges analyst must examine)
- **Expected evidence**: Our causal chain method achieves >10% absolute improvement in chain-level F1 over window/subgraph alternatives, and recovers >90% of ground-truth attack edges while reducing investigation cost by >50x vs KAIROS.

### Claim 2: Node Profiler features significantly improve Transformer discrimination

- **Minimal experiment**: Ablation: train Transformer with and without Node Profiler features. Measure chain-level AUC difference.
- **Baselines / ablations**: Without Node Profiler (KAIROS features only), Without IDF, Without centrality, Without sensitivity, Each Node Profiler component individually
- **Metric**: Chain-level AUC, Precision/Recall at fixed threshold
- **Expected evidence**: Node Profiler contributes >5% absolute AUC improvement; IDF and sensitivity are the most important components.

## Experiment Handoff Inputs

- **Must-prove claims**: Causal chain > window/subgraph (Claim 1), Node Profiler > baseline features (Claim 2)
- **Must-run ablations**: Fixed window vs causal chain vs random walk segmentation, with/without Node Profiler, with/without TGN temporal memory, Transformer vs LSTM vs MLP
- **Critical datasets / metrics**: DARPA E3 (primary), StreamSpot (secondary for cross-dataset), chain-level F1 (primary), investigation cost reduction (secondary)
- **Highest-risk assumptions**: (1) Causal chain extraction quality — if chains are noisy, Transformer can't compensate. (2) Positive sample scarcity — E3 has one attack day, may need data augmentation.

## Compute & Timeline Estimate

- **Estimated GPU-hours**: TGN pretraining ~5h (reuse KAIROS checkpoint), Chain extraction ~2h (CPU), Transformer training ~1h, Evaluation ~1h. Total: ~9 GPU-hours.
- **Data / annotation cost**: Ground truth already available from DARPA/MAGIC annotations. No new annotation needed.
- **Timeline**: Week 1: Chain Extractor implementation + Node Profiler. Week 2: Transformer training + ablation experiments. Week 3: Full baseline comparison + analysis. Week 4: Paper writing.
