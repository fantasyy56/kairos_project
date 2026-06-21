# Gemini Response — Round 2: Theoretical Backbone + Introduction Structure + Evaluation Arc

**Date**: 2026-06-17
**Reviewer**: Gemini

## Front 1: "Why It Works" — 4-Layer Theoretical Backbone

Order: Layer 1 (Information) → Layer 2 (Causal Invariance) → Layer 3 (Signal Propagation) → Layer 4 (Attention Sparsity)

- **Layer 4 (NEW — Attention Sparsity/Capacity)**: Fixed 15-min window = 10,000 events → Transformer O(N²) collapses. Causal chains filter N down to K relevant events (K ≪ N), allowing 100% of Transformer capacity on attack trajectory.
- **Layer 2 tone**: Frame as "theoretically grounded hypothesis," not absolute guarantee (OS updates can change binary paths).
- **Single-sentence "why"**: "By extracting exact causal paths, our method structurally isolates the invariant mechanisms of an attack from the stochastic noise of concurrent system operations, maximizing both signal density and cross-environment generalization."

## Front 2: Introduction Restructured

- **¶4 ("Why Now") CUT from Intro** → move to Discussion. Compress into single transition clause at start of ¶5.
- **¶3 ordering**: MAGIC (static nodes, drops time) → EagleEye (flat text, drops structure) → KAIROS (severs causal links). Kicker: "The common failure is abstraction..."
- **¶5**: Start with one-sentence positioning. "Leveraging recent advances in temporal graph networks and sequence modeling..."
- **One-sentence contribution**: At BEGINNING of ¶5 (not ¶6).

## Front 3: Claim-Driven Evaluation Structure — CONFIRMED

Headers are claims, mapping to theoretical layers:
- 6.1: Φ_bw Quantifies True Causal Structure (Layer 1)
- 6.2: Unsupervised Calibration Discovers OS Causal Horizon
- 6.3: Causal Chains Maximize Discriminative Power (Main Results)
- 6.4: Causal Features are Invariant Across Environments (Layer 2 — knockout punch)
- 6.5: Component Ablation (Layer 4 proof)

"If a reviewer doubts Causal Invariance in the Introduction, Section 6.4 is waiting."
