n < 3 dropped. [BOS] token added. Token-level mean loss. Now for inference latency.

## Honest Assessment of Deployment Scope

Let me be upfront: this paper's primary contribution is the extraction + discrimination methodology, not a production streaming system. Both KAIROS and MAGIC evaluate in batch/day mode on DARPA data. I'll design for streaming feasibility but evaluate in batch mode (matching baselines). A streaming deployment is a natural follow-up paper.

That said, the latency question matters for the paper's "practicality" story. Here's the design.

## Latency Breakdown (Per-Day Processing)

Processing DARPA E3 (April 6, ~5M events in 24h = ~58 events/sec average, bursts to ~1000/sec):

### Component Timing (estimated from KAIROS benchmarks)

| Component | Throughput | Per-Day Cost |
|-----------|-----------|-------------|
| TGN inference | ~11K edges/sec | ~8 min |
| Chain extraction (Top-100 seeds) | ~100 seeds × ~100 graph ops each | ~2 min (CPU) |
| Transformer inference | ~50 chains × 64 tokens × 1.5M params | ~1 sec (GPU) |
| eCDF thresholding | ~50 scalar comparisons | negligible |
| **Total** | | **~10 min per day** |

The bottleneck is TGN inference (reused from KAIROS). Chain extraction and Transformer add minimal overhead.

## Streaming Design (For Paper's "Deployment Considerations" Section)

### Micro-Batch Window Processing

Rather than true event-by-event streaming, use a tumbling micro-batch window:

```
Window size: 60 seconds (configurable)
Processing cycle:
  1. Accumulate events in sliding graph buffer (τ = 15 min retention)
  2. Every 60s: run TGN on new events → update memory state
  3. If any event exceeds TGN loss threshold: extract chain, run Transformer
  4. Output: chain score within ~2 seconds of window close
```

**Why this works**: 60-second detection latency is operationally acceptable for APT (attacks unfold over hours/days). The 15-minute graph retention aligns with KAIROS's window size — chains spanning longer than 15 minutes are handled by our soft temporal decay (not hard threshold), so they're still captured at lower coherence.

### Incremental Graph Maintenance

The provenance graph buffer:
- Nodes: hash-indexed by (node_type, node_label) for O(1) lookup
- Edges: stored in adjacency lists with timestamps
- Expiration: edges older than τ_max (configurable, default 15 min) are lazily evicted
- Memory: ~1-5M edges in buffer → ~200MB-1GB (fits in RAM)

### Seed Prioritization

Only extract chains when TGN loss exceeds a dynamic threshold (95th percentile of recent benign loss). This avoids extraction for the vast majority of benign events. On a typical day, 100-500 seeds trigger extraction out of 5M events (0.01%).

### Parallel Chain Extraction

Chain extraction for different seeds is embarrassingly parallel — no shared state mutation during traversal (read-only graph queries). Can run on multiple CPU threads.

## What the Paper Claims vs What It Doesn't

**Claims**:
- Our method adds <20% overhead to KAIROS's existing TGN pipeline
- Per-day processing completes in ~10 minutes on a single GPU + CPU
- 60-second detection latency is achievable with micro-batch windows

**Does NOT claim**:
- Sub-second per-event streaming latency
- Production deployment readiness
- Kernel-level integration (no eBPF/LSM hook implementation)

## Question

The micro-batch approach means there's a 60-second gap between "attack event occurs" and "chain score computed." For APT detection this is fine, but it means the system is "near-real-time" rather than "real-time." Should I:

1. **Frame as "near-real-time"** — honest, defensible, matches the 60s window?
2. **Frame as "batch processing with streaming capability"** — emphasizes the current evaluation mode while showing the path to streaming?
3. **Drop the streaming discussion entirely** — focus the paper purely on detection quality, leave deployment to future work?
