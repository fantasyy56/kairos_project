# Gemini External Review — Round 1

**Date**: 2026-06-15
**Reviewer**: Gemini (via manual-review MCP)
**Score**: 5/10

## Summary
Logically sound pipeline but relies on outdated datasets, a fatal data augmentation strategy, and mismatched theoretical claims. Borderline for Big-4, more suitable for CCS/NDSS.

## Key Critiques

| # | Issue | Severity |
|---|-------|----------|
| 1 | 10→10,000 augmentation on DARPA E3 is a **fatal flaw** — Transformer will memorize augmentation, not attacks. DARPA E3 already saturated (>95% F1 baselines) | CRITICAL |
| 2 | Causal Representation Learning claims are **overreach** — method is heuristic graph traversal + temporal decay, not causal discovery/IRM | CRITICAL |
| 3 | Contribution reads as **KAIROS + SLEUTH/Holmes + Transformer** (pipeline engineering, not fundamental breakthrough) | HIGH |
| 4 | Need modern dataset: OpTC, DARPA ENGAGE, or custom Caldera testbed | HIGH |
| 5 | Transformer should be self-supervised on benign data, not supervised on augmented 10 samples | HIGH |
| 6 | Formal theorem not needed; empirical proof of causal coherence metric is sufficient | MEDIUM |

## Recommended Fixes
1. Frame Transformer as anomaly detector trained on benign data only (self-supervised/reconstruction)
2. Upgrade to OpTC / DARPA ENGAGE / Caldera
3. Rename narrative: drop "Causal Representation Learning" → "Context-Aware Temporal Provenance Tracking"
4. Emphasize model-free causal coherence metric as primary scientific contribution
5. Prove empirically that coherence metric correlates with true attack chains

## How to get from 5/10 to 8.5/10
1. Self-supervised on benign, test on real attacks (no augmentation)
2. Modern dataset
3. Honest narrative framing
4. Strong ablation on causal coherence metric

## Final Question from Reviewer
How were you planning to generate synthetic positive samples without introducing identifiable statistical artifacts?
