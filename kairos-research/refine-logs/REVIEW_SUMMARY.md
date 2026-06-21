# Review Summary

**Problem**: APT detection coarse granularity → need fine-grained causal chain detection on provenance graphs
**Initial Approach**: Two-stage: TGN filter → Transformer discriminator on causal chains
**Date**: 2026-06-15
**Rounds**: 2 / 5
**Final Score**: 8.3 / 10
**Final Verdict**: REVISE (remaining gap gated on experimental validation)

## Problem Anchor
[See FINAL_PROPOSAL.md for full anchor]

## Round-by-Round Resolution Log

| Round | Main Reviewer Concerns | What Was Simplified / Modernized | Solved? | Remaining Risk |
|-------|------------------------|----------------------------------|---------|----------------|
| 1 | Contribution too close to SPARSE/EdgeTrace (5/10); Chain Extractor underspecified (6/10); Node Profiler too weak for CCF-A | Reframed contribution from "causal chain as detection unit" to "causal chain extraction **algorithm**"; Added formal pseudocode; Downgraded Node Profiler to feature engineering | Yes | Venue readiness still gated on experiments |
| 2 | Theoretical guarantee missing; No intrinsic chain quality metric; Supporting contribution causing sprawl | Single contribution focus; Added causal coherence metric; Added causal sufficiency justification; Connected to causal representation learning | Partial | Theoretical guarantee (formal proof) still needed for full score |

## Overall Evolution

- **More concrete**: Chain Extractor went from "seed → fwd/bwd trace" to a formally-specified algorithm with pseudocode, 4 defined parameters, and calibration protocol
- **More focused**: From "two contributions" (chain detection + Node Profiler) to one contribution (chain extraction algorithm). Transformer and Node Profiler are now tools, not contributions
- **More modern**: Connected to causal representation learning (Schölkopf); SCM-grounded termination conditions
- **Drift avoided**: All refinements stayed within the original problem anchor

## Final Status
- **Anchor status**: Preserved throughout
- **Focus status**: Tight — single algorithmic contribution
- **Modernity status**: Appropriately modern — causal inference grounding without buzzword-chasing
- **Strongest parts**: Causal coherence metric (model-free validation); formal Chain Extractor pseudocode; cross-dataset generalization prediction grounded in causal representation theory
- **Remaining weaknesses**: No formal theorem (gap 1); venue readiness limited by pre-experiment stage (gap 3)
