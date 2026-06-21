The 3-case formulation stays. Now for the Transformer input representation.

## Current Feature Vector (60-dim, per event)

```
[src_node (24) | edge (9) | dst_node (24) | structure (3)]
                                  ↑                    ↑
                          time_delta_from_prev    is_branch_point
                          was_seed                is_merge_point
                                                  depth_from_seed
```

Where:
- src/dst_node (24): [node2higvec(16) | node_type(3) | IDF(1) | sensitivity(1) | degree_anomaly(1) | community_id(1) | bridge_centrality(1)]
- edge (9): [edge_type_onehot(7) | time_delta_from_prev(1) | was_seed(1)]

Δt_i (time gap) is currently buried as a single scalar in the edge block. d_i (graph distance) is NOT in the feature vector at all.

## Proposed Revision: Explicit Temporal and Causal Encoding

### 1. Time Delta: Sinusoidal Encoding (Not Scalar)

A single scalar Δt cannot express the nonlinear relationship between time gaps and anomaly. A 100ms gap and a 101ms gap are functionally identical; a 1s gap and a 100s gap are categorically different.

Replace the scalar `time_delta_from_prev` with a sinusoidal time encoding (8 dims):

```
TE(Δt, 2j)   = sin(Δt / 10000^(2j/8))
TE(Δt, 2j+1) = cos(Δt / 10000^(2j/8))
```

This is identical in form to the Transformer's positional encoding, but applied to physical time instead of sequence position. The frequency spectrum allows the model to learn both fine-grained timing (milliseconds matter for FORK→EXEC) and coarse-grained timing (hours matter for slow APTs).

Why this works for autoregressive prediction: when predicting the next event, the model learns that after a FORK event at Δt=0.1s, an EXEC is expected within ~0.5s. If an EXEC appears after Δt=3600s, the model is surprised → high prediction error → anomaly.

### 2. Graph Distance: Bucketed Embedding

d_i ∈ {0, 1, 2, ..., δ} is a small integer. Learn a small embedding table:

```
d_embed = Embedding(d_i, dim=4)  # δ≤10, 4 dims sufficient
```

This allows the model to learn that "directly connected events" (d_i=0 via process) have different prediction patterns than "indirectly connected events" (d_i=2 via file → process → file).

### 3. Bridge Type Flag (New)

Per our 3-case φ function, the model should know whether consecutive events are bridged by an identity-preserving node or a stateful node:

```
bridge_flag ∈ {0 (identity-preserving), 1 (stateful), 2 (indirect, d_i > 0)}
```

One-hot encoded, 3 dims.

### Revised Feature Vector (75-dim)

```
[src_node (24) | edge_type (7) | time_sinusoidal (8) | d_embed (4) | bridge_flag (3) | was_seed (1) | dst_node (24) | structure (3) | Φ_weight (1)]
```

Wait — should Φ_weight (the pairwise coherence score φ) be included? We said "keep metric separate from Transformer." But φ is computed during extraction (model-free) and carries information about causal tightness. If Ω(attack chains) < Ω(benign chains) for slow APTs, the Transformer should know this.

I lean toward INCLUDING φ as a single scalar. It's not the coherence METRIC that's the problem — it's feeding the chain-level Φ as an attention bias, which would dominate the model. A per-event φ value is just another feature the model can use or ignore.

### 4. Sequence Position: Standard Sinusoidal PE

In addition to the time encoding (which encodes physical time gaps), standard positional encoding encodes order in the sequence. Both are needed:
- Positional PE: "this is the 3rd event in the chain"
- Time TE: "3.2 seconds elapsed since the 2nd event"

### 5. Input Embedding Layer

```
Raw features (75-dim) → Linear(75, 128) → + Positional PE(128) → Transformer input
Time TE is embedded INTO the features before the linear projection, not added after.
```

## Question

Two specific design questions:

1. **Φ_weight as input feature**: Include the pairwise coherence φ(e_i, e_{i+1}) as a scalar in the event feature vector, or keep the metric completely separate? The upside: the Transformer knows how causally tight each consecutive pair is. The downside: if φ values are systematically different between train (benign) and test (attack), the model may learn to rely on φ rather than learning event patterns. Your call?

2. **Predicting Δt vs predicting event type**: For the autoregressive training objective, should the model predict (a) only the next event's features, (b) the next event's features + the time gap Δt to that event, or (c) the next event's features + Δt + d_i? Option (b) seems natural — the model must learn WHEN as well as WHAT to expect. Option (c) adds graph distance prediction, which may be too hard (d_i depends on graph topology, not just sequence patterns).
