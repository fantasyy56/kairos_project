# Paper Rewrite Plan — v3 (Pre-BP1 Edition)

> **版本：v3**
> **日期：2026-06-24**
> **作者：fantinli + AI co-author + GPT-5.5（Round 11/12 外审反馈）**
> **范围：英文版 `paper/` + 中文版 `paper-CN/`**
> **状态**：理论框架已被 Round 12 外审认可（7/10, no fundamental gap），本蓝图列出 **BP1（2026-07-31）实验启动前必须完成的论文改写**
> **前置文档**：
> - `Memory.md` §10.8（v2 决议 D1–D10）
> - `Memory.md` §10.10（Round 11 critique 分类）
> - `Memory.md` §10.11（Round 12 反馈 + BP1 前置任务）
> - `refine-logs/external-review-round-11-response.md`（我方 action plan）

---

## 0. North Star（v3 升级版，必须铭记）

> **真正的亮点是：在一个明确声明的 audit model 下，定义并校准一个无需 attack 模型的结构性 chain coherence 度量，并把 chain 提升为 first-class detection unit。这个度量不是因果概率，而是 audit-grounded coherence score。**

| v2 中的措辞 | v3 强制替换为 |
|------------|---------------|
| "kernel-observed causality" | "kernel-mediated dependency evidence under stated audit model" |
| "Φ as probability" / "probabilistic estimator" | "Φ as coherence score" / "length-normalized additive coherence" |
| "three-pillar causal validity argument" | "three audit-grounded coherence factors" / "three sources of dependency evidence" |
| "exact dependency causal connection" (process bridge) | "high-confidence identity continuity with decay/conditioning" |
| "closed-form probability estimate" (Poisson) | "first-order baseline hazard model, empirically validated per resource class" |
| "kernel-certified causal closure" | "kernel-certified identity scopes that bound plausible dependency horizons" |
| "true causal chain recovery" | "causally plausible chain extraction" |
| "zero attack-side prior" | "no attack labels and no attack-pattern templates" |

任何措辞违反上表 → 立即回滚。

---

## 1. v3 与 v2 的关系

v3 **包含** v2 D1–D10 全部决议，**新增**以下层次：

| 层 | 内容 | 来源 |
|----|------|------|
| **Layer A**: 框架方向决议 | v2 D1–D10 | 已锁定 |
| **Layer B**: 理论深度修正 | Round 11 critique 接受项 → action plan | Round 11 response §2 |
| **Layer C**: 外审最终要求 | Round 12 T1–T7（BP1 前 7 项） + G1–G5（5 个 gap） + W1–W4（剩余弱点） | Round 12 §5/§7/§8 |
| **Layer D**: 措辞强制替换 | 上文 North Star 表 | Round 12 §2/§4 |

冲突解决规则：**Round 12 > Round 11 response > v2 决议 > v1 措辞**。

---

## 2. v3 改写决议（在 v2 D1–D10 之上新增）

### 决议 D11：放弃概率语言（Round 12 §8 一票否决项）
- 整篇论文 Φ 不再被称为 probability、probabilistic estimator、true causal probability
- 允许的弱措辞：survival-inspired / hazard-based / likelihood-like / calibrated coherence score
- abstract 第 3 句改：从 "three-pillar causal validity argument" → "audit-grounded coherence factors"
- §4.4.2 三个 case 标题统一改：从 "causality" → "dependency evidence"

### 决议 D12：Φ 公式从 arithmetic mean 改为 mean-log（Round 12 §3.2/§3.3）

**v1/v2 公式：**
\[
\Phi(C) = \frac{1}{n-1} \sum_i \phi(e_i, e_{i+1})
\]

**v3 公式：**
\[
\log \Phi(C) = \frac{1}{n-1} \sum_i \log \max(\phi(e_i, e_{i+1}), \phi_{\min})
\]

- `φ_min` smoothing floor 是对 audit incompleteness 的妥协，需在 §6 报告对 φ_min 的 sensitivity
- 主指标：mean-log Φ
- Secondary 指标（防短链作弊）：\(S(C) = \log \Phi(C) - \gamma \log n\) 或单独 length 维度 ablation

### 决议 D13：Process bridge 公式化条件因子（Round 12 §5 Gap 5）

**v1 case-1 φ**（过强）：
\[
\phi_{\text{proc}} = 1 \quad \text{(exact, time-independent)}
\]

**v3 case-1 φ**：
\[
\phi_{\text{proc}}(e_i, e_{i+1}) = \exp(-\beta_p \Delta t) \cdot g_{\text{thread}} \cdot g_{\text{exec}} \cdot g_{\text{lifetime}}
\]

其中：
- \(g_{\text{thread}}\): same TID → 1，cross-thread → < 1
- \(g_{\text{exec}}\): no exec boundary → 1，crossed exec → < 1
- \(g_{\text{lifetime}}\): process lifetime ≤ τ_short → 1，long-lived daemon → < 1（lifetime-dependent decay）
- \(\beta_p\): 即使 same TID 也有非零温和时间衰减（避免 daemon 内长间隔事件 φ 仍为 1）

### 决议 D14：Poisson 降级 + 资源类分化（Round 12 §7.4）

- Poisson 不再作为"closed-form probability"出现
- 改为 "first-order baseline hazard model"
- §4.4.2 case-2 改为 resource-class survival models：
  - **File**: 保留 write-interference Poisson 作为 baseline，但要求 §5 报告 Poisson goodness-of-fit
  - **Pipe**: ordered-consumption model
  - **Unix socket / network socket**: connection-state survival（不是 Poisson）
  - **Shared memory / ambiguous IPC**: §7 显式 "out of model"
- 如果 §5 实验显示 Poisson goodness-of-fit 失败 → 自动 fallback 到 empirical survival function (Kaplan-Meier)

### 决议 D15：增补 §3.1 Audit Model + Event Semantics Table（Round 12 §3.1）

§3.1 必须包含 4 块（operational，不是 rhetorical）：

1. **Trusted Computing Base 声明**
   - Trusted: kernel + audit collector
   - Out of TCB: user-space processes
   - Out of scope: kernel compromise、audit buffer overflow、collector failure（建模为 missing-event noise，不专门防御）

2. **Event Coverage Table**（每行一种边类型）
   | Edge type | Source entity | Dest entity | Time semantic | Dependency direction | Dep kind (control/data/state) | Known caveats |
   |-----------|---------------|-------------|---------------|---------------------|-------------------------------|--------------|
   | EVENT_EXECUTE | process | binary file | start of exec | data + control | control transfer | no payload |
   | EVENT_READ | process | file | syscall return | data | data into proc | no offset, no content |
   | EVENT_WRITE | process | file | syscall start | data | data out of proc | offset/append unrecorded |
   | EVENT_FORK | parent proc | child proc | fork return | control + identity | child inherits parent state | fd inheritance implicit |
   | EVENT_SENDTO | process | netflow | syscall start | data | data out | flow id only |
   | EVENT_RECVFROM | netflow | process | syscall return | data | data in | flow id only |
   | EVENT_OPEN | process | file | syscall return | state | resource access | mode flag may be missing |
   | EVENT_CLOSE | process | file | syscall return | state | resource release | — |

3. **Entity Identity Model**
   - Process identity = `(pid, creation_time)` tuple；PID reuse handled by tuple
   - Thread identity: TID if available in audit subsystem (CADETS 包含)
   - File identity: `(inode, mount_id)` + rename tracking；hard link 视作同一实体
   - Socket identity: 5-tuple + CDM ObjectUUID
   - Container/namespace: 视作可能产生 PID collisions 的来源；E3/E5 默认单 namespace

4. **Missing-Event Model**
   - 当 chain 中预期边缺失时，使用 `φ_min` floor 作为补偿
   - 不尝试推断丢失内容，由 Transformer 的 next-event prediction loss 自然降级
   - Long-gap chain truncation: 若两事件 Δt > τ_gap → 强制切链
   - §6 报告 `φ_min, τ_gap` 的 sensitivity

### 决议 D16：Mixture training + ablation 三配置（Round 12 §3.4）

- Training anchor sampling: 50% uniform random + 50% benign high-loss (TGN score > 95th percentile on **benign** days)
- eCDF calibration corpus 同样使用 mixture
- §6 ablation 必须报告三个 configuration:
  - C-random-only: uniform random anchors only
  - C-seed-only: seed-matched anchors only
  - C-mixture: 50/50 (default)
- 措辞改：从"procedural identity"降级为 **"distributional coverage + partial procedural symmetry"**

### 决议 D17：Chain correctness 三层定义（Round 12 §5 Gap 1）

§4.1 增补 chain correctness 形式化定义：

1. **Dependency-plausible chain (DPC)**：\(\log \Phi(C) \geq \text{threshold}\)，纯结构属性，benign data 上多数 chain 都满足
2. **Attack-relevant chain (ARC)**：DPC 且 \(C \cap \text{GT-attack-edges} \neq \emptyset\)，需要 ground truth
3. **Complete attack narrative (CAN)**：merged set of ARCs 覆盖 attack 的 entry/lateral/exfil 三阶段

§6 evaluation metric 对应这三层：
- DPC 由 Φ 直接给出（§5 metric validation）
- ARC 通过 edge-IoU + node recall 衡量（§6 main results）
- CAN 通过 stage coverage 衡量（§6 attack reconstruction case study）

### 决议 D18：分离 Φ / A / Alert score（Round 12 §5 Gap 2）

§4 强制形式化分离：

\[
\text{Extract}(s; \Phi, \phi_{\min}, d_{\max}^*, \beta^*) \rightarrow \{C_1, \ldots, C_k\}
\]
\[
A(C) = \text{eCDF}\left[\sum_j \mathcal{L}_j(C)\right] \quad (\text{component-wise eCDF max})
\]
\[
\text{Alert}(C) = \mathbb{1}[A(C) > \theta]
\]

- Φ 只用于 extraction 和 ranking
- A 是 maliciousness score
- 永不混用，永不在 abstract 说 "Φ 衡量恶意性"

### 决议 D19：路径 vs DAG scope 显式声明（Round 12 §5 Gap 3）

§4.4 增一句：
> "We extract and score linearized seed-centric causal paths; merged alerts form an investigation graph at analyst-facing layer. Extending Φ to native DAG scoring is future work."

§7 future work 列为第 3 条。

### 决议 D20：Negative-control sanity check 进 §5（Round 12 §5 Gap 4）

§5 metric validation 必须包含 4 项 negative control，证明 Φ 度量的是 dependency structure 而非 graph density / temporal proximity：

1. **Time-shuffled graph**: 保留边和节点，时间戳全打乱 → Φ 应显著退化
2. **Direction-reversed graph**: 所有边方向反转 → Φ 应退化
3. **Entity-randomized graph**: 节点保留 degree distribution，但 identity 随机重连 → Φ 应退化
4. **Interference-shuffled graph**: 共享资源访问 interleaving 顺序随机 → case-2 φ 应退化

期望结果（写入 §5 表）：4 种 negative control 上 Φ 中位数 < benign Φ 中位数 - 2σ。

---

## 3. v3 改写任务清单（T1–T7 + 措辞 + 中文同步）

> 改动顺序：T1–T7 各项独立，可并行；但建议按 §章节顺序 §3 → §4 → §5 → §6 → §7 → abstract → conclusion 推进，最后整体过一遍措辞替换。

### T1: 删除所有概率 claim（措辞层）

**涉及章节**：abstract, §1 intro, §4.4 (whole), §4.5, §8 conclusion

**具体操作**：
1. abstract 搜索 `probability|probabilistic|exact` → 替换或删除
2. §4.4.2 三个 case 子标题：`causality` → `dependency evidence`
3. §4.4.2 段首句"with probability 1, exact"→ "with high confidence under identity-continuity conditions"
4. §4.4.2 Poisson 段开头"closed-form probability estimates rather than heuristics" → "first-order baseline hazard estimates that we validate empirically per resource class"
5. §4.4.2 末段"factored probability estimator" → "factored coherence score over audit-grounded dependency factors"

**验收**：grep `probability\|probabilistic` 在 paper/sections/*.tex 应只剩 §3.1 audit-model 段和 §6 eCDF 段（eCDF 本身是概率定义，那里保留）

### T2: Φ 公式从 arithmetic mean 改为 mean-log

**涉及章节**：§4.4.1 (Φ 定义), §4.4.2 (φ 子项), §5 (metric validation), §6 (eCDF)

**具体操作**：
1. §4.4.1 公式块替换为 D12 中 v3 公式
2. 增一句解释：`φ_min smoothing floor handles audit incompleteness (missing edges)`
3. §4.4.1 末段加 secondary length-aware variant：`S(C) = log Φ(C) − γ log n`，标注为 "reported for robustness analysis in §6.X"
4. §6 evaluation 增 ablation: `varying φ_min ∈ {1e-3, 1e-2, 1e-1}` 测 sensitivity
5. §4.6 (eCDF detection) 改输入：从 Φ → A，因为 Φ 不再是 anomaly score（D18）

**验收**：所有 Φ 公式出现处都是 log 形式；arithmetic mean 表述全部清除

### T3: Process bridge 公式化条件因子

**涉及章节**：§4.4.2 case 1

**具体操作**：
1. 替换 case-1 公式为 D13 中 v3 公式
2. 定义 `g_thread, g_exec, g_lifetime` 取值：
   - `g_thread = 1` if same TID else `0.5`（cross-thread within process）
   - `g_exec = 1` if no exec boundary else `0.3`（reset of memory image）
   - `g_lifetime = max(0.2, 1 − lifetime / τ_lifetime)`，`τ_lifetime = 1 hour`（empirically chosen，§5 sensitivity）
3. `β_p`: 默认 1e-4 / sec（30 分钟衰减到 ~0.55）
4. 增 §5 实验：long-lived daemon false-link rate（sshd, cron, browser, server）

**验收**：case-1 段落无"exact"或"probability 1"字样；公式含 4 个 factor

### T4: Poisson 降级 + resource-class survival models

**涉及章节**：§4.4.2 case 2, §5 metric validation, §7 limitations

**具体操作**：
1. case-2 段首改：从"Poisson interference process" → "resource-class survival model, with Poisson as baseline for file writes"
2. 分 4 个 sub-case:
   - File: Poisson baseline + §5 goodness-of-fit
   - Pipe: ordered consumption（前序 read 必依赖最近一次 write）
   - Socket: connection-state（同 connection 内 send/recv 配对）
   - Shared memory / ambiguous IPC: §7 显式 "out of model"
3. §5 增实验：在 benign E3 数据上做 Poisson goodness-of-fit per resource class
4. §7 limitations 加一段：shared memory / mmap / signal IPC 当前 out of model

**验收**：Poisson 不被称为 closed-form；4 个 sub-case 各有公式或显式 out-of-scope 声明

### T5: 增补 §3.1 Audit Model + Event Semantics Table

**涉及章节**：§3 新增 §3.1（在 related work 之后，§4 system design 之前）

**具体操作**：
1. 按 D15 四块结构新写 §3.1（约 1 页）
2. Event Semantics Table 完整 8 行（CADETS E3 的 8 种边类型）
3. Entity Identity Model 单独 paragraph
4. Missing-Event Model 单独 paragraph，引用 §4.4 的 `φ_min`

**验收**：§3.1 自包含；reviewer 看完知道我们假设什么、不假设什么

### T6: Mixture training + eCDF calibration

**涉及章节**：§4.5 (training), §4.6 (eCDF calibration), §6 (ablation)

**具体操作**：
1. §4.5 training corpus 段：从"uniformly random across event types"改为"50% uniform random + 50% benign high-loss anchors (TGN score > 95th percentile on benign days)"
2. 加一段解释：random covers benign distribution broadly; seed-matched matches online covariate distribution; mixture balances
3. 措辞改：从"procedural identity"→"distributional coverage + partial procedural symmetry"
4. §4.6 eCDF calibration corpus 同步改为 mixture
5. §6 ablation 表加 3 行：C-random-only / C-seed-only / C-mixture

**验收**：anchor sampling 描述含三种策略；ablation 表预留三行（占位 `DATA_NEEDED`）

### T7: Chain correctness 三层定义 + matching metric

**涉及章节**：§4.1 (overview), §6 (evaluation metrics)

**具体操作**：
1. §4.1 增 paragraph "Chain correctness levels"，按 D17 三层定义
2. §6.1 evaluation metric 新增 subsection "Chain-level matching":
   - Primary: edge-IoU(C_predicted, C_groundtruth)
   - Secondary: node recall on attack-relevant nodes
   - Tertiary: temporal overlap of chain timespan vs attack window
   - Investigation cost: #nodes/edges to inspect for full attack recovery
3. 对 node-level baselines (KAIROS/MAGIC): 定义 synthetic chain construction (1-hop / 2-hop BFS from flagged node) 以纳入同一 metric
4. Top-K reporting: K ∈ {10, 50, 100}

**验收**：三层定义清晰且与 §6 metric 一一对应

---

## 4. v3 新增的 5 个 theoretical gap 改动（G1–G5）

| Gap | 落地任务 | 在哪个 T 中已覆盖 |
|-----|---------|------------------|
| G1 (chain correctness 三层) | §4.1 + §6.1 | T7 |
| G2 (Φ/A/Alert 分离) | §4 形式化定义 | T1 (措辞) + T2 (eCDF 输入改为 A) |
| G3 (path vs DAG scope) | §4.4 一句话 + §7 future work | 新增 T8 |
| G4 (negative-control sanity check) | §5 新增 4 项实验占位 | 新增 T9 |
| G5 (long-lived process 公式) | §4.4.2 case-1 | T3 已覆盖 |

### T8: Path vs DAG scope 声明
- §4.4 第一段加一句：`"We extract and score linearized seed-centric causal paths; merged alerts form an investigation graph at analyst-facing layer. Native DAG scoring of Φ is future work."`
- §7 future work 加第 3 条

### T9: Negative-control sanity check
- §5 增 subsection "Negative-control validation of Φ"
- 占位 4 个实验结果：time-shuffled / direction-reversed / entity-randomized / interference-shuffled
- 期望表述：`"On all four negative controls, Φ degrades to < benign median - 2σ, indicating Φ measures dependency structure rather than graph density or temporal proximity."`

---

## 5. v3 新增的 4 个剩余 weakness（W1–W4，在论文 §7 中诚实标注）

| Weakness | 落地句 |
|---------|--------|
| W1 (Φ may be perceived heuristic) | §7 限制段一句：`"We call Φ a coherence score, not a probability; reviewers may still view it as heuristic absent further calibration"` |
| W2 (seed-bound recall) | §6.1 主结果段（不是 §7 脚注）加 seed-recall decomposition 子表 |
| W3 (path underrepresents branched APT) | §7 limitations 第 2 条，同 T8 |
| W4 (resource survival complexity) | §7 limitations 第 4 条："Currently models file/process/socket only; shared memory and ambiguous IPC declared out of model" |

---

## 6. 改动顺序与确认点（v3）

```
英文版改动 (paper/sections/):
  Layer 0 (措辞统一替换)
    T1 (删除概率 claim) → 确认 ●

  Layer 1 (核心公式)
    T2 (Φ → mean-log + φ_min) → 确认 ●
    T3 (process bridge 公式化) → 确认 ●
    T4 (Poisson 降级 + 4 sub-case) → 确认 ●

  Layer 2 (结构补充)
    T5 (§3.1 audit model + event table) → 确认 ●
    T6 (mixture training + 三配置 ablation) → 确认 ●
    T7 (chain correctness 三层 + matching metric) → 确认 ●

  Layer 3 (剩余 gap)
    T8 (path vs DAG scope) → 与 T9 一起 ● 
    T9 (§5 negative-control) → 确认 ●

  Layer 4 (诚实标注)
    W1-W4 加入 §7 → 确认 ●

  Layer 5 (Contribution list 重排为 v3)
    按 §10.11.3 4 项 → 确认 ●

  Layer 6 (Abstract / Conclusion 最终对齐)
    确认 ●

中文版 (paper-CN/sections/):
  按英文版 v3 完成后整体重写，保护已成熟段落，减少机器翻译感 → 确认 ●

最后:
  Memory.md §10.12 记录 v3 改写完成 → 完成
  进入 BP1 实验阶段（2026-07-31 deadline）
```

每个确认点 fantinli 可以选：**GO** / **HOLD（就地修复）** / **ROLLBACK**。

---

## 7. 不进入 v3 的事（明确划界）

- **不**再发 Round 13 外审（Round 12 已 explicit verdict: proceed after rewrite）
- **不**修改 Timeline（BP1 仍 2026-07-31）
- **不**新增 baseline（11 个 baseline 已足够）
- **不**改 documentclass（IEEEtran 已 v1 切换完成）
- **不**改 references.bib 核心条目，仅修复 typo 和 placeholder（eagleeye, SLEUTH, EdgeTrace Authors → real names）
- **不**改实验占位符为真实数字（BP1 之后才有真实数据）

---

## 8. v3 与 v2 / Round 11 / Round 12 的对照表

| v3 决议 | v2 来源 | Round 11 来源 | Round 12 来源 |
|--------|---------|---------------|---------------|
| D11 (放弃概率语言) | — | 接受 C5 | §8.1 强制 |
| D12 (mean-log Φ) | — | 接受 C5 (action plan) | §3.2/§3.3 确认 |
| D13 (process bridge 公式化) | — | 接受 C3 (action plan) | §5 Gap 5 强制 |
| D14 (Poisson 降级) | — | 接受 C4 (action plan) | §7.4 确认 |
| D15 (§3.1 audit model) | — | 接受 C2 (action plan) | §3.1 强制 + Event Table |
| D16 (mixture training) | — | 提出 (action plan) | §3.4 接受 + 措辞调整 |
| D17 (chain correctness 三层) | — | 接受 M5 (action plan) | §5 Gap 1 强制 |
| D18 (Φ/A/Alert 分离) | — | — | §5 Gap 2 强制 |
| D19 (path vs DAG scope) | — | — | §5 Gap 3 强制 |
| D20 (negative-control) | — | — | §5 Gap 4 强制 |
| D1 (TGN 在叙事中消失) | D1 | — | — (仍有效) |
| D2 (§1 6 步递推) | D2 | — | — (仍有效) |
| D3 (dependency causality in abstract) | D3 | — | 强化为 D11 |
| D4 (BW 降级 deployment prior) | D4 | 接受 C5 | 仍有效 |
| D5 (cross-dataset) | D5 | 接受 | 仍有效 |
| D6 (elbow 下沉) | D6 | — | 仍有效 |
| D7 (contributions 重排) | D7 | — | 升级为 §10.11.3 v3 list |
| D8 (abstract 250 词) | D8 | — | 仍有效 |
| D9 (先英后中) | D9 | — | 仍有效 |
| D10 (Memory 增量) | D10 | — | 仍有效 |

---

## 9. v3 之后的路线图

```
2026-06-24 ~ 2026-07-15  v3 论文改写（英文版 + 中文版）
2026-07-15 ~ 2026-07-31  BP1 实验：metric validation
    - benign vs random Φ AUC
    - elbow / inflection curve on Φ-vs-d_max
    - Poisson goodness-of-fit per resource class
    - 4 项 negative control
    - long-lived daemon false-link rate
    - φ_min, τ_gap, β_p sensitivity
2026-07-31  BP1 deadline: §5 真实数据填入
2026-08-01 ~ 2026-09-30  BP2: 自回归 Transformer 训练（mixture anchors）
2026-09-30  BP2 deadline: §4.5 训练曲线 + ablation
2026-10-01 ~ 2026-11-30  BP3: 全流水线 + 全 baseline 对比 (E3 + E5)
2026-11-30  BP3 deadline: §6 主结果完整
2026-12 ~ 2027-01 中旬  论文最终打磨 + 2 周 buffer
2027-01 底  CCS 2026 投稿
```

---

*v3 生成于 2026-06-24，是 v2 + Round 11 response + Round 12 外审三方合并的最终蓝图。Round 13 外审不需要；v3 改写完成后直接进入 BP1 实验。*
