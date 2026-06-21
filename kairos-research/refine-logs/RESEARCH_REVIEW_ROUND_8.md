φ excluded from input. Bucketed time prediction. Now for the loss balancing.

## Multi-Task Autoregressive Prediction Head

At each step i, given events [e₁, ..., e_i], predict e_{i+1}:

```
Prediction targets for e_{i+1}:

1. Categorical:
   - edge_type (7-class CE)
   - node_type_src (3-class CE) — subject/file/netflow
   - node_type_dst (3-class CE)

2. Continuous (node representations):
   - node2higvec_src (16-dim) — hierarchical path hash, values in [-1, 1]
   - node2higvec_dst (16-dim)
   - IDF_src, IDF_dst (scalar, normalized to [0,1])
   - sensitivity_src, sensitivity_dst (scalar, [0,1])
   - degree_anomaly_src, degree_anomaly_dst (scalar, [0,1])

3. Temporal:
   - time_bucket (10-class CE) — log-spaced: [0-1ms, 1-10ms, 10-100ms, 100ms-1s, 
     1-10s, 10-60s, 1-10min, 10-60min, 1-24h, >24h]
```

**Observation**: With proper design, most loss components naturally fall in [0, ~2]:
- CE with ~10 classes: max ~log(10) ≈ 2.3
- Cosine similarity for 16-dim vectors: range [0, 2]
- MSE for [0,1]-normalized scalars: max 1.0

They're already in comparable ranges. But "comparable" is not "balanced."

## Proposed Solution: Cosine Similarity + Equalized Sum

### Continuous features → Cosine Similarity Loss

Replace MSE on node2higvec with:

```
L_nodevec = 1 - cos_sim(pred_nodevec, true_nodevec)
```

Range [0, 2]. Naturally normalized, no hyperparameter needed. MSE on 16-dim hash vectors is problematic because the hash space is sparse — most dimensions are zero, so MSE drives the model to predict zeros everywhere. Cosine similarity focuses on directional alignment, which is what we actually want (is this node embedding "pointing toward" the same semantic region?).

For scalar node properties (IDF, sensitivity, etc.): standard MSE, values normalized to [0,1]. L_scalars ∈ [0, 1].

### Categorical features → Standard CE

```
L_edge_type = CE(pred_edge_type, true_edge_type)  # 7 classes
L_node_type = CE(pred_node_type_src, true_src) + CE(pred_node_type_dst, true_dst)
```

### Time → CE on log-spaced buckets

```
L_time = CE(pred_time_bucket, true_time_bucket)  # 10 classes
```

### Total Loss: Equal-Weight Sum

```
L_total = L_edge_type + L_node_type + L_nodevec + L_scalars + L_time
```

**Why equal weights work here**: Every component is:
1. In the same numeric range ([0, ~2.5])
2. Measuring a different, non-redundant aspect of the event
3. All equally important for anomaly detection

No λ-hunting needed. No uncertainty weighting complexity.

**Fallback**: If one component dominates during training (e.g., L_nodevec consistently 10x larger than L_time), normalize each loss by its EMA over the last 100 batches:

```
L_total = Σ_k L_k / EMA(L_k)
```

This is simpler than GradNorm and more stable than uncertainty weighting for a model of this size.

### Anomaly Score at Inference

The multi-task loss IS the anomaly score:

```
anomaly_score(e_{i+1} | e_{1..i}) = L_total(predicted, actual)
```

A benign event that follows the learned distribution gets low total loss. An attack event that violates temporal expectations OR semantic patterns OR node properties gets high loss. The autoregressive framework naturally aggregates all dimensions of anomaly into a single interpretable scalar.

Chain-level anomaly score = mean per-event anomaly score over the chain.

## Question

Two concerns about this design:

1. **Catastrophic forgetting of temporal anomalies**: If the model learns to predict event types perfectly but time prediction remains noisy (because benign processes have inherently variable timing), L_time will always be high and may mask L_edge_type anomalies. Should time prediction use a SEPARATE head with detached gradients (not backpropagating into the shared Transformer body), so temporal pattern learning doesn't interfere with semantic pattern learning?

2. **Unsupervised threshold**: With the multi-task loss as anomaly score, how do we set the threshold for "this chain is anomalous"? Option (a): fit a Gaussian/EVT distribution to benign chain scores and flag chains above some quantile (like MAGIC's KNN approach). Option (b): train a small MLP on top of per-event loss vectors to classify the chain (requires positive labels → back to the augmentation problem). Option (c): something else?
