Gradients kept attached. Component-wise eCDF thresholding adopted. Now for batching and truncation.

## Chain Length Characteristics

After our extraction pipeline (TGN seeds + causal tracing + Branch-Weighted Coherence pruning + Structural Sparsity Prior), extracted chains should be:

- **Typical benign**: 5-30 events (e.g., cron job: 5 events, package manager install: 20-50 events)
- **High-branching benign** (Firefox, compilation): pruned by Φ_bw to ~10-40 events
- **Attack chains**: 10-15 events (linear, no branching to prune)
- **Edge case**: Extremely long chains may still appear if a seed lands on a systemd/init-related event

Saturation analysis: with δ≤3 and B=20 branch limit, the worst-case chain depth is ~12 events before termination (backward 3 hops × 2 directions, each hop adding up to B events, pruned to ~50 by temporal coherence). Realistic upper bound: ~50 events per chain.

## Batching Strategy: Length-Bucketed Padding

Given the modest sequence lengths, the standard autoregressive training setup works cleanly:

```
1. Sort all chains by length
2. Group chains into buckets: [1-10, 11-20, 21-30, 31-50, 50+]
3. Within each bucket: pad to bucket max length, causal mask
4. Sample batches from same bucket → minimize padding waste (~15-20% max)
```

**Context window**: Set max_seq_len = 64. This covers 95%+ of chains without truncation. A 64-event chain at 75-dim input is tiny by Transformer standards (~1.5M params, d_model=128 — roughly BERT-tiny scale).

## Truncation Strategy for Overlong Chains (>64 events)

For the rare chain exceeding 64 events, truncation must preserve the most causally informative events. Three options, with one clear winner:

**Option A: Seed-centric truncation** — keep events closest to the seed in causal distance, discard events at the chain extremities. Rationale: the seed is where the anomaly signal is strongest (TGN flagged it); events further from the seed are progressively less likely to be attack-relevant.

**Option B: Head + tail preservation** — keep first 8 events (causal origin) + last 8 events (causal consequence) + middle 48 events around seed. Rationale: the full causal arc matters for understanding the attack.

**Option C: Coherence-ranked truncation** — keep the 64 events with highest Φ_bw contribution (i.e., drop events that are weakly coherent with their neighbors). Rationale: let the metric we already trust make the decision.

**Recommendation**: Option A (seed-centric). It's the simplest, most computationally efficient (no re-ranking needed), and aligned with the core assumption that seed proximity = attack relevance. The backward/forward traces naturally center the chain on the seed, so truncating from the ends drops the least attack-relevant events first.

For OPTIONAL refinement (if reviewer demands): Option C can be added as a "coherence-preserving" variant in an ablation.

## Implementation Detail: Causal Mask Construction

For autoregressive training, each chain C = [e₁, ..., e_n] produces n-1 training steps:

```
Step 1: mask=[1, 0, 0, ..., 0]  →  input=[e₁, PAD, PAD, ...]  →  predict e₂
Step 2: mask=[1, 1, 0, ..., 0]  →  input=[e₁, e₂, PAD, ...]   →  predict e₃
...
```

This is standard causal LM training. A single chain contributes (n-1) loss values — one per autoregressive step. Batches mix steps from different chains with appropriate masking.

**Optimization**: Since epoch-level shuffling of individual steps across chains is expensive, batch entire chains and compute the autoregressive loss over all positions in parallel using the standard causal attention mask. PyTorch's `nn.TransformerEncoder` with `src_mask` handles this natively.

## Question

Three implementation-level concerns:

1. **Minimum chain length**: Chains of length 1-2 events contain almost no sequential information. Should we discard chains with n < 3 before training? This eliminates trivial chains (single events that happen to have high TGN loss but no causal context) but reduces benign training data.

2. **Start-of-chain token**: For autoregressive language models, a [BOS] token initializes the sequence. For our event chains, should we prepend a learnable [CHAIN_START] embedding, or just use the first event as the initial context (predicting from event 1 onward, losing the prediction of event 1 itself)?

3. **Mixed-length training stability**: If a batch contains chains of lengths [5, 8, 12, 20], the shorter chains contribute fewer loss terms. Should we weight each chain's loss by 1/(n-1) so all chains contribute equally to the batch loss, or let longer chains naturally dominate (they provide more signal per chain)?
