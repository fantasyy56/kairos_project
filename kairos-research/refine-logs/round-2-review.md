# Round 2 Review (Re-evaluation)

## Dimension Scores

| Dimension | Round 1 | Round 2 | Δ | Weight |
|-----------|---------|---------|---|--------|
| Problem Fidelity | 8 | 9 | +1 | 15% |
| Method Specificity | 6 | 8 | +2 | 25% |
| Contribution Quality | 5 | 7.5 | +2.5 | 25% |
| Frontier Leverage | 6 | 7.5 | +1.5 | 15% |
| Feasibility | 7 | 8 | +1 | 10% |
| Validation Focus | 6 | 8 | +2 | 5% |
| Venue Readiness | 5 | 7 | +2 | 5% |
| **OVERALL** | **6.1** | **7.9** | **+1.8** | — |

## Verdict: REVISE (improved from 6.1 → 7.9, but not yet at 9)

---

## What Improved

1. **Contribution reframing (+2.5)**: The shift from "causal chain as detection unit" (too close to SPARSE/EdgeTrace) to "TGN-guided temporal causal chain extraction algorithm with SCM grounding" is the biggest improvement. The paper now has a clear algorithmic contribution that no existing work provides.

2. **Method concreteness (+2)**: Pseudocode, defined parameters, termination conditions, and quantified data augmentation make the proposal implementable. An engineer could start coding from this document.

3. **Validation design (+2)**: Cross-dataset experiment promoted to main paper. Investigation cost metric defined. Ablation suite is comprehensive and targeted.

4. **Frontier leverage (+1.5)**: SCM grounding connects provenance graph analysis to causal inference — a genuine modernization that avoids buzzword-chasing.

5. **Venue readiness (+2)**: The paper is no longer "yet another Transformer on provenance" but "causal chain extraction from temporal provenance graphs." This is a less crowded space.

## Remaining Gaps (preventing 9+)

### Gap 1: No theoretical guarantee for chain extraction
The algorithm is well-specified but lacks a formal statement about *why* causal tracing should recover attack-relevant edges. A theorem (even a weak one) would make this a much stronger contribution.

**Suggested addition**: Prove that under a causal Markov condition on the provenance graph, the extracted chain is a superset of the true attack causal chain with high probability. Or prove that temporal decay weighting preserves the causal ordering property.

### Gap 2: Chain quality metric undefined
The Transformer validates chains, but there's no *intrinsic* metric for chain quality independent of the downstream task. Without this, the Chain Extractor's quality is only measured by the Transformer's performance — circular if both are jointly designed.

**Suggested addition**: Define a "causal coherence" metric: the fraction of consecutive edge pairs in the chain that have a genuine causal relation (measured by mutual information or Granger causality in the provenance event stream). This can be estimated on benign data and used to calibrate the algorithm's parameters.

### Gap 3: Venue readiness gated on experimental results
Even with the strongest proposal, CCF-A venues require experimental validation. The score can't exceed ~7.5 without results. This is expected at the pre-experiment stage.

**Note**: This gap cannot be closed in the refinement loop. It requires running experiments.

## Simplification Opportunities (Round 2)

1. **Drop the "supporting contribution" framing entirely.** The paper has one contribution: causal chain extraction. Node Profiler and Transformer are tools. A one-contribution paper is stronger than a paper trying to have two contributions.

2. **Consider whether the SCM grounding needs the full Pearl framework.** A simpler causal sufficiency assumption may suffice for provenance graphs where all common causes are observed (by construction). Don't over-formalize.

## Modernization Opportunities (Round 2)

1. **Connect to the broader "causal representation learning" literature.** Schölkopf et al.'s work on causal representation learning provides a natural framework for why causally-extracted features (chains) should generalize better than correlation-based features (windows, random walks). This gives a theoretical motivation for why causal chain extraction should work across datasets.

## Drift Warning: NONE

The refinement stays true to the problem anchor. No drift detected.

## Verdict Rule Application

READY requires: overall >= 9, no drift, one focused contribution, no complexity bloat.
Current: 7.9, no drift, focused contribution, minimal complexity.

→ REVISE. The remaining 1.1 points are partly gated on experimental validation (cannot be closed pre-experiment) and partly addressable through theoretical strengthening (Gap 1, Gap 2).

**Recommendation**: Proceed to implementation with the current proposal. The theoretical gaps (1, 2) can be addressed during/after experiments. The fundamental architecture and contribution framing are now solid.
