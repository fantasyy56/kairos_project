Excellent observation on the File Node Bridge vulnerability. Let me address it directly.

## The Fix: Classify Bridging Nodes by Mutability

You're right that not all d_i = 0 bridges are equal. The key distinction is whether the bridging node is **identity-preserving** (a process) or **stateful** (a file/socket that can be modified by third parties).

### Node Type Classification

| Bridge Type | Node Types | Causal Guarantee | Time Penalty |
|---|---|---|---|
| **Identity-preserving** | subject (process) | Absolute — PID guarantees identity | β ≈ 0 |
| **Stateful** | file, netflow (socket), pipe | Probabilistic — third party may overwrite | Apply β |

The refined pairwise coherence:

```
φ(e_i, e_{i+1}) = {
    exp(-α · d_i)                              if d_i = 0 AND bridge is identity-preserving
    exp(-α · d_i) · exp(-β · Δt_i)            if d_i = 0 AND bridge is stateful
    exp(-α · d_i) · exp(-β · Δt_i)            if 0 < d_i ≤ δ
    0                                           if d_i > δ
}
```

### Why This Is Not Ad-Hoc

This classification maps to a fundamental OS principle. A process is a **capability** — its PID and memory space remain under its exclusive control until termination. No third party can "write into" a running process. A file is a **shared resource** — any process with appropriate permissions can modify it.

The provenance graph data model already encodes this: node types (subject, file, netflow) are in the schema. No additional labeling needed.

### Intervening Write Detection: Optional, Not Required

You asked about checking for intervening write events. I propose a pragmatic stance:

**Do NOT check for intervening writes during chain extraction.** It's expensive (requires temporal range queries for every file bridge) and the β temporal decay already handles the common case — large time gaps → low coherence. The case where Process C writes File X exactly between Process A's write and Process B's read, creating a false causal link that β doesn't catch because Δt is small, is:

1. Rare in practice (requires three processes interacting with the same file within a tight window)
2. Self-limiting — such files tend to be high-traffic (/tmp, logs) and their events will be pruned by the Structural Sparsity Prior (high branching factor BF → low Φ_bw)

If a reviewer pushes back: we can add an optional lightweight check — when d_i = 0 through a file bridge AND Φ_bw ranks this chain in the top-K, verify that no intervening WRITE exists. This is a post-extraction validation, not a per-edge cost. But I believe this is unnecessary for the initial submission.

### Updated Causal Coherence Metric (Complete)

Putting it all together after 5 rounds of workshopping:

```
Given: provenance graph G, chain C = [e₁, ..., e_n]

For consecutive (e_i, e_{i+1}):
  d_i  = shortest directed path length from dst(e_i) to src(e_{i+1})
  Δt_i = t_{i+1} - t_i
  bridge_type = node_type(dst(e_i)) = node_type(src(e_{i+1}))  [for d_i=0]

  φ(e_i, e_{i+1}) = {
    exp(-α · d_i)                              d_i=0, identity-preserving bridge (subject)
    exp(-α · d_i) · exp(-β · Δt_i)            d_i=0, stateful bridge (file, netflow)
    exp(-α · d_i) · exp(-β · Δt_i)            d_i ∈ (0, δ]
    0                                           d_i > δ
  }

Chain coherence:     Φ(C) = mean_i φ(e_i, e_{i+1})
Branch penalty:      Φ_bw(C) = Φ(C) · exp(-λ · BF(C))

Calibration (model-free, on benign data):
  δ* = elbow of mean Φ vs δ curve
  β* = 1/τ* where τ* = elbow of mean Φ vs τ curve
  α* = 1/δ*
  λ* = quantile-calibrated on benign branching distribution
```

## Question

With the identity-preserving vs stateful bridge distinction added, the pairwise coherence function now has three cases. Is this still clean enough for a CCS/NDSS paper, or should we simplify back to two cases (losing the node-type distinction) and handle the File Bridge vulnerability differently — for example, by making the extraction algorithm avoid stateful bridges entirely (only follow edges through process nodes, never through files)?
