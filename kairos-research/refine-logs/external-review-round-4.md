# Gemini External Review — Round 4

**Date**: 2026-06-15
**Reviewer**: Gemini
**Focus**: Calibration regularizer + SSH daemon problem

## Key Approvals
- Branch-Weighted Coherence approved → call it "Structural Sparsity Prior"
- Elbow method sufficient — skip MDL
- Predicted elbow at δ≈2-3 for DARPA E3
- Cross-dataset δ* variation is a FEATURE (proves adaptivity), not a bug

## New Challenge
How to handle long-running dormant processes (SSH daemon) so τ doesn't sever legitimate causal links?
