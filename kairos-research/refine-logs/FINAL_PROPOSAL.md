# Final Proposal (v3)

# Causal-Edge-Aware Temporal Chain Extraction for APT Detection on Provenance Graphs

---

## 一、Problem Anchor

- **Bottom-line problem**: Existing provenance-based APT detection detects at coarse granularities (time windows, graph snapshots, individual entities). No method identifies which **causally-connected event sequence** constitutes the attack — yet this is exactly what SOC analysts need for investigation.
- **Must-solve bottleneck**: The gap between "something anomalous happened somewhere" and "this specific chain of causally-related events is the attack."
- **Non-goals**: NOT general provenance representation learning; NOT improving node/edge anomaly detection in isolation; NOT using LLMs; NOT cross-domain/federated; NOT claiming real-time inline blocking.
- **Constraints**: DARPA TC E3 primary; extend to E5 (THEIA/Trace) for cross-dataset; single GPU; no attack labels for training; batch evaluation matching KAIROS/MAGIC baselines.
- **Success condition**: Chain-level F1 >90%, >10% absolute improvement over window/random-walk/subgraph alternatives; >50× investigation cost reduction vs KAIROS; demonstrated cross-dataset generalization (E3 → E5).

---

## 二、Method Thesis

**One sentence**: We propose a model-free Causal Coherence Metric that quantifies the structural integrity of event chains extracted from provenance graphs, a calibration protocol that discovers the "natural causal horizon" of an OS from benign data alone, and an autoregressive Transformer that discriminates attack chains from benign chains by learning to predict event transitions — together forming the first end-to-end system for causal chain-level APT detection.

---

## 三、Single Contribution

**The Causal Coherence Metric and its unsupervised calibration protocol.**

The metric is:
- **Model-free**: computable directly from provenance graph topology and timestamps, no model training required
- **Self-calibrating**: parameters (δ, β, λ) are discovered from benign data via elbow detection on the Φ-vs-δ curve
- **OS-adaptive**: different OS configurations produce different optimal parameters — the protocol discovers them automatically, making the system portable across environments without manual tuning

The chain extraction algorithm and autoregressive Transformer are validation mechanisms — they prove the metric's utility for downstream APT detection.

---

## 四、完整架构

### Pipeline Overview

```
┌─────────────────── OFFLINE (once per dataset) ───────────────────┐
│                                                                    │
│  Full Provenance Graph ──→ Node Profiler ──→ per-node properties │
│  (all days, all events)    (IDF, sensitivity,                     │
│                             degree anomaly,                        │
│                             bridge centrality,                     │
│                             community ID)                          │
│                                                                    │
│  Benign days (D2-D4) ──→ TGN pretraining (reuse KAIROS)          │
│                         ──→ Coherence Metric calibration           │
│                             (elbow method on Φ vs δ curve)         │
│                                                                    │
│  Benign chains (D2-D4) ──→ Autoregressive Transformer training   │
│                             (self-supervised, benign only)         │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘

┌─────────────────── ONLINE (per test day) ─────────────────────────┐
│                                                                    │
│  Day's Events                                                      │
│       │                                                            │
│       ▼                                                            │
│  ┌─────────┐                                                       │
│  │  TGN    │  edge-by-edge, updates temporal memory state          │
│  │  Filter │  outputs: per-edge reconstruction loss                │
│  └────┬────┘                                                       │
│       │ loss > threshold (95th %ile of recent benign loss)         │
│       ▼                                                            │
│  ┌──────────────────┐                                              │
│  │  Chain Extractor │  seed → fwd/bwd causal trace                 │
│  │                  │  prune via Φ_bw (Branch-Weighted Coherence)  │
│  └────┬─────────────┘                                              │
│       │ candidate chains (10-50 events, ~100-500 chains)           │
│       ▼                                                            │
│  ┌──────────────────┐                                              │
│  │  Autoregressive   │  next-event prediction per chain             │
│  │  Transformer     │  output: per-event multi-task loss           │
│  └────┬─────────────┘                                              │
│       │ per-event loss vector [L_cat, L_cont, L_time]              │
│       ▼                                                            │
│  ┌──────────────────┐                                              │
│  │  eCDF Detection  │  map loss → percentile via benign eCDF       │
│  │                  │  anomaly_score = max(P_cat, P_cont, P_time) │
│  └────┬─────────────┘                                              │
│       │ chain scores                                                │
│       ▼                                                            │
│  ┌──────────────────┐                                              │
│  │  Post-processing │  merge overlapping high-score chains         │
│  │  (simple rule)   │  (shared nodes + temporal proximity < 60s)  │
│  └──────────────────┘                                              │
│       │                                                            │
│       ▼                                                            │
│  Attack Causal Paths                                                │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 五、Phase 1: Node Profiler（离线特征工程）

为每个节点预计算 5 个属性，与 KAIROS 的 16 维 node2higvec 拼接：

| 属性 | 计算方式 | 含义 |
|------|---------|------|
| IDF | log(总时间窗口数 / 包含该节点的窗口数) | 节点稀有度 |
| Path Sensitivity | 节点路径是否包含敏感关键词 (/etc/passwd, /etc/shadow, ~/.ssh 等) | 安全敏感性 |
| Degree Anomaly | \|deg(node) - mean_deg(type)\| / std_deg(type) | 连接模式异常度 |
| Bridge Centrality | 归一化介数中心性 | 图结构桥接性 |
| Community ID | Louvain 社区发现结果 | 功能模块归属 |

**输出**: 每节点 21 维 = [node2higvec(16) | 5 属性]，不声称贡献。

---

## 六、Phase 2: TGN Seed Identification（复用 KAIROS）

- 复用 KAIROS 预训练的 TGN（GraphAttentionEmbedding + TGNMemory + LinkPredictor）
- 任务：边类型预测（自监督，仅在良性数据上训练）
- 输出：每条边的 reconstruction loss
- 种子选取：loss > 良性数据 95% 分位数 → 触发因果链提取

---

## 七、Phase 3: Causal Chain Extractor（核心算法贡献）

### 7.1 算法流程

```
Algorithm: Causal Chain Extraction
Input: Provenance graph G, seed edge s=(u₀→v₀), calibrated parameters
       (δ*, β*, λ*, B=20)
Output: Set of candidate chains with Φ_bw scores

function EXTRACT_CHAINS(G, s):
    C_set ← {[(u₀→v₀)]}  // each chain starts as [seed]
    
    // Backward trace: what caused the seed?
    current ← {(u₀→v₀)}
    for depth = 1 to ∞:
        prev ← ∅
        for each (u→v) in current:
            // incoming edges to u, within δ* causal hops
            prev ← prev ∪ CAUSAL_PREDECESSORS(G, u, δ*)
        if prev is empty: break  // causal boundary reached
        C_set ← BRANCH_EXTEND(C_set, prev, direction="backward")
        if |C_set| > B: C_set ← PRUNE_BY_Φ_bw(C_set, B)
        current ← prev
    
    // Forward trace: what did the seed cause?
    current ← {(u₀→v₀)}
    for depth = 1 to ∞:
        next ← ∅
        for each (u→v) in current:
            next ← next ∪ CAUSAL_SUCCESSORS(G, v, δ*)
        if next is empty: break
        C_set ← BRANCH_EXTEND(C_set, next, direction="forward")
        if |C_set| > B: C_set ← PRUNE_BY_Φ_bw(C_set, B)
        current ← next
    
    return C_set
```

**关键设计决策**:
- CAUSAL_PREDECESSORS: 沿逆向边 BFS，仅包含因果影响事件类型（EXEC, FORK, WRITE — 不含 READ, CLOSE）
- CAUSAL_SUCCESSORS: 沿正向边 BFS
- BRANCH_EXTEND: 每个 chain × 每个新边 → 新 chain（笛卡尔积），保持链内时间序
- PRUNE_BY_Φ_bw: 保留 Φ_bw 最高的 B 条链

### 7.2 Causal Coherence Metric

**核心公式 — 逐对因果相干性 (pairwise)**:

```
给定连续事件对 (e_i, e_{i+1}):
  d_i  = dst(e_i) 到 src(e_{i+1}) 的最短有向路径长度
  Δt_i = t_{i+1} - t_i
  bridge_type = 当 d_i=0 时，dst(e_i) [= src(e_{i+1})] 的节点类型

              ┌ exp(-α · d_i)                          d_i=0 且 bridge 为 identity-preserving (subject)
              │
  φ(e_i,e_{i+1}) = ┤ exp(-α · d_i) · exp(-β · Δt_i)          d_i=0 且 bridge 为 stateful (file, netflow)
              │
              └ exp(-α · d_i) · exp(-β · Δt_i)          0 < d_i ≤ δ*
              0                                         d_i > δ*
```

**为什么分三种情况**:
- **Identity-preserving bridge (subject/process)**: 进程身份保证因果关系。PID + 内存空间由内核独占，不受第三方修改 → β ≈ 0，时间衰减无意义
- **Stateful bridge (file/netflow)**: 文件/套接字是共享资源，可能被第三方覆盖 → β 施加时间衰减
- **Indirect path (d_i > 0)**: 概率性因果 → β 施加时间衰减

**链级相干性**:

```
Φ(C) = (1/(n-1)) · Σ_{i=1}^{n-1} φ(e_i, e_{i+1})     (算术平均，鲁棒于审计日志丢失)
```

**分支加权相干性 (Branch-Weighted Coherence)**:

```
Φ_bw(C) = Φ(C) · exp(-λ · BF(C))
```

其中 BF(C) = chain 中所有 non-terminal 节点的平均出度。

**命名**: "Structural Sparsity Prior" — 攻击链在结构上是稀疏的（低分支），良性进程（Firefox, apt-get）有幂律高分支出度。

### 7.3 参数校准协议（模型无关）

**核心洞察**: OS 有一个"自然因果视野"——超过某个 hop 数后，再多的事件连接都是噪声。这个视野可以通过在良性数据上观察 Φ-vs-δ 曲线来自动发现。

```
校准步骤:
1. 从良性种子用 LOOSE 参数提取 chains (δ=10, α=0.1, β=0.01)
2. 固定种子，vary δ ∈ {1,2,...,10}，重新提取 chains
3. 绘制 mean Φ vs δ 曲线
4. δ* = elbow — 即曲线二阶导数最负处（边际增益最大衰减点）
5. 固定 δ*，vary τ ∈ {10s,30s,60s,120s,300s}，重新提取 chains
6. τ* = elbow on Φ vs τ 曲线
7. α* = 1/δ*, β* = 1/τ*
8. λ* = benign chains 中 top-10% Φ 的 chains 的平均 BF 对应分位数
```

**为什么 elbow 一定存在**: OS 因果深度是有限的。回溯足够远，所有事件汇聚到 init/PID 1 或内核线程，Φ 会因为无关进程被强行连接而下降。Elbow 之前的 δ 是"有效因果视野"，之后是"噪声区"。

**为什么这是贡献**: 定义了 metric 很简单，但设计一个无监督协议，仅从良性数据中自动发现 OS 的自然因果视野，是系统层面的突破。

---

## 八、Phase 4: Autoregressive Transformer

### 8.1 训练范式

**自监督，仅在良性 chains 上训练，零攻击标签。**

给定 chain C = [e₁, e₂, ..., e_n]，自回归训练：

```
Input:     [BOS], e₁, e₂, ..., e_{n-1}
Predict:   e₁,    e₂, e₃, ..., e_n
Loss:      L(e₁|BOS), L(e₂|e₁), ..., L(e_n|e_{n-1})
```

每个 event e_i 是一个多任务预测目标。

### 8.2 输入表示（75-dim）

```
per event:
  src_node (24): [node2higvec(16) | node_type(3) | IDF(1) | sensitivity(1) |
                  degree_anomaly(1) | community_id(1) | bridge_centrality(1)]
  edge (20):     [edge_type_onehot(7) | time_sinusoidal(8) |
                  d_embed(4) | bridge_flag(3) | was_seed(1)]
                  ↑ 注意：Φ_weight 不包含在内
  dst_node (24): [同 src_node]
  structure (3): [is_branch_point | is_merge_point | depth_from_seed]

[BOS] token:     learnable 75-dim embedding

Input embedding: Linear(75 → 128) + Positional PE(128)
```

**关键设计**:
- **时间编码用 sinusoidal（8 维）**，非标量。同时捕捉毫秒级和小时级时序模式
- **图距离用 learned embedding（4 维）**，d_i ∈ {0,...,δ*}
- **bridge_flag（3 维 one-hot）**: {identity-preserving, stateful, indirect}
- **不包含 φ 作为输入特征**: φ 由 Δt、d_i、bridge_flag 确定性决定，加入会导致模型"偷懒"直接依赖 φ 而非学习事件语义

### 8.3 多任务预测头

```
Transformer output (d_model=128)
    │
    ├── MLP_head_cat_1  → edge_type (7-class CE)
    ├── MLP_head_cat_2  → node_type_src (3-class CE)
    ├── MLP_head_cat_3  → node_type_dst (3-class CE)
    ├── MLP_head_cont_1 → node2higvec_src (16-dim, Cosine Similarity Loss)
    ├── MLP_head_cont_2 → node2higvec_dst (16-dim, Cosine Similarity Loss)
    ├── MLP_head_cont_3 → IDF_src, IDF_dst, sensitivity_src, sensitivity_dst, ... (MSE, [0,1] normalized)
    └── MLP_head_time   → time_bucket (10-class CE, log-spaced buckets)
```

**时间分桶 (log-spaced 10 类)**:
[0-1ms, 1-10ms, 10-100ms, 100ms-1s, 1-10s, 10-60s, 1-10min, 10-60min, 1-24h, >24h]

### 8.4 损失函数

```
L_total = L_edge_type + L_node_type + L_nodevec + L_scalars + L_time
```

**等权和可行**: 所有组件在 [0, ~2.5] 范围内（CE ≤ log n_classes, Cosine Similarity ∈ [0,2], MSE ∈ [0,1]）。

**回退 EMA 归一化**: 如果某组件在训练中持续远大于其他:

```
L_total = Σ_k L_k / EMA_{100 batches}(L_k)
```

**梯度不分离**: 时间头与语义头共享 Transformer body — OS 中时序与语义耦合。不 detach。

**批损失**: token-level mean over all non-padded tokens（长链天然贡献更多信号）。

### 8.5 训练细节

| 参数 | 值 |
|------|-----|
| Transformer | 3-layer Encoder, d_model=128, nhead=4, d_ff=512, dropout=0.1 |
| 参数量 | ~1.5M |
| Max seq_len | 64 |
| Batching | length-bucketed (1-10, 11-20, 21-30, 31-50, 51-64) |
| Truncation | seed-centric（超长链从两端截断） |
| 最小链长 | n ≥ 3（链长 1-2 的单点异常由 TGN 处理） |
| 优化器 | Adam, lr=1e-4, weight_decay=1e-4 |
| 早停 | val loss, patience=10 |
| 训练时间 | ~1 GPU-hour |

### 8.6 自回归 vs MLM 的论证

采用自回归（next-event prediction）而非 masked event prediction（MLM/BERT）：

- 溯源图中因果严格向前流动。MLM 允许模型向前看未来的事件来重建过去的事件——可以"cheat"
- 自回归强制模型仅从历史因果事件构建表示 → 当攻击链偏离良性自回归分布时，预测误差会 spike
- 与 MAGIC 的 GMAE 互补——MAGIC 在节点/图上做 mask-reconstruct，我们在因果链序列上做自回归

---

## 九、Phase 5: Detection via eCDF Thresholding

### 9.1 异常分数计算

在 benign validation set 上运行训练好的 Transformer，独立收集每个损失组件的分布：

```
对每个损失组件 k ∈ {cat, cont, time}:
  收集 benign 链上所有 per-event L_k 值
  计算 eCDF_k: raw loss → percentile (0.0 ~ 1.0)

Inference:
  对每个 event: raw L_k → P_k = eCDF_k(L_k)
  event anomaly score = max(P_cat, P_cont, P_time)
  chain anomaly score = mean_i event_anomaly_score(e_i)
```

**为什么用 max 而非 sum**: 一个维度的强异常（如时间极不寻常但语义正常）可能被 sum 掩盖。max 保留最敏感的异常维度。

**可解释性**: 告警时输出触发的维度——"temporal anomaly" / "semantic anomaly" / "structural anomaly"。

### 9.2 阈值

链被标记为异常当 chain anomaly score > 99.9% 分位数（在 benign chains 上校准）。等价于：如果任何事件在任何一个维度上极端异常，整条链被标记。

---

## 十、Deployment Considerations

### 部署定位

**Asynchronous Out-of-Band (OOB) Detector** — 不声称实时内联阻断。作为 SOC 自动分流工具，将分析员工作量从天级压缩到秒级。

### 微批处理架构

```
Window: 60秒 tumbling window
Per window:
  1. 累积事件到滑动图缓冲（τ_max = 15 min edge retention）
  2. TGN 处理新事件，更新 memory state
  3. 仅对超过 loss 阈值的事件提取 chains
  4. Transformer 并行推理所有 chains
  5. 输出: chain scores（window 关闭后 ~2 秒内）

Throughput: ~144× 实时（一天数据 10 分钟处理完）
```

**三个防御性论断**:
1. **解耦控制平面**: TGN、Chain Extractor、Transformer 完全解耦。TGN 线性更新图状态，Transformer 仅在种子触发时被惰性并发调用
2. **线性状态可扩展性**: 图缓冲由时间窗口界定，不由系统运行时长界定 → 内存有界
3. **吞吐-延迟权衡**: 60 秒窗口是 GPU 矩阵块连续处理的最优选择，最大化吞吐，代价是可忽略的 60 秒检测延迟

### Paper 中声明/不声明

**声明**: 相比 KAIROS 增加 <20% 开销；单日处理 ~10 min；60 秒检测延迟可实现
**不声明**: 亚秒级流式延迟；生产部署就绪；内核级集成

---

## 十一、与 Baseline 的本质差异

| 方法 | 链/路径提取策略 | 我们的核心差异 |
|------|----------------|---------------|
| **EagleEye** (eCrime 2024) | 固定大小时间窗口 | 因果边追溯保留因果方向；窗口混合了无因果关联的事件 |
| **Sentient** (AAAI 2026) | 随机游走场景分割 | 随机游走可能逆因果边遍历；我们强制尊重因果方向 |
| **GET-AID** (ESORICS 2025) | 时序子图 | 时间分区忽略因果结构；我们因果追溯 |
| **SPARSE** (2024) | 规则基语义路径评分 | 需要专家规则和威胁情报；我们用自学习的 TGN 信号 |
| **SLOT/CAGE/EdgeTrace** | 后处理链重建 | 链质量受上游检测 recall 约束；我们以链为检测单元 |
| **MAGIC/KAIROS/Unicorn** | 不做链级检测 | 窗口/实体/快照级 vs 因果链级 |

**附加 baseline**: **SLEUTH, Holmes** — 经典规则基前向/后向溯源系统。用我们的 Coherence Metric 评估它们的输出，证明我们的链比它们的规则基链"更紧凑"。

---

## 十二、实验设计

### Main Experiment 1: 链提取质量 (DARPA E3 CADETS)
- 固定 Transformer 架构，仅变化链/段提取方法
- 比较: Ours (causal trace) vs EagleEye (window) vs Sentient (random walk) vs GET-AID (temporal subgraph) vs SPARSE (rule)
- 指标: Chain-level Precision/Recall/F1, AUC, Investigation Cost (#edges analyst examines)

### Main Experiment 2: 跨数据集泛化 (DARPA E5 THEIA/Trace)
- 在 E5 上重新校准 Coherence Metric 参数（协议不变，参数自动适配）
- 重新训练 TGN + Transformer
- 同样比较链提取方法，证明 causal features transfer better

### Main Experiment 3: Coherence Metric 验证（模型无关）
- Benign chains vs Random chains: Φ_bw 分布应有显著差异（证明 metric 捕获因果结构）
- Attack chains: case study — 验证攻击链也有高 Φ（攻击遵守 OS 物理规律但语义异常）
- SLEUTH/Holmes 输出 vs 我们的输出: Φ_bw(Ours) > Φ_bw(SLEUTH/Holmes)

### Ablation Suite（6 项）
1. 移除因果方向强制执行 → undirected BFS（预期最大 F1 下降）
2. 移除 TGN 时序记忆 → static edge features for seed
3. 移除 Branch-Weighted Coherence → 仅用 Φ
4. 移除 Node Profiler → 仅用 KAIROS 原始特征
5. 移除时间编码 → 标量 Δt
6. Transformer → LSTM → MLP

---

## 十三、Timeline (CCS 2026, 预计 deadline 2026 年 1 月底)

| Breakpoint | Date | Deliverable |
|------------|------|-------------|
| BP1 | Jul 31 | Coherence Metric 数学定义完成 + 在原始 DARPA E3 数据上验证 elbow 存在 |
| BP2 | Sep 30 | 自回归 Transformer 训练完成（E3 benign chains），baseline reconstruction error 建立 |
| BP3 | Nov 30 | 全流水线集成，链级 AUC/F1 on E3 + E5，vs 所有 baseline |
| BP4 | Dec–mid Jan | 论文写作 + ablation + 2 周 buffer |

**总 GPU 估算**: TGN pretraining ~5h + Transformer training ~3h (E3+E5) + Evaluation ~2h = ~10 GPU-hours

---

## 十四、关键设计决策汇总

| 决策 | 结论 | 理由 |
|------|------|------|
| 训练范式 | 自监督自回归，仅良性 | 零攻击标签，避免数据增强陷阱 |
| φ 公式 | 3-case: identity-preserving / stateful / indirect | 文件桥接脆弱性 + OS capability 原理 |
| 校准方法 | Elbow detection on Φ-vs-δ curve | 避免 trivial maximization (α=0, β=0) |
| 分支控制 | Φ_bw = Φ · exp(-λ · BF) | Structural Sparsity Prior — 攻击链低分支 |
| 时间编码 | Sinusoidal (8-dim) | 捕获毫秒到小时的多尺度时序 |
| φ 作为输入 | 不包含 | 与 Δt, d_i, bridge_flag 冗余，导致 lazy learning |
| 预测目标 | 事件特征 + Δt（不含 d_i） | d_i 依赖全局图拓扑，预测方差太大 |
| 时间预测 | 10 类 log-spaced CE | 避免 MSE 在 heavy-tailed 时间分布上梯度爆炸 |
| 损失平衡 | 等权和 + EMA 回退 | 所有组件自然在 [0, ~2.5] 范围 |
| 梯度分离 | 不分离 | OS 中时间与语义耦合 |
| 异常聚合 | component-wise eCDF + max | 保留最敏感维度，可解释 |
| 部署定位 | Async OOB Detector | 诚实，不声称实时内联阻断 |
| 评估模式 | Batch (匹配 baseline) + streaming design in discussion | Apples-to-apples comparison |
