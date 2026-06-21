# Gemini External Review — Round 2

**Date**: 2026-06-15
**Reviewer**: Gemini (via manual-review MCP)
**Score**: 5/10 → 7.5/10 (+2.5)

## What Changed
- Accepted: self-supervised benign-only training paradigm
- Accepted: narrative reframe away from Causal ML
- Accepted: causal coherence metric as primary contribution
- Pushback accepted: chain-level detection on E3 is defensible IF supplemented by E5 + OpTC

## Key Recommendations

| # | Recommendation | Action |
|---|---------------|--------|
| 1 | Use **autoregressive** (next-event prediction) not MLM for Transformer training | Causal arrow of time — MLM lets model cheat forward in time |
| 2 | Make **Causal Coherence Metric** the primary contribution | Elevates from "pipeline" to "methodology" paper |
| 3 | **SLEUTH + Holmes are required baselines** | Apply your metric to their extracted chains; prove yours are "tighter" |
| 4 | **E3 + E5 + OpTC** as dataset trio | E3=unit test, E5=cross-environment, OpTC=modern noise stress-test |
| 5 | Timeline: **7 months to CCS 2026** is realistic with 4 breakpoints | See below |

## Score Breakdown
- 7.5/10 current (structural design is viable)
- +1.5 remaining: mathematical rigor of Causal Coherence Metric
- +1.0 remaining: E3 + E5 + OpTC empirical results without FPR explosion

## Timeline (Breakpoint Architecture)
- **BP1 (Jul 31)**: Finalize Coherence Metric math definition + validate on raw E3 data
- **BP2 (Sep 30)**: Complete autoregressive Transformer training on benign E3/E5
- **BP3 (Nov 30)**: Full pipeline integration, chain-level AUC/F1 across E3/E5/OpTC, vs Holmes
- **BP4 (Dec–mid Jan)**: Paper writing, ablations, 2-week buffer before deadline

## Remaining Fatal Flaws
None. Remaining risk is execution risk, not conceptual risk.
