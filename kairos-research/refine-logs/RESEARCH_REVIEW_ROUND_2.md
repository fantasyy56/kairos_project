Thank you for the honest and detailed review. I accept several of your criticisms and want to push back on one. Let me address each and ask follow-ups.

## Changes Accepted

### 1. Training Paradigm: Supervised → Self-Supervised on Benign Only
You're right. Augmenting 10 chains to 10,000 is a fatal flaw. I'm pivoting to:

**New training design**: Train the Transformer as a **masked event prediction model** on benign chains only—mask random events in benign causal chains, train the Transformer to reconstruct masked event features (analogous to BERT's MLM, applied to provenance event sequences). At inference time, chains where the model makes high reconstruction error are flagged as anomalous.

This is conceptually aligned with MAGIC's GMAE paradigm but applied to **causal chain sequences** rather than graph nodes. It has the additional benefit of requiring zero attack labels for training—positive samples are used only for evaluation, not training.

**Question**: Is this self-supervised paradigm convincing enough, or should I consider a different training objective (e.g., contrastive learning between pairs of benign chains)?

### 2. Narrative Reframe: Drop "Causal Representation Learning"
Accepted. I'm renaming the contribution to **"Causal-Edge-Aware Temporal Chain Extraction"**. The theoretical grounding will be limited to:

- **Causal sufficiency** in provenance graphs (one paragraph—kernel audit logs observe all entities, so causal sufficiency holds by construction)
- **Causal coherence metric** as the model-free calibration tool (this moves to primary contribution position)
- No Pearl/SCM overclaiming, no Schölkopf causal representation learning claims

The paper's framing shifts from "we do causal ML on provenance graphs" to "we extract causally-meaningful chains from provenance graphs and calibrate extraction quality without ground truth."

### 3. Emphasize Causal Coherence Metric
This is now positioned as a primary scientific contribution alongside the chain extraction algorithm. The story: "Existing methods extract chains using heuristics (windows, random walks, temporal subgraphs) with no way to measure chain quality without downstream labels. We propose a model-free metric that quantifies causal coherence of extracted chains, enabling parameter calibration on benign data alone."

## Pushback

### On DARPA E3 Saturation

You said DARPA E3 is saturated (baselines >95% F1) and therefore unsuitable. I want to push back:

Those >95% F1 numbers are for **node-level detection** (MAGIC) or **window-level detection** (KAIROS). My method solves a different problem: **chain-level detection** — identifying which specific sequence of causally-connected edges constitutes the attack. No existing method reports chain-level F1 on DARPA E3, because no existing method attempts this.

The question isn't "can I beat MAGIC at node detection?" — it's "can I solve a problem that MAGIC and KAIROS fundamentally cannot solve?"

That said, I take your point about dataset diversity. My revised plan:

- **DARPA E3** (CADETS): Primary development + chain-level evaluation (new problem, no saturation)
- **DARPA E5** (THEIA or Trace): Cross-dataset chain-level generalization
- Consider: **OpTC** if feasible within compute constraints

**Question**: Does this framing address your saturation concern? If not, what specific evidence would convince you that chain-level detection is sufficiently differentiated from node-level/window-level detection?

## Follow-Up Questions

1. **Self-supervised objective**: Between (a) masked event prediction on benign chains, (b) contrastive learning between benign chain pairs, or (c) next-event prediction (autoregressive)—which would you recommend for a small Transformer (~1.5M params) on ~50-event chains?

2. **Causal coherence metric as primary contribution**: You said this is "your strongest defense against being labeled incremental." If I make the causal coherence metric the primary contribution, with the extraction algorithm and self-supervised Transformer as supporting validation, does this change your venue assessment?

3. **Baseline additions**: You mentioned SLEUTH and Holmes as prior rule-based tracking work. Do you consider these required baselines for a CCS/NDSS submission, or is acknowledging them in related work (with the clear distinction that they use rules while we use learned signals) sufficient?

4. **Revised score**: With these changes—(a) self-supervised training on benign only, (b) narrative reframe away from causal ML, (c) causal coherence metric as primary contribution, (d) E3 + E5 cross-dataset—what is your revised score?

5. **Venue fit**: CCS 2026 deadline is typically late January. Given the scope of changes needed (new training paradigm, possibly new dataset), is this timeline realistic or should I target CCS 2027 / S&P 2027?

Please be as specific as possible on the remaining fatal flaws.
