# Kairos 改进方案 — 设计讨论记录

> 目标：在 DAPRA provenance graph 上实现比 Kairos 时间窗口更细粒度的攻击检测
> 核心思路：图过滤 → Transformer 精判 → 细粒度攻击路径

---

## 一、项目背景

- 论文：KAIROS: Practical Intrusion Detection and Investigation using Whole-system Provenance (S&P 2024)
- 当前方法：TGN 给每条边打 loss → 时间窗口统计 → 异常窗口 → 串成异常队列
- 问题：15分钟时间窗口颗粒度太粗，无法定位到具体的攻击边/节点

## 二、我们的方案方向

**两阶段方案**：
1. 图模型/GNN 做前处理过滤，筛掉大量正常节点和路径
2. Transformer 对候选因果链做精判，找出真正的攻击路径

**核心挑战**：
1. 用图方法找到细粒度的异常队列有难度
2. Transformer 需要有效的输入表示才能发挥作用

---

## 三、已达成共识的关键点

### 3.1 Graph Transformer 的定位
- 不能直接调用现成的 Graph Transformer 模型作为主力
- 可以作为小的模块后续添加（如 Exphormer 的稀疏注意力、GraphGPS 的混合架构）

### 3.2 Transformer 的适用边界
- Transformer 擅长：捕捉序列中的语义距离和关联、共现模式、长距离依赖
- Transformer 不擅长：理解图拓扑结构、识别重要节点（无标注时）、处理极端类别不平衡
- 策略：把 Transformer 不能做的工作摘出来做成子模块，让 Transformer 只做它能做的

### 3.3 需要注入攻击模式知识
- 不能让 Transformer 从海量被正常数据稀释的异常数据中自己发现攻击
- 需要从已知攻击种子出发提取攻击模式，显式注入到训练数据中

### 3.4 序列化方案
- 基于因果链（causal chain）的序列化是连接图结构和 Transformer 的关键桥梁
- 需要多视角序列化补偿图结构信息的丢失
- 需要显式的结构标记（分支、并行、因果等）

### 3.5 节点重要度
- 利用图的拓扑属性无监督计算节点重要度（IDF、中心性、异常度传播等）
- 作为 Transformer 的 attention bias 或 token weight

---

## 四、理论分析：Transformer 方案可行性

### 4.1 攻击链 vs 正常链的信号层级

以 CADETS E3 真实攻击链路为例：

```
攻击链:
nginx → FORK → bash → EXEC → /tmp/vUgefal → READ → /etc/passwd → WRITE → /var/log/devc → SENDTO → 81.49.200.166

正常链:
bash → EXEC → /usr/bin/python → READ → /home/admin/script.py → WRITE → /home/admin/output.txt
```

| 信号层级 | 攻击链特征 | 正常链特征 | Transformer 能学吗？ |
|---|---|---|---|
| **边类型序列** | FORK→EXEC→READ→WRITE→SENDTO | EXEC→READ→WRITE | **能** — 核心序列模式 |
| **节点类型转换** | subject→subject→file→file→file→netflow | subject→file→file→file | **能** — 跨边界到 netflow |
| **节点路径层级** | /tmp→/etc→/var/log→外部IP | /usr/bin→/home→/home | 部分能 — 需要路径特征 |
| **节点稀有度** | vUgefal 从未出现，81.49 未知IP | python 极其常见 | **不能** — 需子模块 |
| **资源敏感性** | /etc/passwd 是凭证文件 | script.py 是普通文件 | **不能** — 需子模块 |
| **图拓扑位置** | nginx 不应 fork 子进程 | bash→python 正常父子 | **不能** — 需图结构模块 |

### 4.2 Transformer 在学什么 (Self-Attention 的物理含义)

Transformer 的核心是：对序列中任意两个位置 (i, j)，计算「理解位置 i 时，位置 j 有多重要」。

以攻击链为例：

```
位置1: nginx → FORK → bash          (web server forking — 不寻常)
位置2: bash → EXEC → /tmp/vUgefal   (临时目录执行 — 可疑)
位置3: /tmp/vUgefal → READ → /etc/passwd  (读凭证 — 高度可疑)
位置4: /tmp/vUgefal → WRITE → /var/log/devc (写日志 — 覆盖痕迹)
位置5: /tmp/vUgefal → SENDTO → 81.49.200.166 (数据窃取)
```

Attention 可以学到的事件间相互印证：
- 位置5 是 SENDTO 到外部 IP → attention 聚焦位置3「读了什么敏感数据」
- 位置2 是 EXEC 临时文件 → attention 强化位置4「WRITE 日志变得比普通写更可疑」
- 位置1 源是 nginx(web服务) → attention 使位置5 的外部通信更可疑

**核心价值**：不是孤立判断每条边，而是学习事件之间的相互印证关系。单个事件可能只是弱信号，但在上下文中互相强化就变成了强信号。

### 4.3 必须从 Transformer 剥离的子模块

| 子模块 | 做什么 | 为什么 Transformer 做不到 |
|---|---|---|
| **Node Profiler** | 计算节点属性：IDF、路径敏感性、节点类型、Bridge Centrality、异常度传播、出入度异常 | 需要全局图信息，不仅是序列内信息 |
| **Chain Extractor** | 从种子节点做前后向因果追溯，分支处理，长度截断 | 需要图遍历，不是序列操作 |
| **Graph Context** | 并行行为标注、汇聚检测、间接因果分析、社区归属 | 需要完整的图拓扑 |
| **Pattern Matcher** | 已知攻击模式的模糊匹配和泛化 | 符号化的规则匹配，不是端到端学习 |

### 4.4 完整架构：五阶段流水线

```
Phase 0: Node Profiler
  输入: 全 provenance graph
  输出: 每个节点的属性向量 (IDF, 敏感性, 中心性, 社区ID, 度异常...)
  方法: 无监督图统计 + 路径分析

Phase 1: Graph Filter
  1a. TGN 给每条边打 loss (复用 Kairos)
  1b. Top-K 高 loss 边作为种子
  1c. 从种子做前后向因果追溯
  1d. 遇到分支 → 生成多条因果链
  输出: ~几千条候选因果链

Phase 2: Chain Featurizer
  每个事件拼装特征:
  [node2higvec_src | node_type | rarity | sensitivity | community |
   edge_type_onehot | time_delta |
   node2higvec_dst | node_type | rarity | sensitivity | community |
   structure_marker]
  输出: 特征序列 (seq_len, augmented_feature_dim)

Phase 3: Transformer Discriminator
  输入: 特征序列 + attention_mask
  架构: 小型 Transformer Encoder (3-4层, d_model=128-256, ~2M params)
  输出: 链级异常分数 (0~1)
  训练: 攻击链=1, 正常链=0, CrossEntropy Loss

Phase 4: Path Assembler
  输入: 高分因果链 + 时间戳 + 节点重叠
  步骤: 共享节点 + 时间接近 → 拼接 → 完整攻击路径图
  输出: 节点/边级别的攻击路径
```

### 4.5 理论可行性判断

| 维度 | 判断 | 依据 |
|---|---|---|
| **信号充分性** | ✅ 可行 | 增强特征后，攻击链在序列模式、类型转换、稀有度组合上有足够区分性 |
| **Transformer 适用性** | ✅ 可行 | Self-attention 的"事件间相互印证"正是攻击检测需要的归纳偏置 |
| **取消大海捞针** | ✅ 可行 | 图过滤把 29M 边 → 几千条链，异常密度从 ~0.001% → ~5% |
| **数据量** | ⚠️ 有风险 | CADETS E3 一天攻击，正样本可能只有几十到几百条链 |
| **跨攻击泛化** | ⚠️ 有风险 | 新攻击模式可能完全不同于训练集 |
| **链提取质量** | 🔴 决定性 | 如果因果链丢失了攻击关键事件，后续全部无效 |

### 4.6 风险缓解策略

**数据量不足**：
- 先用 StreamSpot (600 个图，更多攻击实例) 验证概念
- 数据增强：子链采样、节点泛化(类型级替换实例级)
- 小模型 (~2M params, 3层, d_model=128) 防止过拟合
- 跨 engagement 验证 (E3 训练 → E5 测试)

**跨攻击泛化**：
- 特征多用类型级/类别级，少用实例级
- Pattern Matcher 提供 rule-based 兜底

---

## 五、待深入讨论的问题

- [ ] 因果链从 provenance graph 中的具体提取策略（正/负样本构造）
- [ ] 各子模块的具体设计细节
- [ ] 评估方案和 ground truth 构建
- [ ] 训练数据量估算和类别不平衡处理
- [ ] 用 StreamSpot 先做概念验证 vs 直接上 DAPRA

---

## 六、技术决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-06-10 | 使用因果链作为 Transformer 的基本输入单元 | Provenance 图的因果边天然适合序列化，保留事件因果关系 |
| 2026-06-10 | 多视角序列化 + 结构标记 | 补偿图拍平为序列时丢失的拓扑信息 |
| 2026-06-10 | 节点重要度无监督预计算 | 解决无标注节点问题，利用图结构信号 |
| 2026-06-10 | 两阶段架构（图过滤 → Transformer 精判） | 解决海量数据中异常稀疏的问题 |
| 2026-06-10 | Graph Transformer 作为可选小模块，不作为主力 | 现成 GT 模型不直接适配 provenance 图的异构有向时序特性 |
| 2026-06-10 | 五阶段流水线架构 | 把 Transformer 不能做的工作拆成独立子模块 (Node Profiler, Chain Extractor, Graph Context, Pattern Matcher) |
| 2026-06-10 | 特征增强策略 | 在 Kairos 的 39 维特征基础上，增加节点类型、稀有度、敏感性、社区 ID 等预计算属性 |

---

## 七、Baseline 分析与科研故事闭环 (2026-06-15)

### 7.1 已有 Baseline 深度分析

#### KAIROS (S&P 2024)
- **方法**：TGN 边类型预测 → 边重建 loss → 15分钟窗口统计 → 1.5σ 阈值 + IDF + 硬编码关键词过滤 → 异常队列拼接 → Louvain 社区发现
- **问题定义**："哪个 15 分钟时间窗口包含攻击？"
- **检测机制**：非学习的统计方法。loss 阈值、IDF、关键词黑名单均为手工规则
- **粒度**：时间窗口 → 窗口内所有边
- **作为 baseline 的定位**：
  - [x] Tier 1 必比：是你的技术起点，证明"从窗口到链"的增量收益
  - [x] 最干净的消融：同样的 TGN backbone，加上 Chain Extractor + Transformer 判别器后提升多少
  - [⚠️] 局限：KAIROS 检测侧太弱（规则方法），打败它不能证明 Transformer 好，只能证明"学习 > 规则"

#### MAGIC (USENIX Security 2024)
- **方法**：GMAE (GAT Encoder + Masked Auto-Encoder) 在良性图上训练 → 节点 embedding → KNN 密度检测
- **问题定义**："哪个系统实体是恶意的？"
- **检测机制**：KNN distance-based。学习的是正常节点 embedding 的密度分布，偏离的视为异常
- **粒度**：Batch-level (图级) 或 Entity-level (节点级)
- **作为 baseline 的定位**：
  - [x] Tier 1 必比：当前自监督 provenance IDS 的 SOTA，USENIX Security 2024
  - [⚠️] 核心差异不是"谁的方法更好"而是"回答不同问题"：MAGIC 回答"哪个节点异常"，你回答"哪条链是攻击"
  - [⚠️] 需要小心控制变量：特征差异（MAGIC 用简单 node type onehot，你用路径层级 hash）、时序差异（MAGIC 静态快照，你有时序因果链）
  - [⚠️] CADETS 上 entity-level F1 已达 97%，天花板高，提升空间有限但并非不存在

### 7.2 必须补充的 Baseline

判断标准：必须是 CCF-A 会议/期刊或经典工作，且与研究故事强相关。

#### Tier 1 — 直接可比 (必须打败，证明问题定义优势)

| # | Baseline | 会议 | 方法概述 | 与你的关系 |
|---|---------|------|---------|-----------|
| 1 | **KAIROS** | S&P 2024 | TGN + 统计阈值 | 技术起点，增量收益证明 |
| 2 | **MAGIC** | USENIX Security 2024 | GMAE + KNN | 自监督 SOTA，entity-level 最接近 |
| 3 | **PROGRAPHER** | USENIX Security 2023 | graph2vec + TextRCNN | 唯一同时做"图嵌入 + 序列建模"的工作，和你的 "GNN + Transformer" 范式最可比 |

**PROGRAPHER 深度分析** (最重要的对比对象之一)：
- 流程：Snapshot Builder → graph2vec 图嵌入 → TextRCNN 快照序列预测 → RSG 排名定位可疑节点
- **和你最像的地方**：都是"graph embedding → sequence model"两阶段范式
- **和你不同的地方**：
  - 粒度：快照级 (snapshot) vs 因果链级 (causal chain)
  - 序列模型：TextRCNN (RNN+CNN) vs Transformer (Self-Attention)
  - 检测方式：预测下一个快照的 embedding vs 判别整条链的异常性
  - 输出：可疑节点排名 vs 完整攻击因果链
- **为什么必须比**：这是最干净的对比。同样的两阶段范式，不同的粒度选择和序列模型选择。如果赢了，你同时证明了：(a) 因果链粒度优于快照粒度，(b) Transformer 优于 TextRCNN

#### Tier 2 — 经典方法 (证明序列/图建模优势)

| # | Baseline | 会议 | 方法概述 | 与你的关系 |
|---|---------|------|---------|-----------|
| 4 | **UNICORN** | NDSS 2020 | Graph Sketching (WL核 + HistoSketch) + K-medoids 进化模型 | 第一个实用 provenance IDS，历史地位重要 |
| 5 | **ThreaTrace** | TIFS 2022 | GraphSAGE + 节点级异常检测 | 节点级 GNN 方法，与 MAGIC 互补 |
| 6 | **DeepLog** | CCS 2017 | LSTM 日志序列异常检测 | 序列异常检测的经典工作 |

**为什么需要这些**：
- **UNICORN**：证明了基于图结构的 APT 检测可行性。但它用 graph sketching 丢失了细粒度结构信息，且是 snapshot-level。你的方法在这个维度上是明确的升级
- **ThreaTrace**：和 MAGIC 都是节点级，但用 GraphSAGE 而非 GAT，且多模型分节点类型。打败它证明你的方法在节点级 GNN 方法之上的增量
- **DeepLog**：虽然不是 provenance graph 方法，但是序列异常检测的经典基准。比较它证明：你的方法不是因为"用了序列模型"而好，而是因为"在正确的数据结构（因果链）上用了序列模型"

#### Tier 3 — 近期前沿 (对标最新进展)

| # | Baseline | 会议 | 方法概述 | 与你的关系 |
|---|---------|------|---------|-----------|
| 7 | **SLOT** | CCS 2025 | Graph RL + 攻击链重建 | 最新工作，也做攻击链重建 |

**SLOT 深度分析**：
- 流程：Graph Construction → Latent Behavior Mining (attention + graph transform) → Embedding (Bernoulli bandit RL for neighbor selection) → Detection (MLP + iForest) → Attack Chain Reconstruction (LPA clustering + MITRE ATT&CK)
- **关键区别**：SLOT 的链重建是**后处理步骤**（先检测异常节点，再用聚类连成链），你的链重建是**检测本身**（先提取链，再判断链是否攻击）
- **为什么你必须讲清楚这个区别**：
  - 后处理链：链的质量受限于上游检测的质量。如果上游漏检了一个关键节点，链就断了
  - 端到端链检测：链是基本检测单元。即使单个节点信号弱，整个链的模式异常也能被 Transformer 捕获
  - 类比：先找嫌疑人再拼作案过程 (SLOT) vs 直接判断"这个作案过程是否发生" (你)

#### Tier 4 — Ablation Variants (方法贡献拆解)

| # | 变体 | 目的 |
|---|------|------|
| A | KAIROS-TGN + KNN (MAGIC 检测头接 TGN) | 隔离"检测机制"的贡献 (KNN vs Transformer) |
| B | TGN embedding + LSTM (替换 Transformer) | 隔离"Transformer 架构"的贡献 |
| C | Random walk chains (替换因果追溯) | 隔离"因果链提取"的贡献 |
| D | Without Node Profiler | 隔离"全局图统计特征"的贡献 |
| E | Without temporal features | 隔离"时序建模"的贡献 |
| F | MAGIC features on your pipeline | 隔离"特征工程"的贡献 |

#### Baseline 完整总揽

```
Tier 1 (必比, 3个): KAIROS, MAGIC, PROGRAPHER
Tier 2 (应比, 3个): UNICORN, ThreaTrace, DeepLog
Tier 3 (选比, 1个): SLOT
Tier 4 (消融, 6个): A-F
────────────────────────────────────────
Total: 7 baselines + 6 ablation variants
```

### 7.3 核心问题定义

#### 当前所有方法回答的问题

| 方法 | 检测对象 | 输出形式 | 能否給出攻擊敘事？ |
|------|---------|---------|-------------------|
| KAIROS | 15分钟时间窗口 | 异常窗口列表 | 否 (窗口内仍需人工排查) |
| MAGIC | 单个系统实体 (节点) | 可疑节点列表 | 否 (节点间关系缺失) |
| UNICORN | 图快照 | 异常快照 | 否 (快照级, 丢失内部结构) |
| ThreaTrace | 单个系统实体 (节点) | 可疑节点列表 | 否 (同 MAGIC) |
| PROGRAPHER | 图快照 + 节点 | 异常快照 + 可疑节点排名 | 部分 (节点在快照内, 无跨快照因果) |
| DeepLog | 日志序列 | 异常日志条目 | 否 (无图结构, 无因果关系) |
| SLOT | 节点 + 后处理聚类 | 异常节点 + 聚类标签链 | 部分 (链由后处理拼出, 非端到端) |
| **你的方法** | **因果链 (事件序列)** | **攻击因果链 + 完整路径** | **是 (直接输出攻击叙事)** |

#### 为什么因果链检测不可替代

APT 攻击的本质是多步因果依赖：
```
初始入侵 → 持久化 → 提权 → 横向移动 → 数据渗出
```

在 provenance graph 中，每一步是一条因果边。关键洞察：

1. **单事件不是攻击**。`process read /etc/passwd` 在系统管理脚本中是正常的，在攻击链中才是恶意的。事件的恶意性由**上下文**定义。KAIROS/MAGIC 无法提供这个上下文。

2. **孤立节点不是攻击**。MAGIC 标记了 `/tmp/vUgefal` 和 `81.49.200.166` 为可疑，但无法告诉你它们之间的因果关系 (谁导致了谁)。SOC 分析员拿到的是"嫌疑人名单"，不是"犯罪过程"。

3. **时间窗口不是攻击**。KAIROS 的 15 分钟窗口包含数千条边，攻击边可能只有几十条。窗口级告警 = "这栋楼里发生了犯罪"。因果链 = "罪犯从哪扇门进入、经过了哪些房间、在每个房间做了什么、带走了什么"。

**你的方法的不可替代性根植于问题定义的不可替代性：如果你需要攻击路径，没有任何现有方法能给你。**

### 7.4 Transformer 在这个问题上的绝对优势

现有检测机制的共同缺陷——都是**独立判断**：

| 方法 | 判断方式 | 能否感知事件间关系？ |
|------|---------|---------------------|
| KAIROS | 每条边独立算 loss | 否 |
| MAGIC | 每个节点独立算 KNN 距离 | 否 |
| UNICORN | 每个快照独立聚类 | 否 (快照间有进化模型但快照内丢失结构) |
| ThreaTrace | 每个节点独立判断 | 否 |
| PROGRAPHER | 快照序列预测 (比上述好) | 部分 (快照级, 非事件级) |
| DeepLog | LSTM 序列预测 | 是 (但无图结构, 无因果关系) |

**Transformer Self-Attention 的物理含义**：

```
A = softmax(QK^T / √d_k) · V
```

在因果链上，每个 attention score 的含义是：**"事件 j 的出现，在多大程度上印证或削弱了事件 i 的异常性"**。

以 CADETS E3 真实攻击链为例：
```
事件1: nginx → FORK → bash                     [中等异常: web server fork 不常见但可能]
事件2: bash → EXEC → /tmp/vUgefal               [中等异常: 临时目录执行]
事件3: /tmp/vUgefal → READ → /etc/passwd        [弱异常: 读密码文件, 某些系统工具也会做]
事件4: /tmp/vUgefal → WRITE → /var/log/devc     [弱异常: 写日志]
事件5: /tmp/vUgefal → SENDTO → 81.49.200.166    [中等异常: 外网通信]
```

每个单独事件都有合理解释。但 Self-Attention 让事件间**相互印证**：
- 事件5 (SENDTO 外网) → attention 聚焦事件3 (读了什么敏感数据？)
- 事件2 (EXEC 临时文件) → attention 强化事件4 (写日志变得可疑——可能是覆盖痕迹)
- 事件1 (web server fork) → attention 使事件5 (外部通信) 变成数据窃取而非正常更新

**三个弱信号在上下文中互相强化 → 一个强信号。**

这是 KNN、统计阈值、独立 loss 永远做不到的事：**弱信号的上下文聚合**。

**为什么 DeepLog 的 LSTM 不够**：
- LSTM 有遗忘门，长距离依赖会衰减
- LSTM 是单向/双向序贯的，不能像 attention 那样让任意位置直接交互
- LSTM 建模的是"下一个 event 是什么"，不是"这一整条序列是否异常"。前者是预测范式，你是判别范式

### 7.5 完整科研故事线

```
┌──────────────────────────────────────────────────────────────────┐
│  维度 1: WHAT — 定义新问题                                        │
├──────────────────────────────────────────────────────────────────┤
│  APT 攻击本质是因果链，但现有方法只检测时间窗口/孤立实体          │
│  → 第一个定义因果链级 APT 检测问题                               │
├──────────────────────────────────────────────────────────────────┤
│  维度 2: WHY — 为什么现有方法解决不了                             │
├──────────────────────────────────────────────────────────────────┤
│  - 单事件判断无法感知上下文 → 正常链中的事件与攻击链中的相同事件  │
│    被同等对待                                                    │
│  - 独立节点检测无法恢复因果关系 → 嫌疑人列表 ≠ 犯罪过程          │
│  - 快照级建模丢失内部事件结构 → 快照内的事件因果被压平            │
│  - 后处理链重建受限于上游检测质量 → 上游漏检一个节点, 链就断了    │
├──────────────────────────────────────────────────────────────────┤
│  维度 3: HOW — 因果链作为图与序列的桥梁                           │
├──────────────────────────────────────────────────────────────────┤
│  因果链 = 图的因果性 + 序列的可学习性                             │
│  - 从 provenance graph 的因果边中提取候选链 (保留因果结构)        │
│  - 将链拍平为特征序列 (适配 Transformer)                         │
│  - Self-Attention 实现事件间相互印证 (序列内上下文化)             │
│  - 端到端学习攻击链 vs 正常链的判别边界                           │
├──────────────────────────────────────────────────────────────────┤
│  维度 4: EVIDENCE — 实验证明                                      │
├──────────────────────────────────────────────────────────────────┤
│  vs 7 个 baselines (Tier 1-3) + 6 个 ablation variants (Tier 4)  │
│  指标: 链级 P/R/F1, 攻击路径完整性, SOC 分析员工作量缩减          │
├──────────────────────────────────────────────────────────────────┤
│  维度 5: CONTRIBUTION                                             │
├──────────────────────────────────────────────────────────────────┤
│  1. 首次定义因果链级 APT 检测问题                                 │
│  2. 提出 Graph→Sequence 混合架构 (TGN filter + Transformer        │
│     discriminator) 解决该问题                                     │
│  3. 因果链提取策略 (种子 → 前向/后向追溯 → 分支处理)             │
│  4. 在 DARPA 数据集上实现 SOTA 链级检测                          │
│  5. 输出可解释的攻击路径, 降低 SOC 分析负担                       │
└──────────────────────────────────────────────────────────────────┘
```

### 7.6 不可替代性论证 (Reviewer 视角)

**Q1: 为什么要做链级检测？为什么节点级/窗口级不够？**

A: APT 是过程，不是事件。节点级告诉你"谁可疑"，窗口级告诉你"什么时候可疑"，但 SOC 分析员需要的是"攻击是怎么发生的"。链级检测直接输出攻击叙事，将分析员的工作从"在千万条边中溯源"变为"在数十条链中确认"。工作量从大海捞针缩减到按图索骥。

**Q2: 不能把 KAIROS/MAGIC 的输出后处理成链吗？**

A: 后处理链的质量受限于上游。如果上游检测 FN (漏报) 了一个关键事件，后处理连出来的链就不完整。端到端检测中，即使单个事件信号弱到被上游忽略，只要整条链的模式异常，Transformer 就能检出。这是"先检测再拼链"与"以链为检测单元"的本质区别。

**Q3: 既然 PROGRAPHER 也做序列建模, 你的方法好在哪？**

A: 两个维度。(1) 粒度：PROGRAPHER 的快照 = 固定时间窗口内所有事件的压平。同一快照内的事件因果结构被丢弃。你的因果链保留了事件间的因果边方向，这是更干净、更可解释的信号。(2) 模型：TextRCNN (RNN+CNN) vs Transformer。RNN 的长距离依赖受限于遗忘门，CNN 的局部感受野无法让远距离事件直接交互。Self-Attention 让链上任意两个事件直接"对话"。

**Q4: 如果攻击链很长 (几百步)，Transformer 处理得了吗？**

A: 真实 APT 攻击的核心事件通常在 10-50 步。你不需要把整个进程的子活动都放进链，只需要关键因果边。Chain Extractor 可以通过稀有度过滤、边类型过滤、分支剪枝来控制链长度。此外 Transformer 是 O(n²)，n=50 时 cost 极小。

### 7.7 待解决的关键问题

评估设计方面的新问题：

1. **链级 Ground Truth 构建**：现有标注是节点级 (MAGIC ground truth) 或窗口级 (KAIROS)。如何从攻击描述构造标准答案因果链？
2. **链级评估指标**：predicted chain vs ground truth chain 如何计算匹配？IoU of edges? 编辑距离? 最长公共子序列? 覆盖率?
3. **与 baseline 的统一评估框架**：KAIROS 输出窗口, MAGIC 输出节点, 你输出链 → 如何映射到同一指标？
4. **跨数据集泛化**：E3 只有一个攻击场景 (4月6日), 如何证明对未见攻击的泛化？

---

## 八、技术决策记录 (续)

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-06-15 | Baseline 体系确定为 7+6 (7个外部方法 + 6个消融变体) | 覆盖直接对比、经典方法、前沿进展、方法拆解四个层次 |
| 2026-06-15 | PROGRAPHER 确定为最重要的对比对象之一 | 同样两阶段 (图嵌入→序列建模) 范式，差异在粒度 (快照 vs 链) 和序列模型 (TextRCNN vs Transformer) |
| 2026-06-15 | 科研故事锚定为"因果链级 APT 检测" | 与其他方法的问题定义有本质区别，不是"做得更好"而是"回答不同问题" |
| 2026-06-15 | MAGIC 特征简单是已知的变量混淆风险 | 需要 ablation F (MAGIC features on your pipeline) 来隔离特征工程贡献 |
| 2026-06-15 | SLOT 的链重建是后处理, 区别于你的端到端链检测 | 需要在论文中清晰区分两种范式 |

---

*最后更新：2026-06-15*
