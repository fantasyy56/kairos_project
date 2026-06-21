I need your help constructing a complete, closed-loop research story for both paper writing and oral presentations. The goal is to explain: (1) what three key baselines did, (2) what fundamental gap remains, (3) how our method fills that gap, and (4) why this matters.

## Context: Our Method

We propose **Causal-Edge-Aware Temporal Chain Extraction** for provenance-graph-based APT detection.

**Core contribution**: A model-free Causal Coherence Metric (Φ_bw) that quantifies the causal structural integrity of event chains extracted from provenance graphs, plus an unsupervised calibration protocol (elbow detection) that discovers the natural causal horizon of an OS from benign data alone.

**Pipeline**: TGN (reused from KAIROS for seed identification) → Causal Chain Extractor (novel, bidirectional causal tracing pruned by Φ_bw) → Autoregressive Transformer (self-supervised, train on benign chains only, multi-task next-event prediction) → eCDF thresholding → attack paths.

**Key design decisions**:
- 3-case φ function: identity-preserving bridge (process, no time penalty) vs stateful bridge (file/socket, time penalty applies) vs indirect path
- Branch-Weighted Coherence: Φ_bw = Φ · exp(-λ·BF) — Structural Sparsity Prior (attack chains have low branching, benign processes like Firefox have power-law high branching)
- Autoregressive not MLM (causal arrow of time)
- Trained only on benign data (no attack labels needed)
- 75-dim per-event features including sinusoidal time encoding and learned graph distance embedding
- Component-wise eCDF anomaly scoring (max over temporal/semantic/structural anomaly dimensions)

## The Three Key Baselines

### Baseline 1: KAIROS (S&P 2024)
- **Technical DNA**: Temporal Graph Network (TGN) — TransformerConv + temporal memory module
- **What it does**: Trains TGN to predict edge types on benign data. At test time, edges with high reconstruction loss are anomalous. Groups anomalous edges into 15-minute time windows. Uses statistical threshold (mean + 1.5σ) + IDF filtering + hardcoded keyword blacklist. Louvain community detection for visualization.
- **Thinking path**: "If the model learns what normal event transitions look like, then events that break the learned pattern are suspicious. Aggregate them in time windows to find attack periods."
- **Key limitation**: Answers "which 15-minute window has the attack?" — not "which causal event sequence is the attack?" The detection mechanism (1.5σ, keyword blacklist) is non-learned, hand-tuned. The TGN is good but the detection side is weak.
- **What we inherit**: TGN backbone for seed identification.

### Baseline 2: MAGIC (USENIX Security 2024)
- **Technical DNA**: Graph Masked Auto-Encoder (GMAE) — GAT encoder + masked node feature reconstruction + edge reconstruction
- **What it does**: Masks 50% of node features, trains GAT to reconstruct them on benign provenance graphs. At test time, extracts node embeddings via encoder, uses KNN density estimation — nodes far from benign embedding clusters are anomalous.
- **Thinking path**: "Learn a compressed representation of normal system behavior on provenance graphs. Any entity whose representation deviates from the normal distribution is suspicious. No attack labels needed — pure self-supervision on benign data."
- **Key limitation**: Answers "which entity (node) is suspicious?" — not "how are they causally connected?" Uses static graph snapshots. No temporal modeling. No sequence modeling. Features are simple (node type one-hot only — no path hierarchy, no global graph statistics).
- **What we inherit**: Self-supervised training paradigm (train on benign only, detect via deviation from learned benign distribution).

### Baseline 3: EagleEye (eCrime 2024)
- **Technical DNA**: Encoder-only Transformer (BERT-tiny) on linearized provenance event sequences
- **What it does**: Extracts ~60 security features per event. Linearizes provenance events into fixed-size time windows. Feeds windowed sequences to a Transformer. [CLS] token classification (benign/malicious). Self-attention weights used for interpretability (highlighting which events are most suspicious).
- **Thinking path**: "Provenance events form a temporal sequence. A Transformer with self-attention can learn long-range dependencies between events far apart in the sequence. Fixed windows are a practical segmentation strategy."
- **Key limitation**: Fixed windows mix causally-unrelated events (Firefox page load + SSH login in the same window share no causal relationship). Cross-window causal dependencies are severed at window boundaries. No graph structure awareness — the Transformer sees a bag of co-occurring events, not a causal chain.
- **What we inherit**: Transformer on provenance event sequences — but we replace fixed windows with causal chains.

## The Gap: What All Three Miss

KAIROS has **temporal awareness** but operates at **window granularity** with **non-learned detection**.
MAGIC has **learned self-supervised detection** but operates on **static snapshots** at **entity granularity**.
EagleEye has **Transformer sequence modeling** but operates on **fixed windows** that **ignore causal structure**.

None of them answers: **"Which causally-connected sequence of events is the attack?"**

Each contributed a necessary piece:
- KAIROS → temporal graph modeling works on provenance
- MAGIC → self-supervised learning works for APT detection
- EagleEye → Transformers work on provenance event sequences

But the synthesis — combining temporal graph filtering, self-supervised sequence learning, AND causal structure awareness into one system — is missing. Our Causal Coherence Metric and causal chain extraction fill this synthesis gap.

## What I Need From You

1. **Story architecture**: Help me structure the narrative arc. What's the most compelling "before → after" framing? How to make the audience feel the gap before presenting our solution?

2. **Three-baseline comparison narrative**: How to explain why each baseline's approach is reasonable but insufficient, building toward why our synthesis is necessary? I want the audience to think "of course the next step is causal chain extraction" — not "why didn't they just post-process KAIROS's output?"

3. **One-sentence positioning**: A single sentence that captures what we do differently from ALL three baselines simultaneously. Something sharper than "we do chain-level detection."

4. **Analogy or mental model**: A memorable analogy that makes the difference intuitive. For example: "KAIROS tells you which building the crime happened in. MAGIC tells you which people were involved. EagleEye looks at surveillance footage in 5-minute chunks. We reconstruct the actual sequence of events — who did what, in what order, and why each step led to the next."

5. **The "why now" argument**: Why is 2026 the right time for this synthesis? Why wasn't this done before? (Hint: TGN temporal memory + GMAE self-supervision + Transformer on sequences all emerged in 2022-2024. Before that, the components didn't exist.)

6. **Presentation narrative flow**: If I have 5 minutes to present this to an audience (conference talk, advisor meeting), what's the optimal slide flow? What goes on each slide? What's the one takeaway I want the audience to remember?

7. **Weakness inoculation**: Where is the story most vulnerable to critique? What's the best way to preemptively address those critiques in the narrative itself?

Please be specific and actionable. I need concrete language I can use directly in slides and paper text.
