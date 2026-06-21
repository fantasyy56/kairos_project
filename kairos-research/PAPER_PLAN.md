# Paper Plan

**Title**: Causal-Edge-Aware Temporal Chain Extraction for APT Detection on Provenance Graphs
**One-sentence contribution**: We propose a model-free Causal Coherence Metric that quantifies the causal structural integrity of event chains extracted from provenance graphs, an unsupervised calibration protocol that discovers the natural causal horizon of an OS from benign data alone, and demonstrate that chains extracted under this metric enable more accurate APT detection than window-based, random-walk-based, subgraph-based, or post-hoc chain reconstruction methods.
**Venue**: ACM CCS 2026
**Type**: Systems Security + Methodology
**Date**: 2026-06-16
**Page budget**: 12 pages (CCS double-column, including references)
**Section count**: 8

---

## Claims-Evidence Matrix

| # | Claim | Evidence | Status | Section |
|---|-------|----------|--------|---------|
| C1 | Causal-direction-respecting chain extraction produces chains that are more discriminative for APT detection than fixed-window (EagleEye), random-walk (Sentient), temporal-subgraph (GET-AID), or rule-based (SPARSE) alternatives | Main Experiment 1: chain-level F1 on DARPA E3, all methods using same Transformer | ⏳ Needs experiment | §6.1 |
| C2 | The Causal Coherence Metric (Φ_bw) with elbow calibration discovers meaningful OS causal horizon without ground truth | Φ_bw distributions: benign vs random chains show significant separation (model-free, verifiable before training) | ⏳ Needs experiment | §5.4, §6.2 |
| C3 | The calibration protocol automatically adapts to different OS configurations | E3 vs E5 elbow point comparison — δ* values differ, but each produces optimal chains for its OS | ⏳ Needs experiment | §6.3 |
| C4 | TGN temporal memory for seed identification improves chain quality over static seed selection | Ablation: remove TGN memory → static edge features → chain F1 drop | ⏳ Needs experiment | §6.4 |
| C5 | The Structural Sparsity Prior (branch-weighted coherence) reduces false positives from high-branching benign processes | Ablation: remove Φ_bw → use Φ only → precision drop; qualitative: Firefox chains demoted, attack chains preserved | ⏳ Needs experiment | §6.4 |
| C6 | Our method adds <20% overhead to KAIROS's TGN pipeline | Latency breakdown: TGN 8min + extraction 2min + Transformer 1s per day | ⏳ Needs experiment | §6.5 |

---

## Structure

### §0 Abstract

- **What we achieve**: We present the first provenance-based APT detection system that identifies attacks at the granularity of causal event chains rather than time windows or individual entities.
- **Why it matters / is hard**: APT attacks are inherently multi-step causal chains; existing methods at best detect "when" or "which entity" is suspicious, not "what sequence of causally-connected events" constitutes the attack. The challenge is twofold: extracting causally-meaningful chains from massive provenance graphs (29M+ edges), and evaluating chain quality without attack labels.
- **How we do it**: We propose Causal Coherence Metric (Φ_bw), a model-free metric that quantifies the causal structural integrity of event chains. A calibration protocol based on elbow detection automatically discovers OS-specific causal horizons from benign data. Chains extracted under Φ_bw guidance are validated by a self-supervised autoregressive Transformer trained solely on benign chains.
- **Evidence**: On DARPA E3, our causal chains achieve X% chain-level F1 (vs Y% for EagleEye windows, Z% for Sentient random walks). Investigation cost reduced by >50× vs KAIROS. Φ_bw separates benign from random chains by >0.X AUC before any model training. Cross-dataset calibration on E5 demonstrates automatic OS adaptation.
- **Most remarkable result**: The calibration protocol discovers distinct causal horizons for different OS configurations (E3: δ*=X, E5: δ*=Y), and causal chains consistently outperform all non-causal segmentation strategies by >10% absolute F1.
- **Estimated length**: 180-220 words
- **Self-contained check**: Reader understands: problem (coarse detection), gap (no causal chain detection), method (model-free metric + calibration), result (outperforms alternatives)

---

### §1 Introduction

- **Opening hook**: "Advanced Persistent Threats unfold as causal chains — an initial compromise enables persistence, which enables privilege escalation, which enables data exfiltration. Yet provenance-based intrusion detection systems, despite operating on graphs that explicitly encode causal dependencies, still detect attacks as isolated time windows, individual entities, or graph snapshots."

- **Gap / challenge**: 
  1. Existing methods (KAIROS, MAGIC, PROGRAPHER) detect at coarse granularities — none identify the actual causal event sequence
  2. Recent Transformer-on-provenance methods (EagleEye, Sentient, GET-AID) use fixed windows, random walks, or temporal subgraphs — none respect causal edge direction
  3. Post-hoc chain reconstruction (SLOT, CAGE) depends on upstream detection quality — one missed node breaks the chain
  4. No existing method provides a way to measure chain quality without ground-truth labels

- **One-sentence contribution**: [from header]

- **Approach overview**: 
  1. Reuse KAIROS's TGN for seed identification (temporal memory flags anomalous edges)
  2. Novel Causal Coherence Metric (Φ_bw) defines what makes a chain "causally good"
  3. Elbow-detection calibration protocol discovers OS-specific parameters from benign data alone
  4. Autoregressive Transformer validates that Φ_bw-extracted chains are more discriminative than alternatives

- **Key questions**: 
  - Q1: Can we measure causal chain quality without labels? → Φ_bw + elbow calibration
  - Q2: Do causally-extracted chains improve APT detection over heuristic segmentation? → Experiment 1
  - Q3: Does the calibration protocol adapt to different OS configurations? → Experiment 3

- **Contributions**:
  1. **Causal Coherence Metric (Φ_bw)**: A model-free metric grounded in OS capability-vs-shared-resource semantics, with a 3-case pairwise coherence function and a structural sparsity prior
  2. **Unsupervised calibration protocol**: Elbow detection on benign data that automatically discovers the natural causal horizon of an OS — no manual parameter tuning
  3. **End-to-end system**: First APT detection system that treats causal chains as the detection unit (not post-processing target), validated on DARPA E3 and E5
  4. **Empirical findings**: Causal chains outperform window/random-walk/subgraph alternatives by >10% F1; investigation cost reduced >50×; Φ_bw separates benign from random chains without any model training

- **Results preview**: Figure 1 (hero) showing: (a) an example causal chain vs an example fixed window on the same provenance subgraph — visually demonstrating that causal chains are tighter and more interpretable; (b) bar chart: chain-level F1 of our method vs all baselines

- **Hero figure (Figure 1)**: Two-panel figure. Left: A small provenance subgraph excerpt from DARPA E3 showing the ground-truth attack chain highlighted in red, with a fixed-window overlay (EagleEye-style) highlighted in blue — demonstrating how the window includes causally-unrelated events while the causal chain follows the attack edges precisely. Right: Bar chart comparing chain-level F1 across our method and 7 baselines.

- **Estimated length**: 1.5 pages (~1200 words)

- **Key citations**: KAIROS (S&P 2024), MAGIC (USENIX Security 2024), EagleEye (eCrime 2024), Sentient (AAAI 2026), GET-AID (ESORICS 2025), SPARSE (2024), SLOT (CCS 2025)

- **Front-loading check**: After reading §1, a skim reader knows: (1) the problem is coarse detection granularity, (2) existing methods don't use causal edge direction for chain extraction, (3) we propose a model-free metric + calibration protocol, (4) causal chains outperform alternatives by >10%.

---

### §2 Background and Motivation

#### 2.1 Provenance Graphs for APT Detection (0.3 pages)
- What is a provenance graph: directed graph where nodes = system entities (processes, files, sockets), edges = causal system events (FORK, EXEC, READ, WRITE, SENDTO, etc.) with timestamps
- Why provenance is powerful for APT: captures complete causal history, adversary cannot tamper with kernel-level audit
- The scale problem: DARPA E3 has 268K nodes, 29.7M edges over 5 days

#### 2.2 The Detection Granularity Spectrum (0.3 pages)
- Spectrum visualization: Graph-level (Unicorn) → Snapshot-level (PROGRAPHER) → Window-level (KAIROS) → Entity-level (MAGIC, ThreaTrace) → Edge-level (EdgeTrace) → **Chain-level (Ours)**
- Each level answers a different question. Only chain-level answers "what is the attack narrative?"

#### 2.3 Why Existing Chain/Path Extraction Falls Short (0.5 pages)
- **Fixed windows (EagleEye)**: Events grouped by time, not causality. A window at time T contains causally-unrelated events from different processes
- **Random walks (Sentient)**: Can traverse edges in reverse causal direction — a process reading a file can be "linked" to a process that wrote it, regardless of temporal order
- **Temporal subgraphs (GET-AID)**: Time-based partitioning; events with similar timestamps may have zero causal relationship
- **Post-hoc reconstruction (SLOT, CAGE, EdgeTrace)**: Chain = f(anomalous nodes). If f has false negatives, the chain is incomplete
- **Rule-based extraction (SPARSE, Holmes)**: Requires expert knowledge, cannot detect novel attacks
- **The common failure**: None defines WHAT makes a chain good before extracting it

- **Figure 2**: Illustrative example on a small provenance subgraph. Show the same seed event, trace it with (a) fixed window, (b) random walk, (c) our causal trace. Highlight which events each method includes that are not causally connected to the attack.

- **Estimated length**: 1.1 pages

- **Key citations**: KAIROS, MAGIC, PROGRAPHER, EagleEye, Sentient, GET-AID, SPARSE, SLOT, CAGE, EdgeTrace, Unicorn, Holmes, ThreaTrace

---

### §3 Related Work

Organized by methodological family, not paper-by-paper.

#### 3.1 Provenance-Based Intrusion Detection (0.4 pages)
- **Graph-level / snapshot-level**: Unicorn (NDSS 2020) — graph sketching + evolutionary model. PROGRAPHER (USENIX Security 2023) — graph2vec + TextRCNN sequence prediction.
- **Entity-level / edge-level**: MAGIC (USENIX Security 2024) — GMAE + KNN. ThreaTrace (TIFS 2022) — GraphSAGE. FLASH (S&P 2024) — Word2Vec + GNN. EdgeTrace (TrustCom 2025) — masked GAE + causal path inference.
- **Window-level**: KAIROS (S&P 2024) — TGN + statistical thresholding.
- **Positioning**: All operate at granularities coarser than causal chains. None extracts or evaluates causally-coherent event sequences as first-class detection objects.

#### 3.2 Transformer on Provenance Graphs (0.3 pages)
- **Sequence-based**: EagleEye (eCrime 2024) — fixed windows + BERT-tiny + self-attention for interpretability. LogShield (2024) — RoBERTa on event sequences.
- **Graph-based**: Sentient (AAAI 2026) — Graph Transformer + Mamba-2 + Intent Analysis Module, random walk scenarios. GET-AID (ESORICS 2025) — TransformerConv with two-stage node/event attention, temporal subgraphs. PanThreat (2025) — Graph Transformer + Laplacian PE.
- **Positioning**: These demonstrate Transformers work on provenance. But their segmentation strategies (window/random-walk/subgraph) don't respect causal direction. Our contribution is NOT "Transformer on provenance" — it's the extraction metric that determines WHAT the Transformer processes.

#### 3.3 Attack Investigation and Path Reconstruction (0.3 pages)
- **Rule-based**: Holmes (S&P 2019), Poirot (CCS 2019), SLEUTH — expert-defined attack patterns for path scoring.
- **ML-based post-hoc**: SLOT (CCS 2025) — Graph RL + LPA clustering for chain construction. CAGE (Symmetry 2025) — GAT + Q-learning causal weights. SPARSE (2024) — Suspicious Flow Paths with semantic scoring.
- **Positioning**: Post-hoc methods first detect, then connect. Chain quality bounded by upstream recall. Our method detects directly on chains — the chain IS the detection unit. We use Holmes/SLEUTH as evaluation baselines: our metric applied to their output shows our chains are tighter.

#### 3.4 Causal Modeling in Security (0.2 pages)
- Causal inference for intrusion detection (FALCON, UAI 2025), causal graph learning for attack path identification
- **Positioning**: We are the first to formulate chain quality measurement as a model-free, OS-principle-grounded metric with unsupervised calibration. Prior causal security work either uses causal inference for detection directly, or applies causal graph models — none defines a metric for evaluating extracted chains.

- **Estimated length**: 1.2 pages
- **Key citations**: ~25 papers across 4 subtopics
- **Organization rule**: Synthesize by capability — what can each family DO, and what can't they do? The "can't do" = our contribution space.

---

### §4 System Design

#### 4.1 System Overview (0.3 pages)
- Architecture diagram (Figure 3): offline phase (Node Profiler, TGN pretraining, coherence calibration, Transformer training) → online phase (TGN → Chain Extractor → Transformer → eCDF detection → post-processing)
- Processing model: batch per-day (matching KAIROS/MAGIC evaluation), with micro-batch streaming design in §7
- Complexity budget table: what's reused, what's new, what's intentionally excluded

#### 4.2 Node Profiler: Global Graph Context (0.3 pages)
- 5 properties: IDF, Path Sensitivity, Degree Anomaly, Bridge Centrality, Community ID
- Precomputed offline, concatenated with KAIROS node2higvec → 24-dim per node
- **Not claimed as contribution** — feature engineering to enrich input representation

#### 4.3 TGN Seed Identification (0.3 pages)
- Reuse KAIROS pretrained TGN (GraphAttentionEmbedding + TGNMemory + LinkPredictor)
- Task: edge type prediction (self-supervised, benign-only)
- Seed trigger: reconstruction loss > 95th percentile of benign loss
- Why TGN: temporal memory tracks node state evolution — static features can't distinguish "nginx fork" from "bash fork"

#### 4.4 Causal Chain Extractor (1.2 pages) — **Core contribution**

**Algorithm** (pseudocode):
```
EXTRACT_CHAINS(G, seed s, params δ*, β*, λ*, B=20):
    chains ← {[s]}
    // Backward trace
    current ← {s}; depth ← 1
    while current ≠ ∅:
        prev ← ∅
        for each (u→v) in current:
            prev ← prev ∪ INCOMING_CAUSAL_EDGES(G, u, δ*)
        chains ← BRANCH_EXTEND(chains, prev, "backward")
        if |chains| > B: chains ← PRUNE(chains, Φ_bw, B)
        current ← prev; depth++
    // Forward trace (symmetric)
    // ... (same logic, forward direction)
    return chains
```

**Design rationale for each component**:
- INCOMING_CAUSAL_EDGES / OUTGOING_CAUSAL_EDGES: BFS along edge direction within δ* hops. Filter: only event types representing causal influence (EXEC, FORK, WRITE, SENDTO — not READ, CLOSE which are consequence, not cause).
- BRANCH_EXTEND: Cartesian product (each chain × each new edge). Maintains temporal ordering within each chain.
- PRUNE: Keep top-B chains by Φ_bw score.
- Termination: natural — when no more edges satisfy causal hop constraint δ*, chain is complete at causal boundary.

**Why this is novel vs. alternatives**:
- vs. BFS from KAIROS seeds: KAIROS doesn't do causal tracing — it does Louvain community detection on anomalous edges, which groups by graph proximity, not causality
- vs. random walk (Sentient): we enforce causal edge direction; random walks can traverse backwards
- vs. fixed window (EagleEye): we include only causally-connected events; windows include unrelated co-occurring events

#### 4.5 Causal Coherence Metric (1.0 pages) — **Primary contribution**

**Pairwise coherence φ** (3-case function):
- Case 1: identity-preserving bridge (d_i=0, node_type=subject): only graph distance penalty
- Case 2: stateful bridge (d_i=0, node_type=file/netflow): graph distance + temporal decay
- Case 3: indirect path (0 < d_i ≤ δ*): graph distance + temporal decay
- Case 4: d_i > δ*: φ = 0 (causal boundary)

**Why three cases**: Grounded in OS principles. Process = capability (PID+malloc guarantee identity). File/socket = shared resource (third party may overwrite). Not ad-hoc — provenance schema already encodes node types.

**Chain coherence Φ(C)**: Arithmetic mean of φ over consecutive pairs. Robust to audit log drops (geometric mean would collapse on one missing event).

**Branch-weighted coherence Φ_bw(C)** = Φ(C) · exp(-λ · BF(C)). BF = mean out-degree of non-terminal nodes. Named "Structural Sparsity Prior" — attack chains are structurally sparse (low branching).

**Calibration protocol** (pseudocode or algorithm block):
1. Extract chains from benign seeds with loose parameters (δ=10)
2. For each δ ∈ {1..10}: re-extract, compute mean Φ
3. Plot Φ-δ curve; δ* = elbow (max negative 2nd derivative)
4. Fix δ*; calibrate τ similarly via Φ-τ elbow
5. α* = 1/δ*, β* = 1/τ*
6. λ* = quantile-calibrated on benign BF distribution

**Why elbow exists** (Figure 4: Φ vs δ curve, annotated with elbow point):
- δ=1: only direct causal edges → high Φ but short chains (misses context)
- δ=2-3: captures cause-of-cause → Φ stays high, chains become complete
- δ=5+: noise — unrelated events forced into chains → Φ plateaus or drops
- Eventually all chains converge to init/PID 1 → Φ drops sharply

**Claim**: This protocol discovers the OS's "natural causal horizon" — the maximum meaningful causal distance for that specific system configuration.

#### 4.6 Autoregressive Transformer (0.8 pages)

**Why autoregressive, not MLM**: Provenance causality flows forward. MLM allows the model to look at future events to reconstruct past events — violates causal arrow. Autoregressive forces representation learning from historical events only.

**Input representation** (75-dim per event):
- src_node (24): node2higvec(16) + node_type(3) + IDF(1) + sensitivity(1) + deg_anomaly(1) + community(1) + bridge_cent(1)
- edge (20): edge_type_onehot(7) + time_sinusoidal(8) + d_embed(4) + bridge_flag(3) + was_seed(1)
- dst_node (24): same as src_node
- structure (3): is_branch + is_merge + depth_from_seed
- [BOS] learnable token (75-dim)
- **Φ is NOT included** — redundant with Δt, d_i, bridge_flag; would enable lazy learning

**Architecture**: 3-layer Transformer Encoder, d_model=128, nhead=4, d_ff=512, ~1.5M params. Linear(75→128) + Positional PE. Causal attention mask.

**Multi-task prediction head**: 7 prediction targets — (a) edge_type (7-class CE), (b) node_type_src (3-class CE), (c) node_type_dst (3-class CE), (d) node2higvec_src (cosine similarity), (e) node2higvec_dst (cosine similarity), (f) scalar node properties (MSE, normalized), (g) time_bucket (10-class log-spaced CE)

**Loss**: L_total = Σ L_k. Equal weights (all components naturally in [0, ~2.5]). EMA normalization fallback if one component dominates.

**Training**: Benign chains only (D2-D4). Adam, lr=1e-4. Min chain length ≥ 3. Max seq_len=64. Length-bucketed batching. Seed-centric truncation for overlong chains. ~1 GPU-hour.

#### 4.7 Detection via eCDF Thresholding (0.4 pages)

**Anomaly score construction**:
1. Run trained Transformer on benign validation chains
2. Collect per-component loss distributions (L_cat, L_cont, L_time)
3. Build eCDF for each component: raw loss → percentile
4. At inference: event anomaly = max(P_cat, P_cont, P_time)
5. Chain anomaly = mean_i event_anomaly(e_i)

**Why max, not sum**: A temporally extreme but semantically normal event (e.g., C2 beacon at unusual interval) would be diluted in sum. Max preserves the most sensitive anomaly dimension. Also enables interpretability: alerts tagged as "temporal anomaly" / "semantic anomaly" / "structural anomaly."

**Threshold**: flag when chain anomaly > 99.9th percentile of benign distribution.

- **Estimated total for §4**: 4.3 pages
- **Figure 3**: Architecture overview diagram
- **Figure 4**: Φ vs δ elbow curve, annotated
- **Figure 5**: 3-case φ function illustration on a small provenance subgraph

---

### §5 Metric Validation (Model-Free)

This section validates the Causal Coherence Metric BEFORE any Transformer training. All experiments in §5 are model-free.

#### 5.1 Experimental Setup (0.2 pages)
- DARPA TC E3: 268K nodes, 29.7M edges. Benign: April 2-4. Attack: April 6 (ground truth from MAGIC/ThreaTrace labels).
- Parameter calibration on April 2-3 benign data
- Metric evaluation on April 4 (held-out benign) and April 6 (attack)

#### 5.2 Benign vs Random Chain Discrimination (0.4 pages)
- **Claim**: Φ_bw separates causally-coherent chains from randomly-constructed chains
- **Setup**: Extract chains from TGN seeds on April 4 (benign). Generate random chains by sampling random edges and BFS without causal direction.
- **Metric**: AUC of Φ_bw as a classifier (no model trained)
- **Figure 6**: Histogram of Φ_bw for benign chains vs random chains
- **Expected**: AUC > 0.85, distributions clearly separated

#### 5.3 Elbow Detection Validation (0.3 pages)
- **Claim**: The Φ-δ curve exhibits a detectable elbow, and the elbow point produces optimal extraction
- **Setup**: Plot Φ vs δ for δ ∈ {1..10}. Compare chain quality (chain F1 proxy) at δ* vs δ=1 vs δ=10
- **Figure 7**: Φ vs δ curve with elbow annotation
- **Expected**: Clear elbow at δ≈2-3. Chains at δ* are more complete than δ=1, less noisy than δ=10

#### 5.4 Attack Chain Case Study (0.3 pages)
- **Claim**: Ground-truth attack chains exhibit high Φ_bw (attacks obey OS physics)
- **Setup**: Extract chains from TGN seeds on April 6. Inspect Φ_bw of chains containing ground-truth attack nodes
- **Table 1**: Φ_bw scores for top attack chains vs top benign chains
- **Expected**: Attack chains have comparable Φ_bw to benign (both are physically coherent), but differ in the Transformer's semantic anomaly score — confirming separation of concerns

#### 5.5 Comparison with Rule-Based Extraction (0.3 pages)
- **Claim**: Φ_bw evaluates Holmes/SLEUTH output objectively, showing our extraction is tighter
- **Setup**: Apply Holmes-style rule-based forward/backward trace on the same seeds. Compute Φ_bw of Holmes chains vs our chains
- **Table 2**: Mean Φ_bw ± std for Ours vs Holmes vs Random
- **Expected**: Φ_bw(Ours) > Φ_bw(Holmes) > Φ_bw(Random)

- **Estimated total for §5**: 1.5 pages

---

### §6 End-to-End Evaluation

#### 6.1 Main Results: Chain-Level APT Detection (0.8 pages)
- **Setup**: Full pipeline. Train Transformer on April 2-4 benign chains. Test on April 6. Compare against 7 baselines. All methods use the SAME Transformer architecture — only the chain/segment extraction strategy varies.
- **Baselines**: (1) EagleEye fixed window, (2) Sentient random walk, (3) GET-AID temporal subgraph, (4) SPARSE rule-based path, (5) KAIROS window-level, (6) MAGIC entity-level, (7) SLOT post-hoc chain
- **Metrics**: Chain-level Precision, Recall, F1 (primary). AUC. Investigation Cost = #edges analyst must examine to find all attack edges.
- **Figure 8**: Bar chart — chain-level F1 across all methods
- **Table 3**: Full metrics table (P/R/F1/AUC/InvestigationCost) for all methods
- **Expected**: >10% absolute F1 improvement. >50× investigation cost reduction vs KAIROS.

#### 6.2 Cross-Dataset Generalization (0.5 pages)
- **Setup**: Same pipeline on E5 (THEIA/Trace). Recalibrate Φ_bw parameters via elbow detection (protocol unchanged, parameters auto-adapt). Retrain TGN + Transformer on E5 benign data.
- **Key question**: Does the calibration protocol discover different δ* for different OS configurations?
- **Figure 9**: Side-by-side elbow curves for E3 vs E5
- **Table 4**: δ*, τ* discovered on E3 vs E5; chain-level F1 on both datasets
- **Expected**: δ* differs between E3 and E5 (proving adaptivity), but chain-level F1 is consistently high on both (proving generality)

#### 6.3 Ablation Study (0.6 pages)
6 ablations, ordered by expected impact:
1. **Remove causal direction**: undirected BFS (expected: largest drop — proves causal direction matters)
2. **Remove TGN temporal memory**: static edge features for seed selection (expected: moderate drop — proves TGN value)
3. **Remove Branch-Weighted Coherence**: use Φ only, no branching penalty (expected: precision drop from Firefox/compilation false positives)
4. **Remove Node Profiler**: KAIROS raw features only (expected: moderate drop)
5. **Remove sinusoidal time encoding**: scalar Δt (expected: minor drop — but proves multi-scale timing value)
6. **Replace Transformer with LSTM → MLP** (expected: LSTM close, MLP worse — justifies Transformer choice)

- **Figure 10**: Ablation bar chart — F1 change per ablation
- **Table 5**: Per-ablation metrics

#### 6.4 Efficiency Analysis (0.3 pages)
- Per-component latency breakdown
- Memory: graph buffer bounded by time window (not uptime)
- Throughput: 144× real-time (10 min for 24h of events)
- Compared to KAIROS: <20% additional overhead

- **Estimated total for §6**: 2.2 pages

---

### §7 Discussion

#### 7.1 Deployment Model (0.3 pages)
- Classify as Asynchronous Out-of-Band (OOB) Detector — not inline real-time blocker
- Micro-batch architecture: 60s tumbling window, ~2s processing latency
- Three defense assertions: decoupled control plane, linear state scalability, throughput-latency tradeoff
- Evaluate in batch mode (matching baselines); streaming design in this section

#### 7.2 Limitations (0.3 pages)
- Single attack type in E3 (nginx exploit chain) → E5 provides diversity, but still DARPA-specific
- Assumes benign training data is attack-free (standard assumption in provenance IDS — also made by KAIROS, MAGIC, Unicorn)
- Structural Sparsity Prior may miss highly-branching APT campaigns (e.g., ransomware fan-out). Acknowledged: prior works for low-branching APTs; fan-out attacks are a different detection paradigm
- No formal theorem for elbow existence (empirically validated; MDL approach is future work)

#### 7.3 Future Work (0.2 pages)
- Extend to streaming evaluation with live audit log integration
- Formal causal discovery framework (do-calculus for provenance chain extraction)
- Multi-host provenance integration (cross-machine attack chains)

- **Estimated total for §7**: 0.8 pages

---

### §8 Conclusion

- **Restatement**: We presented Causal Coherence Metric (Φ_bw) — a model-free, OS-principle-grounded metric for quantifying causal chain integrity in provenance graphs — and an unsupervised calibration protocol that discovers the natural causal horizon of an OS from benign data alone. Chains extracted under Φ_bw guidance, validated by a self-supervised autoregressive Transformer, outperform all existing chain/segment extraction strategies.

- **Limitations**: [condensed from §7.2]

- **Closing statement**: "By shifting the detection paradigm from 'where/when is the anomaly' to 'which causal sequence is the attack,' our method provides SOC analysts with directly actionable attack narratives rather than lists of suspicious entities or time windows."

- **Estimated length**: 0.4 pages

---

## Figure Plan

| ID | Type | Description | Data Source | Priority |
|----|------|-------------|-------------|----------|
| Fig 1 | 双面板 | Hero: (左) provenance 子图实例—因果链(红) vs 固定窗口(蓝); (右) 所有方法链级 F1 柱状图 | 手工 + experiment | HIGH |
| Fig 2 | 示意图 | 同一种子, 三种提取策略对比: 固定窗口 / 随机游走 / 因果追溯 | 手工 | HIGH |
| Fig 3 | 架构图 | 系统流水线: offline + online 两阶段, 5 个模块 | 手工 | HIGH |
| Fig 4 | 曲线图 | Φ vs δ elbow 曲线, 标注 δ* | experiment (§5.3) | HIGH |
| Fig 5 | 示意图 | 3-case φ 函数: identity-preserving bridge / stateful bridge / indirect path | 手工 | MEDIUM |
| Fig 6 | 直方图 | Φ_bw 分布: benign chains vs random chains | experiment (§5.2) | HIGH |
| Fig 7 | 曲线图 | Φ vs τ elbow 曲线 (补充 Fig 4) | experiment (§5.3) | MEDIUM |
| Fig 8 | 柱状图 | 主实验结果: 所有方法链级 F1 | experiment (§6.1) | HIGH |
| Fig 9 | 双曲线 | E3 vs E5 elbow 对比 (证明跨 OS 适配) | experiment (§6.2) | HIGH |
| Fig 10 | 柱状图 | Ablation 结果: 6 项 F1 变化 | experiment (§6.3) | HIGH |
| Table 1 | 表格 | 攻击链 vs 良性链 Φ_bw 分数 | experiment (§5.4) | MEDIUM |
| Table 2 | 表格 | Φ_bw(Ours) vs Φ_bw(Holmes) vs Φ_bw(Random) | experiment (§5.5) | MEDIUM |
| Table 3 | 表格 | 主实验结果: 全指标 × 全方法 | experiment (§6.1) | HIGH |
| Table 4 | 表格 | E3 vs E5 校准参数 + F1 | experiment (§6.2) | HIGH |
| Table 5 | 表格 | Ablation 全指标 | experiment (§6.3) | HIGH |

---

## Citation Plan

### §1 Introduction
KAIROS (S&P 2024), MAGIC (USENIX Security 2024), EagleEye (eCrime 2024), Sentient (AAAI 2026), GET-AID (ESORICS 2025)

### §2 Background and Motivation
KAIROS, MAGIC, PROGRAPHER (USENIX Security 2023), EagleEye, Sentient, GET-AID, SPARSE (2024), SLOT (CCS 2025), CAGE (Symmetry 2025), EdgeTrace (TrustCom 2025), Unicorn (NDSS 2020), Holmes (S&P 2019), ThreaTrace (TIFS 2022)

### §3 Related Work
~25 papers across 4 subtopics. Key additions beyond §2: FLASH (S&P 2024), LogShield (2024), PanThreat (2025), Poirot (CCS 2019), SLEUTH, FALCON (UAI 2025), DeepLog (CCS 2017), PROGRAPHER (USENIX Security 2023)

### §4 System Design
KAIROS (TGN backbone), MAGIC (Node Profiler inspiration), Pearl SCM (causal sufficiency grounding), PyTorch / PyG (implementation)

### §5 Metric Validation
Same as §2 + Holmes, SLEUTH

### §6 Evaluation
All baselines from Claims-Evidence Matrix

### §7 Discussion
KAIROS (throughput baseline), MAGIC (deployment model reference)

---

## Reviewer Feedback
[Codex MCP unavailable — skipped. Noted for future iteration.]

---

## Next Steps
- [ ] `/paper-figure` to generate all figures (begin with Fig 1, Fig 3, Fig 4)
- [ ] Run experiments to fill Claims-Evidence Matrix (BP1-BP3 timeline)
- [ ] `/paper-write` to draft LaTeX sections
- [ ] Re-run `/paper-plan` after experiments to fill `[X]` values in Abstract and claims
- [ ] `/auto-review-loop` to iterate on paper quality
