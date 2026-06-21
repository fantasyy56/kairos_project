Excellent catch on the trivial maximization trap. Here's my fix for the calibration objective, plus a concrete regularizer proposal grounded in DARPA E3 data characteristics.

## Fixed Calibration Objective

### Primary: Elbow Detection on the Φ-vs-δ Curve

The core insight: the "natural causal horizon" of an OS is the point where adding more causal hops stops improving coherence.

**Algorithm (revised)**:

```
1. Extract K chains from benign seeds using LOOSE bounds
   (δ=10, τ=300s, α=0.1, β=0.01) — intentionally generous

2. For each δ ∈ {1, 2, ..., 10}:
   - Re-extract chains from the SAME benign seeds
     (varying only δ, fixing τ=300s, α=0.1, β=0.01)
   - Compute mean Φ over all extracted chains
   - Compute |E_extracted| = total number of events in all chains

3. Plot mean Φ vs δ:
   - Φ increases with δ (more hops = more connectivity)
   - BUT: the marginal gain ΔΦ/Δδ diminishes
   - The ELBOW δ* = argmax_{δ} (ΔΦ(δ-1→δ) - ΔΦ(δ→δ+1))
     i.e., the point where the second derivative is most negative

4. Fix δ* at the elbow. Then calibrate τ similarly:
   - For each τ ∈ {10s, 30s, 60s, 120s, 300s}:
     - Extract with fixed δ*, varying τ
     - Plot Φ vs τ, find elbow τ*

5. α and β: With (δ*, τ*) fixed, these become redundant for thresholding
   (they only scale the value within [0,1]). Set α=1/δ*, β=1/τ*
   so that φ(e_i, e_{i+1}) decays naturally within the horizon.
```

This elbow method has no free lunch problem — it doesn't reward δ→∞ because once you pass the true causal horizon of the OS, adding more hops adds noise (unrelated events), not signal. The elbow naturally emerges.

### Secondary: Branching Factor Cap with Temporal Coherence Ranking

You asked what regularizer makes sense for DARPA E3 specifically.

**DARPA E3 benign process characteristics** (from KAIROS paper and our data analysis):
- **High-branching processes**: Firefox (~20-50 children for page loads), apt-get/package managers (~100+ file writes), compilation (~1000+ events)
- **Low-branching processes**: cron jobs (1-5 events), simple CLI tools (1-3 events)
- **Attack processes** (ground truth): nginx exploit chain (~8-15 events, branching factor ~2-3)

The problem: a Firefox process reading a news article spawns hundreds of causally-coherent file reads. Each read is "coherent" (file was opened → then read → then closed), so coherence alone won't filter them. Without a branching penalty, benign Firefox chains dominate and drown the attack signal.

**Proposed regularizer**: Branch-Weighted Coherence

```
Φ_bw(C) = Φ(C) · exp(-λ · BF(C))
```

Where BF(C) = mean out-degree of nodes in chain C (excluding terminal nodes).

This penalizes chains through high-branching nodes but preserves chains through linear processes. On DARPA E3:
- Firefox chain: Φ=0.95, BF=15 → Φ_bw = 0.95 · e^(-λ·15)
- Attack chain: Φ=0.90, BF=2.5 → Φ_bw = 0.90 · e^(-λ·2.5)
- With λ=0.05: Firefox Φ_bw=0.45, Attack Φ_bw=0.79 → attack chain ranks higher

λ itself can be calibrated on benign data: choose λ such that the top-10% most coherent benign chains have BF below some quantile.

### Why This Works in DARPA E3 Specifically

Normal system behavior in E3 follows a **power-law branching distribution**: few processes spawn many children, most spawn few. Attack chains in E3 (nginx exploit → /tmp/vUgefal → /etc/passwd → 81.49.200.166) are structurally **linear** — each step has exactly one causal successor. The branching penalty exploits this structural difference: attacks are causally coherent AND structurally sparse.

This is not a universal claim (sophisticated APTs could fan out), but it holds for the DARPA E3 attacks and provides a clean, model-free prior.

## Questions

1. **Elbow existence**: Is it guaranteed that the Φ-vs-δ curve has a detectable elbow on real provenance data? Or could the curve be smooth (monotonically increasing with no clear inflection)? If no elbow exists, what fallback criterion should select δ*?

2. **Branch-Weighted Coherence as contribution**: Does adding the branching penalty elevate the metric from "simple coherence" to a more publishable contribution? Or does it introduce too many ad-hoc parameters?

3. **Information-theoretic alternative**: Could we frame the calibration as a Minimum Description Length problem — the best (δ, τ) minimizes DL(parameters) + DL(chains | parameters)? This would give theoretical rigor. Is it worth the complexity, or is the elbow method sufficiently principled?

4. **Empirical validation of elbow**: When we actually run this on DARPA E3, do you predict we'll see a clean elbow at δ ≈ 2-3 (direct cause + cause-of-cause), consistent with typical OS interaction depth? Or is this unpredictable without running the experiment?

5. **Cross-dataset transfer**: If the elbow method discovers δ*=3 on DARPA E3, should we expect a similar δ* on StreamSpot or OpTC? If δ* varies significantly across OS versions/configurations, does the calibration protocol become a *feature* (adaptivity) or a *bug* (instability)?
