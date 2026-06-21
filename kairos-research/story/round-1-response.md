# Gemini Response — Round 1: Research Story Construction

**Date**: 2026-06-17
**Reviewer**: Gemini

## 1. Story Architecture: "Evolutionary Convergence"

Framing: NOT "incremental improvement over KAIROS" but "resolution of a fundamental trade-off between Structural Depth and Temporal Fluency."

- **Before (Fragmented Slices)**: SOTA forces analysts to look at system behavior through fragmented dimensions — isolated temporal buckets, static topology maps, or disconnected sequences. The unbroken path of a multi-step APT remains invisible.
- **After (Causal Synthesis)**: Shift from aggregating anomalous entities to verifying continuous causal integrity.

## 2. Three-Baseline Narrative

Each baseline failed not due to poor engineering, but because their underlying DATA ABSTRACTIONS mismatched the APT lifecycle.

| Baseline | Abstraction | Answers | Drops |
|----------|------------|--------|-------|
| KAIROS (S&P 2024) | Coarse Time Windows | "When" anomalies happen | Causal graph topology |
| MAGIC (USENIX 2024) | Static Graph Nodes | "Who" is suspicious | Sequence of events |
| EagleEye (eCrime 2024) | Flat Linear Strings | "What language" of logs | Physical system structure |

**The audience should conclude each is reasonable but insufficient — puzzle pieces without assembly.**

## 3. One-Sentence Positioning

"While existing systems isolate anomalies within fragmented time windows, static graph entities, or flat linear log sequences, our method extracts the exact causal chains linking system events, validating both their structural integrity and chronological coherence through a single self-supervised model."

## 4. Analogy: Flight Path Replay

- KAIROS = legacy radar flagging which 15-min intervals had turbulence (won't trace the path)
- MAGIC = sensor flagging which waypoint markers look out of place (can't connect them across time)
- EagleEye = recording every radio transmission chronologically, mixing up three commercial airliners with the target
- Our Method = reconstructing the unbroken causal flight path of that single aircraft, pruning background noise

## 5. "Why Now" Argument

Before 2024: TGN temporal engines, GMAE unsupervised graph theory, and autoregressive sequence modeling existed in isolation. In 2026, we can synthesize them into a unified pipeline that traces, prunes, embeds, and predicts sequences over a dynamic graph space.

## 6. 6-Slide Presentation Flow

| Slide | Title | Content |
|-------|-------|---------|
| 1 | Restoring Causal Context to APT Detection | Paradigm shift visual: complex graph → clean causal path |
| 2 | The Dimensionality Mismatch | Table: each baseline has a red "Missing" block |
| 3 | Extracting the Causal Horizon | 3-case φ diagram + Φ_bw execution path |
| 4 | Verifying Causal Trajectories | 75-dim token → autoregressive prediction loop |
| 5 | Robust Performance without Attack Labels | PR curves + latency table vs baselines |
| 6 | Paradigm Restored | Flight Path Replay visual, "Context is the detection" |

Key takeaway: **"Context is the detection."**

## 7. Weakness Inoculation

- **Critique 1 ("3-case φ is ad-hoc")**: Map to immutable OS constraints (Capabilities/Process isolation vs Shared Resources/File state). Data-driven calibration via elbow detection eliminates human bias.
- **Critique 2 ("Benign-only training — what about complex benign updates?")**: Structural Sparsity Prior — high-branching benign behaviors get lowered coherence rank before reaching Transformer.
- **Critique 3 (Interactive performance)**: Pipeline simulator shows how window size, throughput, and TGN thresholds shift extraction costs under live streaming.
