I need to revise the deliverable. What I need is NOT "what did each baseline invent" but "HOW does each baseline work, step by step, and HOW does our technical path differ from theirs." The innovation should emerge from the path comparison, not be stated as a bullet point.

## Deliverable 1: Technical Path Cards — Three Baselines + Ours

For each of KAIROS, MAGIC, EagleEye, AND our method, produce a "technical path" — the step-by-step pipeline of what the method actually does. Format identically so paths can be compared side-by-side.

Each path card should have:

**Step 1: Input** — What data enters the system?
**Step 2: Graph/Sequence Processing** — How is the provenance graph processed?
**Step 3: Feature Representation** — How are events/entities represented?
**Step 4: Model/Training** — What model is trained, on what data, with what objective?
**Step 5: Detection Mechanism** — How are anomalies identified?
**Step 6: Output** — What does the analyst receive?

Keep each step to 1-2 sentences. This is about the technical pipeline, not the motivation.

## Deliverable 2: Path Divergence Analysis

After the four path cards, produce a "where we diverge" analysis. For each step in the pipeline, identify:

- **Where do all three baselines converge** (what do they all do similarly)?
- **Where does our path branch off** from each baseline's path?
- **At which step is our innovation concentrated**? (Which step could NOT be achieved by simply combining existing components?)

This is the argument for non-incrementality: our method is not KAIROS + MAGIC + EagleEye glued together — it's a fundamentally different path that diverges at Step X.

## Deliverable 3: 10-Minute Presentation Script

Write the speaking text for a 10-minute talk. The narrative should follow the path comparison structure:

**Opening (60s)**: Hook using the real DARPA E3 attack: nginx → FORK → bash → EXEC → /tmp/vUgefal → READ → /etc/passwd → SENDTO → 81.49.200.166. "This is an APT. Six causally connected steps. Now let me show you what three state-of-the-art systems actually see when they look at this."

**The Three Paths (120s)**: Walk through each baseline's technical path, pointing at each step where they lose the causal connection. Use the path cards. "KAIROS sees this attack as a statistical blip in a 15-minute window, mixed with 10,000 other events. MAGIC sees /tmp/vUgefal as a suspicious node — but doesn't know what spawned it or what it did next. EagleEye chops the timeline into fixed windows — this attack spans two windows, so half the story is in window A, half in window B, and the connection is lost."

**Where We Diverge (120s)**: Walk through our technical path. At each step, explicitly contrast with the baselines. "Step 2 is where we diverge. Instead of slicing by time or random walk, we trace causal edges. When nginx forks bash, we follow that edge. When bash execs the malware, we follow that edge. We don't guess — the kernel recorded the causality. Step 4 is where we validate — we don't use a 1.5σ threshold or KNN distance. We train a Transformer to predict event transitions on benign chains. If a chain forces the model to make unusual predictions, it's anomalous. This is learned, not tuned."

**Why This Path Works (60s)**: The four-layer argument, anchored to specific path steps. "Signal density — our chains guarantee d ≤ δ between consecutive events. Causal invariance — our features are built on kernel-guaranteed edges, not accidental co-occurrence. Attention corroboration — when event 4 in the chain is SENDTO to an external IP, self-attention amplifies the suspicion on event 3 reading /etc/passwd. Capacity efficiency — our chains are 50 events, not 10,000."

**The Metaphor (30s)**: Flight Path Replay.

**Results Preview (60s)**: Five claims, each mapping to a path step.

**Closing (30s)**: "KAIROS, MAGIC, and EagleEye each advanced the field. But they advanced along parallel tracks — temporal, structural, sequential — that never converged. Our path converges them. And the convergence point is the causal chain."

## Deliverable 4: One-Page Visual Comparison

A markdown table mapping all four methods across the six pipeline steps (rows = steps, columns = methods). Each cell = 1 sentence describing what that method does at that step. The "divergence" should be visually obvious — cells where our method does something fundamentally different should be highlighted.

## Deliverable 5: The "Elevator Pitch"

30 seconds. Problem → what baselines miss → what we do differently → result.
