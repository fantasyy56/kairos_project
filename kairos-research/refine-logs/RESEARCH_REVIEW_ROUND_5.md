Good question about the SSH daemon problem. Let me think through it carefully.

## The SSH Daemon Problem, Analyzed

The concern: sshd runs for weeks. If a seed event is a malicious command executed via SSH at t=1,000,000s, and we trace backward through sshd_child → FORK → sshd_parent, the Δt between "sshd started at boot (t=0)" and "sshd fork (t=999,999)" is enormous. Does τ kill the chain?

### Why τ Doesn't Break This (in practice)

**Key insight**: We trace from EVENTS, not from PROCESSES.

When the sshd daemon forks to handle a new connection, the provenance graph records a FORK event with its OWN timestamp:

```
sshd (PID 1000, started at t=0)
  │
  ├─ ... [3 days of unrelated activity by other processes] ...
  │
  ├─ FORK → sshd_child (PID 5000)  [timestamp: t=999,999]  ← THIS is the event we trace
  │    │
  │    └─ EXEC → bash (PID 5001)   [timestamp: t=999,999.1]
  │         │
  │         └─ EXEC → wget malicious.sh  [timestamp: t=1,000,000] ← seed event
```

When tracing backward from the seed:
- Step 1: bash → EXEC → wget (Δt = 0.1s) ✓
- Step 2: sshd_child → FORK → bash (Δt = 0.1s) ✓
- Step 3: sshd → FORK → sshd_child (Δt = 0.1s) ✓

The Δt between consecutive events in the chain is 0.1s — the time between the fork and the exec, NOT the time since sshd was first started. The sshd daemon starting at boot (t=0) is 3 causal hops removed and δ≤3 naturally stops before reaching it.

**The τ parameter applies to consecutive event pairs in the chain, not to process lifetimes.**

### The Real Problem: Slow APTs (Not Dormant Daemons)

The SSH daemon case is actually benign. The real τ vulnerability is slow APT campaigns:

```
Step 1: initial compromise via phishing (t=0)
Step 2: C2 beacon (t=3,600, 1 hour later)
Step 3: payload download (t=7,200, 2 hours later)
Step 4: lateral movement (t=36,000, 10 hours later)
Step 5: data exfiltration (t=72,000, 20 hours later)
```

If τ is calibrated to 60s (typical for interactive benign sessions), this chain gets φ weights close to zero for every pair.

### The Fix: τ as Soft Decay, Not Hard Threshold

**Remove the hard threshold from φ entirely.** The pairwise coherence becomes:

```
φ(e_i, e_{i+1}) = exp(-α · d_i) · exp(-β · Δt_i)    if d_i ≤ δ
                   0                                   if d_i > δ
```

τ is removed as a hard cutoff. The temporal decay exp(-β · Δt_i) provides a CONTINUOUS penalty:
- Δt = 1s → weight ≈ 1.0
- Δt = 60s → weight ≈ 0.55 (with β=0.01)
- Δt = 3600s → weight ≈ 2.7×10⁻¹⁶ (with β=0.01)

The third case is effectively zero, which brings us to the second fix:

**Dual-β calibration**: Calibrate β separately for (a) direct causal edges (d_i = 0, e.g., FORK→EXEC) and (b) indirect causal paths (d_i > 0).

For direct causal edges (d_i=0): the OS kernel guarantees the causal relationship. β_direct should be very small (≈0) because the temporal gap is irrelevant — the kernel recorded the causality. sshd parent and sshd child are causally connected regardless of how long sshd has been running.

For indirect causal paths (d_i > 0): temporal proximity matters. A process that writes a file at t=0 and another process reads it at t=3600 may or may not be causally related, depending on whether the file was modified in between.

```
φ(e_i, e_{i+1}) = {
    exp(-α · d_i)                        if d_i = 0  (direct edge, temporal gap irrelevant)
    exp(-α · d_i) · exp(-β · Δt_i)      if d_i > 0  (indirect, temporal gap matters)
    0                                     if d_i > δ (causal boundary)
}
```

This distinction is justified by provenance graph semantics: direct edges ARE causal by definition (kernel-level audit). Indirect paths are PROBABILISTICALLY causal.

### What About Slow APTs Then?

With the soft-β approach, a slow APT (Δt = 3600s between steps, d_i > 0) gets very low φ values. The chain-level Φ will be low. But this is CORRECT behavior for the coherence metric — the metric honestly reports that indirect causal connections across hours are tenuous.

The Transformer (autoregressive, trained on benign event sequences) is the component that can flag the chain as anomalous despite low coherence. If benign chains typically have high coherence (events clustered in time) and this particular chain has low coherence but suspicious event types (e.g., unusual EXEC→SENDTO transitions), the autoregressive prediction error will be high → flagged as anomalous.

**Separation of concerns, again**: Coherence metric = "how causally tight is this chain?" Transformer = "does this event sequence, regardless of tightness, look like benign behavior?"

## Question

Does this dual-β design (direct edges unpenalized by time, indirect edges penalized) introduce a clean semantic distinction, or does it create a brittle special case that will be hard to calibrate? Is there a better way to handle the distinction between "kernel-guaranteed causality" (direct edge) and "probabilistic causality" (indirect path)?
