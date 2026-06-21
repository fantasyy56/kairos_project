# Gemini External Review — Round 3

**Date**: 2026-06-15
**Reviewer**: Gemini
**Focus**: Mathematical definition of Causal Coherence Metric

## Critical Issues Found

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| 1 | Calibration trivial maximization: α=0, β=0, δ=∞, τ=∞ produces Φ=1 always | FATAL | Add regularizer or use elbow method |
| 2 | False property claim: arithmetic mean Φ ≠ 0 when one pair breaks | MATH ERROR | Keep arithmetic mean (robust to missing events), delete false claim |

## Key Design Decisions

1. **Keep arithmetic mean** — robust to single audit log drops. Don't use geometric mean.
2. **No asymmetric event-type weights** — hyperparameter explosion. Let Transformer learn semantics. Metric measures physical causality only.
3. **10 attack chains = case studies, not statistical evidence** — stats come from benign vs random comparison.
4. **Primary contribution = calibration PROTOCOL** — discovering "natural causal horizon" of an OS from its benign resting state. This is the systems-level breakthrough.
5. **Causal Explosion problem**: high-branching benign processes (compilers, zip) will flood extractor. Need out-degree penalty.
6. **Keep metric separate from Transformer** — don't feed coherence as input feature. Separation of concerns.

## New Question from Gemini
What regularizer makes sense for DARPA E3 data given typical benign process branching patterns?
