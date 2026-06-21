# Refinement Report

**Problem**: APT detection on provenance graphs — from coarse time windows to fine-grained causal chains
**Initial Approach**: Two-stage TGN filter → Transformer discriminator on causal chains ("causal chain as detection unit")
**Date**: 2026-06-15
**Rounds**: 2 / 5
**Final Score**: 8.3 / 10
**Final Verdict**: REVISE (remaining gap gated on experimental validation)

## Output Files
- Review summary: `refine-logs/REVIEW_SUMMARY.md`
- Final proposal: `refine-logs/FINAL_PROPOSAL.md`
- Full refinement log: `refine-logs/round-1-refinement.md`, `refine-logs/round-2-refinement.md`

## Score Evolution

| Round | PF | MS | CQ | FL | Fe | VF | VR | Overall | Verdict |
|-------|----|----|----|----|----|----|----|---------|---------|
| 1 | 8 | 6 | 5 | 6 | 7 | 6 | 5 | 6.1 | REVISE |
| 2 | 9 | 8.5 | 8 | 8 | 8 | 8.5 | 7.5 | 8.3 | REVISE |

## Round-by-Round Review Record

| Round | Main Reviewer Concerns | What Was Changed | Result |
|-------|------------------------|------------------|--------|
| 1 | Contribution too close to SPARSE/EdgeTrace (5/10). Chain Extractor underspecified — no pseudocode (6/10). Node Profiler too weak for CCF-A. | Reframed dominant contribution from "causal chain as detection unit" to "causal chain extraction **algorithm**." Added SCM-grounded formal pseudocode. Downgraded Node Profiler to feature engineering. Quantified data augmentation. Promoted cross-dataset to main experiment. | Resolved (6.1 → 7.9) |
| 2 | No theoretical guarantee. No intrinsic chain quality metric. Supporting contribution causing sprawl. | Single contribution focus. Added causal coherence metric (model-free). Added causal sufficiency justification. Connected to causal representation learning for cross-dataset generalization prediction. | Partial (7.9 → 8.3). Remaining: formal theorem + experiments |

## Final Proposal Snapshot

- **One thesis**: Causal chain extraction algorithm for provenance graphs, validated by standard Transformer
- **One contribution**: Algorithm characterized by TGN-guided seeds, causal-direction tracing, temporal decay, coherence pruning, model-free calibration
- **Architecture**: 3 components — TGN (reused) → Chain Extractor (novel) → Transformer (standard)
- **Validation**: E3 primary + StreamSpot cross-dataset + 6 ablations
- **Baselines**: EagleEye, Sentient, GET-AID, SPARSE, KAIROS, MAGIC, PROGRAPHER, SLOT, UNICORN, ThreaTrace, DeepLog

## Method Evolution Highlights

1. **Most important focusing move**: From "Transformer on causal chains" (descriptive, incremental-sounding) to "causal chain extraction algorithm" (prescriptive, algorithmic contribution)
2. **Most important mechanism upgrade**: Causal coherence metric — provides model-free intrinsic validation, breaks circular dependency between Chain Extractor and Transformer
3. **Most important modernization**: Causal representation learning connection — gives theoretical motivation for cross-dataset generalization, distinguishes from purely empirical baseline comparisons

## Pushback / Drift Log

| Round | Reviewer Said | Author Response | Outcome |
|-------|---------------|-----------------|---------|
| 1 | "Causal chain as detection unit" too close to SPARSE Suspicious Flow Paths | Reframed to algorithmic contribution: causal chain **extraction**, not detection | Accepted |
| 1 | Node Profiler is weak supporting contribution | Downgraded to feature engineering; removed from contributions | Accepted |
| 1 | Need cross-dataset validation in main paper | Promoted StreamSpot to Experiment 2 | Accepted |
| 1 | Path Assembler is a named module that adds no value | Removed; replaced with simple post-processing rule | Accepted |
| 2 | Need theoretical guarantee | Added causal sufficiency justification + causal coherence metric | Partially accepted (formal theorem still pending) |

## Remaining Weaknesses

1. **No formal theorem**: The causal sufficiency justification is prose, not a theorem. A formal statement about chain recovery probability under the causal Markov condition would strengthen the contribution significantly. Deferred to paper-writing phase.

2. **Pre-experiment**: Score ceiling at ~8.3 without experimental results. CCF-A venues require empirical validation. This is expected and not a flaw in the proposal.

3. **Single attack type in E3**: The DARPA E3 dataset contains one attack scenario. Even with StreamSpot cross-validation, the diversity of attack types tested is limited. OpTC or THEIA would strengthen the evaluation.

## Next Steps

1. Implement Chain Extractor algorithm (pseudocode in Round 1 refinement)
2. Calibrate parameters (δ, λ, τ) using causal coherence on benign data
3. Train Transformer on extracted chains
4. Run full baseline comparison
5. Address theoretical gaps during paper writing
6. Consider `/experiment-plan` for detailed experiment roadmap
