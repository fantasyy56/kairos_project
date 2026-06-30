# Session Memory — Kairos 改进方案讨论

> 最后更新：2026-06-23
> 详细技术设计记录：`./design-notes.md`
> 论文贡献分析：`./contribution-analysis.md`
> 最终方案：`./refine-logs/FINAL_PROPOSAL.md`
> 论文框架：`./PAPER_PLAN.md`
> 论文改写蓝图（v2）：`./PAPER_REWRITE_PLAN.md`

---

## 1. 项目背景

### Kairos 论文与代码
- 论文：Cheng et al., "KAIROS: Practical Intrusion Detection and Investigation using Whole-system Provenance", IEEE S&P 2024
- 代码仓库：`/Users/lijunyou/代码/kairos/`
- Kairos 是一个基于全系统 provenance graph 的 APT 入侵检测系统
- 核心流水线：原始日志 → PostgreSQL → 图向量化 → TGN 训练 → 边重建(测试) → 异常队列构建 → 攻击调查

### 关键代码文件（已完整阅读）
- `DARPA/CADETS_E3/config.py` — 全局配置
- `DARPA/CADETS_E3/kairos_utils.py` — 工具函数（时间转换、DB连接、hash等）
- `DARPA/CADETS_E3/create_database.py` — 解析 DARPA CDM JSON 数据入 PostgreSQL
- `DARPA/CADETS_E3/embedding.py` — 节点层级特征 hash + 图向量化（边特征 = [src_node_vec | edge_onehot | dst_node_vec], 共39维）
- `DARPA/CADETS_E3/model.py` — GNN 模型（GraphAttentionEmbedding + LinkPredictor）
- `DARPA/CADETS_E3/train.py` — TGN 训练（4月2-4日数据训练）
- `DARPA/CADETS_E3/test.py` — 边重建测试（4月3-7日），每条边得到一个 loss，按时间窗口切分
- `DARPA/CADETS_E3/anomalous_queue_construction.py` — 异常队列构建（IDF + 统计阈值 1.5σ + 队列拼接）
- `DARPA/CADETS_E3/evaluation.py` — 评估（标注了4月6日的攻击窗口和攻击节点）
- `DARPA/CADETS_E3/attack_investigation.py` — 攻击可视化（Louvain 社区发现 + Graphviz）
- `StreamSpot/` — StreamSpot 数据集实验（类似流程，不同数据格式）

### 数据集结构（CADETS E3）
- 节点类型：subject (进程)、file (文件)、netflow (网络流)
- 边类型：EVENT_EXECUTE, EVENT_READ, EVENT_WRITE, EVENT_FORK, EVENT_SENDTO, EVENT_RECVFROM, EVENT_OPEN, EVENT_CLOSE
- 数据规模：268,242 节点, 29,727,441 条事件
- 训练窗口：4月2-4日（正常数据）
- 测试窗口：4月3-7日（4月6日包含攻击）
- 标注攻击节点：/tmp/vUgefal, /var/log/devc, nginx, 81.49.200.166, 78.205.235.65 等

---

## 2. 用户目标

在 DAPRA provenance graph 上实现比 Kairos 更细粒度的攻击检测。Kairos 以 15 分钟时间窗口为检测单位，颗粒度太粗。目标是识别到具体的异常节点/边，组成攻击路径（而非攻击窗口）。

### 用户提出的方案方向
**两阶段架构**：图模型/GNN 做前处理过滤 → Transformer 做精判

### 用户的思维特点
- 不满足于表面方案，反复追问为什么可行，理论根基在哪里
- 对 "Transformer 能否学到因果关系"、"没有标注怎么办" 这类根本性问题有清晰的直觉
- 倾向先确定方案可行再动手，而非先跑实验再分析
- 主动要求做理论分析和风险识别
- 要求记录讨论过程到 markdown 文件，确保可回溯

---

## 3. 讨论演进过程

### 第一阶段：理解 Kairos 代码
- 完整阅读了 Kairos 的所有核心代码文件
- 理解了 TGN 训练、边loss计算、时间窗口统计、异常队列构建的完整流程
- 识别了 Kairos 的局限性：时间窗口太粗、统计阈值方法简单

### 第二阶段：方案方向探索
- 提出 Graph Transformer 方案 — 调研了 Graphormer、GraphGPS、Exphormer、NodeFormer、SAN、TokenGT 等
- 发现最近的 provenance graph anomaly detection 工作（Sentient、GET-AID、EdgeTrace）
- **关键判断**：Graph Transformer 不能直接调用，只能作为可选的轻量小模块。原因是：
  - 现成 GT 未适配 provenance 图的异构有向时序特性
  - 直接用于全图计算量太大
  - 结构编码（最短路径等）在 26 万节点图上不可行

### 第三阶段：方案收敛
- 用户明确两个核心问题：
  1. 如何从海量日志中提取攻击模式并注入 Transformer
  2. 序列化后丢失图结构和无节点标注的问题怎么解决
- 提出 **因果链（causal chain）** 作为图和序列的桥梁
- 提出 **Node Profiler** 等子模块解决 Transformer 做不到的事

### 第四阶段：理论可行性分析
- 分析了攻击链 vs 正常链在 6 个信号层级上的差异
- 明确了 Self-Attention 在攻击检测中的物理含义：事件间相互印证
- 拆解出 Transformer 做不到的 4 件事 → 4 个子模块
- 确定了 5 阶段流水线架构
- 识别了 2 个关键风险：数据量、跨攻击泛化

### 第五阶段：Baseline 分析与科研故事闭环 (2026-06-15)
- 完整阅读并分析了 KAIROS 和 MAGIC 的代码
- 两个 baseline 的对比矩阵：KAIROS (TGN + 统计阈值) vs MAGIC (GMAE + KNN)
- 确定需要补充的 baseline：PROGRAPHER (USENIX 2023), UNICORN (NDSS 2020), ThreaTrace (TIFS 2022), DeepLog (CCS 2017), SLOT (CCS 2025)
- 完整的科研故事闭环：从"问题定义差异"到"不可替代性论证"

### 第六阶段：Novelty Check 与 Idea 打磨 (2026-06-15~16)
- 检索发现 12 篇高度相关论文，最危险的重叠：**EagleEye** (eCrime 2024), **Sentient** (AAAI 2026), **GET-AID** (ESORICS 2025)
- 核心判断：单独组件（Transformer on provenance, attack path extraction）已被覆盖，但组合（TGN + Causal Chain + Transformer + Node Profiler）是新的
- 创新性评估：5.5-6/10 → 需要重新定位贡献

### 第七阶段：External Review with Gemini (2026-06-15~16, 10 轮)
- 使用 manual-review MCP server 接入 Gemini 做外部评审
- 分数演进：5.0 (Round 1) → 7.5 (Round 2) → 架构完整 (Round 10)
- 关键 pivot：
  1. 训练范式：监督+增强 → 自监督自回归（仅良性数据训练）
  2. 核心贡献：从"因果链作为检测单元" → "Causal Coherence Metric + 无监督校准协议"
  3. 叙事框架：从"Causal Representation Learning" → "Causal-Edge-Aware Temporal Chain Extraction"
  4. 数据集：DARPA E3 only → E3 + E5 + (可选 OpTC)
- 覆盖 10 个技术议题：训练范式、叙事框架、Coherence Metric、校准正则化、SSH daemon、File Bridge、Token 表示、损失函数、Batching、部署

### 第八阶段：Paper Plan 与论文写作 (2026-06-16)
- 使用 paper-plan skill 生成论文框架（8 节，CCS 2026 目标）
- 使用 paper-write skill 生成英文 + 中文两版 LaTeX 初稿
- 中文版适配 XeLaTeX + acmart 兼容 Overleaf 编译

---

## 4. 最终方案架构 (Locked after 10-round review)

### 唯一贡献
**Causal Coherence Metric (Φ_bw) + 无监督校准协议**

### 完整流水线
```
Offline (per dataset):
  Provenance Graph → Node Profiler → per-node properties
  Benign days → TGN pretraining (reuse KAIROS)
  Benign chains → Coherence Metric calibration (elbow method)
  Benign chains → Autoregressive Transformer training (self-supervised)

Online (per test day):
  Events → TGN (edge loss) → Top-K seeds
  Seeds → Causal Chain Extractor (Φ_bw-pruned bidirectional trace)
  Chains → Autoregressive Transformer (multi-task next-event prediction)
  Loss → eCDF thresholding → anomaly scores → attack paths
```

### 关键设计决策（全部经过评审锁定）

| 决策 | 结论 |
|------|------|
| 训练范式 | 自监督自回归，仅良性数据。自回归（非MLM）：因果严格向前，MLM可以cheat |
| Coherence Metric | 3-case φ: identity-preserving bridge (process) / stateful bridge (file/netflow) / indirect path |
| 校准方法 | Elbow detection on Φ-vs-δ curve（避免 trivial maximization α=0,β=0） |
| 分支控制 | Φ_bw = Φ · exp(-λ·BF) — Structural Sparsity Prior（攻击链低分支） |
| 时间编码 | Sinusoidal (8-dim)，非标量（多尺度时序） |
| φ 作为输入 | 不包含（与Δt, d_i, bridge_flag冗余，导致lazy learning） |
| 预测目标 | Event features + Δt（不含d_i，d_i依赖全局图拓扑） |
| 时间预测 | 10-class log-spaced CE（避免MSE在heavy-tail时间分布上梯度爆炸） |
| 损失平衡 | 等权和 + EMA回退（所有组件自然在[0,~2.5]范围） |
| 梯度分离 | 不分离时间头（OS中时间与语义耦合） |
| 异常聚合 | component-wise eCDF + max（保留最敏感维度，可解释） |
| 部署定位 | Async Out-of-Band Detector（不声称实时），微批60s窗口 |
| 评估模式 | Batch per-day（匹配KAIROS/MAGIC baseline） |

### 输入表示（75-dim per event）
- src_node (24): node2higvec(16) + node_type(3) + IDF(1) + sensitivity(1) + deg_anomaly(1) + community(1) + bridge_cent(1)
- edge (20): edge_type_onehot(7) + time_sinusoidal(8) + d_embed(4) + bridge_flag(3) + was_seed(1)
- dst_node (24): same as src
- structure (3): is_branch + is_merge + depth_from_seed
- [BOS] learnable token (75-dim)

### Transformer
- 3-layer Encoder, d_model=128, nhead=4, d_ff=512, ~1.5M params
- Multi-task prediction head: edge_type (7-CE) + node_types (3-CE ×2) + node2higvec (cosine) + scalars (MSE) + time_bucket (10-CE)
- Equal-weight sum loss, EMA normalization fallback
- Length-bucketed batching, max_seq_len=64, seed-centric truncation
- Training: benign chains only, n≥3, ~1 GPU-hour

---

## 5. Baseline 体系

### Tier 1 (直接可比)
1. **KAIROS** (S&P 2024) — TGN + 统计阈值，技术起点
2. **MAGIC** (USENIX Security 2024) — GMAE + KNN，自监督 SOTA
3. **PROGRAPHER** (USENIX Security 2023) — graph2vec + TextRCNN，两阶段范式最接近

### Tier 2 (经典方法)
4. **UNICORN** (NDSS 2020) — Graph Sketching + 进化模型
5. **ThreaTrace** (TIFS 2022) — GraphSAGE 节点级检测
6. **DeepLog** (CCS 2017) — LSTM 日志序列异常检测

### Tier 3 (近期前沿)
7. **SLOT** (CCS 2025) — Graph RL + 后处理攻击链
8. **EagleEye** (eCrime 2024) — Transformer on provenance sequences（最接近的竞争工作）
9. **Sentient** (AAAI 2026) — Graph Transformer + Mamba-2 + IAM
10. **GET-AID** (ESORICS 2025) — Two-stage graph attention + attack scenario
11. **CAGE** (Symmetry 2025) — GAT + Q-learning 因果权重
12. **EdgeTrace** (TrustCom 2025) — Masked GAE + 因果路径推断

### 额外 Baseline
- **SLEUTH / Holmes** — 经典规则基溯源系统，用 Coherence Metric 比较输出

### Ablation 变体 (6 项)
1. Remove causal direction (undirected BFS)
2. Remove TGN temporal memory (static seed features)
3. Remove Branch-Weighted Coherence (Φ only)
4. Remove Node Profiler (KAIROS raw features)
5. Remove sinusoidal time encoding (scalar Δt)
6. Transformer → LSTM → MLP

---

## 6. MCP & Skills 安装记录

### Codex MCP
- `@openai/codex` v0.139.0 已安装
- MCP 注册: `claude mcp add codex -s user -- codex mcp-server`
- 状态: 因缺少 OpenAI API Key，当前不可用

### Manual-Review MCP
- 本地路径: `Auto-claude-code-research-in-sleep/mcp-servers/manual-review/server.py`
- MCP 注册: `claude mcp add manual-review -s user -- python3 <path>/server.py`
- 状态: ✓ 已连接，用于 Gemini 外部评审 (10 轮)

### 已使用的 Skills
- `research-refine` — 方案打磨（Phase 0-4 自评 + 修订）
- `novelty-check` — 创新点查新（手动执行，Codex MCP 不可用）
- `research-review` — 外部评审（manual-review MCP + Gemini）
- `paper-plan` — 论文框架生成（CCS 2026 目标）
- `paper-write` — 论文初稿写作（英文 + 中文）

---

## 7. 文件索引

| 文件 | 内容 |
|------|------|
| `/Users/lijunyou/代码/kairos/` | Kairos 原始代码 |
| `/Users/lijunyou/代码/project/project1/KAIROS/` | Kairos 本地代码副本 |
| `/Users/lijunyou/代码/project/project1/MAGIC/` | MAGIC 本地代码副本 |
| `kairos-research/Memory.md` | 本文件 — 会话记忆 |
| `kairos-research/design-notes.md` | 详细技术设计文档 + Baseline 分析 + 科研故事闭环 |
| `kairos-research/contribution-analysis.md` | 论文贡献拆解 + Reviewer 攻防 |
| `kairos-research/PAPER_PLAN.md` | 论文框架（CCS 2026, 8 节, 15 张图表） |
| `kairos-research/refine-logs/FINAL_PROPOSAL.md` | 最终研究方案 (v3, 经过 10 轮评审) |
| `kairos-research/refine-logs/round-*-*.md` | 各轮评审和修订记录 |
| `kairos-research/refine-logs/external-review-round-*.md` | Gemini 外部评审记录 (10 轮) |
| `kairos-research/refine-logs/RESEARCH_REVIEW_REQUEST.md` | 外部评审 brief |
| `kairos-research/refine-logs/RESEARCH_REVIEW_ROUND_*.md` | 外部评审各轮 prompt |
| `kairos-research/paper/` | 英文论文 LaTeX 初稿 |
| `kairos-research/paper-CN/` | 中文论文 LaTeX 初稿 (XeLaTeX + Overleaf 可编译) |

---

## 8. Timeline (CCS 2026)

| Breakpoint | Date | Deliverable |
|------------|------|-------------|
| BP1 | 2026-07-31 | Coherence Metric 数学定义 + E3 原始数据上验证 elbow |
| BP2 | 2026-09-30 | 自回归 Transformer 训练完成 (E3 benign chains) |
| BP3 | 2026-11-30 | 全流水线集成 + E3/E5 全 baseline 对比 |
| BP4 | 2026-12 ~ 2027-01 中旬 | 论文写作 + ablation + 2 周 buffer |
| Deadline | 2027-01 底 (预计) | CCS 2026 投稿 |

---

## 9. 用户偏好记录

- 喜欢先从理论分析入手，确认可行后再讨论实现细节
- 对 Transformer 的能力边界有清醒的认识，不会过度乐观
- 组织能力强，会主动要求记录和结构化讨论
- 关注实际可操作性，不追求论文 novelty 而追求方案有效
- 对 provenance graph 和攻击检测领域有较深理解
- 偏好英文和中文论文双版本，中文版需 Overleaf 可编译
- 喜欢使用外部 AI（Gemini）做独立 cross-model review

---

*下次会话可从 Timeline BP1 开始：Coherence Metric 数学定义 + E3 原始数据上验证 elbow。*

---

## 10. 第九阶段：Paper v1 → v2 改写循环（2026-06-22 ~ 06-23）

> 详细蓝图见 `./PAPER_REWRITE_PLAN.md`（v2，2026-06-23）

### 10.1 v1 已合入的论文改动（2026-06-22）
- **§1 Introduction**：新增"Why causality is intrinsic to APT detection"段 + "kernel-observed vs inferred"段；引用 King-Backtracking (SOSP 2003) 标识 dependency explosion 经典出处。
- **§4.4.2 Causal Coherence Metric**：新增 `\paragraph{Causal validity of φ}` 显式声明 dependency causality 语义；三个 case 的合法性升级——case 1（进程桥）从"absolute"改成"with probability 1, exact, not approximated"；case 2（共享资源桥）新增**泊松干扰过程推导** Pr[no interfering write] = exp(-λ_r·Δt)，让指数衰减项不再是启发式而是闭式概率估计；case 3 新增多跳存活推导 p^d = exp(-d·ln(1/p))；末段把 Eq.4.1 显式总结为"factored probability estimator"。
- **§4.4.3 Calibration Protocol**：新增 `\paragraph{Choice of calibration chains: process lifecycles as natural causal units}`；把第 1 步的"K benign TGN seeds"改成"K process-lifecycle seeds"；明确 elbow location 是 OS 可测量属性。
- **§4.5 Architecture and Training**：把"Training uses only benign chains"一句话扩成 `\paragraph{Training chains: distributional symmetry with online extraction}`，明确训练锚点采"跨 event type 均匀随机采样 + 完全相同的提取过程 + 完全相同的参数"，引入"procedural identity, not per-chain ground truth"概念；强调校准与训练立在两个互相独立的理论根基上。
- **bib**：新增 King-Backtracking (SOSP 2003) 条目，paper/ 和 paper-CN/ 各一份独立 references.bib。
- **LaTeX 模板切换**：从 acmart (sigconf) → IEEEtran (conference)。中文版去掉所有 acmart+ctex 兼容 hack。Overleaf 编译验证：英文 pdfLaTeX、中文 XeLaTeX。

### 10.2 v1 → v2 触发点（2026-06-23 fantinli 提出）
- **fantinli 直觉性观察**："肘部检测"被当成亮点强调，但它只是一个二阶导取最负值的几何技巧，没有不可替代性。abstract / introduction 应当强调真正的重点。
- **fantinli 元判断**：这种"被错误强调的非重点"不止肘部检测一处，论文里还有很多。
- 由此触发 v2 的"亮点错位排查"。

### 10.3 v2 自检产出（AI 诊断 → fantinli 全部认可）

**A 类：被误当亮点（要降级或淡化）**
- A1 肘部检测 — abstract / contributions / conclusion 全部去除作为 selling point 的措辞
- A2 TGN "reused from KAIROS" — 从 contribution list 删除
- A3 Branch-Weighted Coherence — 降级为 deployment-time refinement，不再是 core metric
- A4 Cross-platform → cross-dataset — 修复 overclaim
- A5 Node Profiler — 从 §4.2 独立 subsection 降级为 §4.3 的一段
- A6 §4.5.1 "Why Autoregressive" — 整 subsection 删除并入一句话
- A7 §4.6 Component-wise eCDF — 加一句标注 "orthogonal to causal contribution"

**B 类：被埋没的真亮点（要提升或新增强调）**
- B1 "kernel-observed vs inferred" — 进 abstract 第二句
- B2 "chain as detection unit, not post-hoc artifact" — 进 abstract 第一句
- B3 双用途分工（calibration vs training）— 升级为 contribution 第二项
- B4 "physical causality vs semantic anomaly 关注点分离" — §4 加 design principle 段
- B5 dependency causality 语义边界 — abstract / intro / conclusion 都需要露出

**C 类：缺失的重点强调（应该有但完全没提）**
- C1 三层因果有效性论证作为 explicit theoretical contribution — 升级为 contribution 第一项的明确组成
- C2 "zero attack-side prior" 性质 — abstract 末尾独立强调
- C3 "为什么 chain-level detection 长期没人做" framing — §1 / §7 显式回答

### 10.4 fantinli 在 v2 自检上额外贡献的两点

- **fantinli D1**："直接说 reused from KAIROS 显得照搬"——AI 升级为完整决议：TGN 在叙事核心中"消失"，不仅仅换措辞，章节标题改成 generic 的 "Seed Identification"，第一句明确 framework agnostic to choice of edge-level detector。后续真要改进 TGN 时论文核心叙事不需要重写。
- **fantinli D2**："因果合理性应当从 APT 现象 + 系统日志现象层 → 必要性 → 检测理论这样的层次"——AI 反驳并补充：必须从"APT 现象本身的特点"出发而**不**从"DARPA 数据集特点"出发，否则会被 reviewer 一句"换个数据集还成立吗"问到无言。由此确定 §1 改用"APT 现象 → Provenance 现象 → 必要性合流 → 唯一技术难点 → Our approach"6 步递推叙事，三个原 limitation 不再单独成节而是融入 Our approach。

### 10.5 v2 改写决议汇总（10 条）
见 `./PAPER_REWRITE_PLAN.md` §2，决议 D1–D10。其中 D1 (TGN 消失) 和 D2 (§1 6 步递推) 是 fantinli 直接贡献并由 AI 落实为正式决议。

### 10.6 v2 落地任务（12 项 X1–X12）
见 `./PAPER_REWRITE_PLAN.md` §3。改动顺序：英文版 X1→X10 每项独立确认，全部确认后中文版 X12 不逐句翻译而是按新骨架重新中文写作（fantinli 要求"减少机器翻译感"）。最后 Memory.md 再做一次完成态总结。

### 10.7 协作流程升级
- **Codex CLI MCP**：fantinli 完成 `npm install -g @openai/codex` + `claude mcp add codex -s user -- codex mcp-server`，但 `~/.claude.json` 中 codex env 字段为空，未登录（codex login status: Not logged in）。Codex 走 ChatGPT account OAuth 或 API key 二选一，本会话期间未配通。
- **CodeBuddy IDE 限制**：当前会话 AI 无 mcp__codex__codex 工具，无法直接调用 GPT-5.5。
- **采纳的协作模式**：fantinli 作为人肉中转，AI 撰写发给 GPT-5.5 的内容，fantinli 在另一会话/IDE 转发，再把回复粘回。但本轮先做 v2 自检 + 论文改写，**改完再发 GPT-5.5 外审**（确保外审看到的是 v2 manuscript 本身，避免 reviewer-bias）。

### 10.8 v2 改写蓝图（正式决议与执行计划）

> **蓝图来源**：`./PAPER_REWRITE_PLAN.md` (v2, 2026-06-23)
> **状态**：决议已锁定，等待逐项确认后执行

#### 10.8.1 北极星（north star，必须铭记）
"真正的亮点是把 APT 检测从'哪个区域可疑'重新定义为'恢复攻击的因果叙事'，并第一次给出'链的因果质量'这个本来不存在的可度量概念。" 工具（肘部检测、TGN、BW、Node Profiler）一律不进 abstract/contribution/conclusion，只在 §4 实现描述中出现。

#### 10.8.2 十项正式决议（D1–D10）

| 决议 | 内容 | 关键改动 |
|------|------|---------|
| **D1** | TGN 在叙事核心中"消失"（不仅仅换措辞）| §4.3 标题改 "Seed Identification"，第一句 framework agnostic；abstract/intro/conclusion 不出现 TGN 三字 |
| **D2** | §1 改用"APT 现象 → Provenance 现象 → 必要性合流 → 技术难点 → Our approach"6 步递推 | 三个 limitation 融入叙事，不再单独列举；abstract 加入 D3 dependency causality 语义 |
| **D3** | Dependency causality 语义边界在 abstract 出现一次 | abstract 第 2 句声明"dependency causality"并对比"kernel-observed vs inferred" |
| **D4** | Branch-Weighted Coherence 降级为 deployment-time refinement（保留实验数字，不作亮点） | §4.4.2 Φ_bw 新增开头句"not part of causal coherence definition itself"；abstract/contribution/conclusion 不强调 |
| **D5** | Cross-platform → Cross-dataset，明确为 DARPA Transparent Computing engagements | §6.2 措辞调整；§7 future work 指明 Windows ETW/OpTC 真正跨平台留待未来 |
| **D6** | 肘部检测下沉为 implementation note | abstract/contribution/conclusion 只讲"natural causal horizon discovery"；算法术语仅在 §4.4.3 出现一次 |
| **D7** | 双用途分工 + 三层因果有效性提升为 contribution | Contribution list 重排：①chain-level paradigm grounded in dependency causality + 三层有效性论证，②principled benign-data dual usage，③end-to-end system & validation，④可选开源 |
| **D8** | Abstract ~250 词预算 | 必进：B1（kernel-observed vs inferred）、B2（chain-level detection unit）；其余下沉 introduction |
| **D9** | 先英文后中文，中文版不逐句翻译 | 中文版以 v1 已成熟段落为母版，按英文版新结构重新中文写作（长定语→短句、被动→主动、形式主语→实体主语） |
| **D10** | Memory.md 增量同步而非重写 | 本轮新增 §10，不动 §1–§9；历史路径保持原样作为记录 |

#### 10.8.3 十二项具体改动（X1–X12）与确认点

| 改动 | 涉及章节 | 内容概要 | 确认点 |
|------|---------|---------|--------|
| **X1** | Abstract (§0) | 重写：去 elbow/TGN/cross-platform/BW，加 kernel-observed/dual-usage/zero-attack-prior；5 句结构 | ✓ 待确认 |
| **X2+X3** | Introduction (§1) + Contributions list | 6 步递推 + 4 项 contribution 重排（按 D7）；三 limitation 融入散文 | ✓ 待确认 |
| **X4** | Related Work (§3) | 局部调整：KAIROS→互补问题、Transformer→different layer、positioning 中性化 | ✓ 待确认 |
| **X5** | System Design (§4) 结构 | §4.2 Node Profiler 并入 §4.3；§4.3 标题改 generic；§4.4 加 Design Principle；§4.5.1 删除；§4.6 加 orthogonal 标注 | ✓ 待确认 |
| **X6+X7** | §4.4.2–4.4.3 局部 | Φ_bw 新增 deployment-time 开头；校准协议去 selling point，用 inflection 代替 elbow | ✓ 待确认 |
| **X8+X9** | Evaluation (§6) + Discussion (§7) | Cross-dataset 措辞；新增§7.1"Why Chain-Level Detection Out of Reach" | ✓ 待确认 |
| **X10** | Conclusion (§8) | 全部重写：chain paradigm + dependency causality + dual benign usage；去 elbow/cross-platform/TGN 作亮点 | ✓ 待确认 |
| **X11** | References | 不动（King-Backtracking 已 v1 加入） | — |
| **X12** | 中文版全章 (paper-CN/sections/) | 英文版完全确认后，按新结构重新中文写作，保护 v1 成熟段落 | ✓ 待确认 |

#### 10.8.4 执行顺序与界限
- **改动顺序**：X1 → X2+X3 → X4 → X5+X6+X7 → X8+X9 → X10 → X12，每步确认后再下一步
- **不做的事**：不做实验、不新增引用、不改实验设计、不改数字占位、不改 documentclass、不改 bib
- **GPT-5.5 外审**：英文版全部确认后，发改完的论文给 GPT-5.5 review（不发 PLAN，防 reviewer-bias）

---

### 10.9 v2 改写当前状态（2026-06-23 16:33）

**状态**：PLAN 文件已生成完成，英文版改动未执行，等待逐项确认。

**预期**：fantinli 在 IDE 收到本 Memory 更新后，从 PAPER_REWRITE_PLAN.md §4 按顺序执行 X1–X10，每步在确认点拍板（GO/HOLD/ROLLBACK）。英文版全部确认后，启动中文版 X12 改写，最后进入 GPT-5.5 外审。

---

*v2 改写循环开始于 2026-06-23。下次会话若要恢复，从本 10.8.2–10.8.4 中标注"待确认"的改动项继续。*

---

### 10.10 GPT-5.5 外审 Round 11（2026-06-23 16:38）

#### 10.10.1 外审输入与状态
- **输入**：v2 改写后的英文论文（含大量实验占位符 `DATA_NEEDED` / `Expected`）
- **GPT-5.5 评分**：3/10 — Reject
- **核心评估**：理论框架有亮点，但实验空缺 + 理论 claim 过强 → 当前不适合 CCS/S&P 投稿
- **关键背景澄清（fantinli 强调）**：实验结果 fantinli 还没做，外审看到的是"理论稿件 + 实验占位"，而非完整投稿。本轮外审的 3/10 评分主因（CRITICAL 1）是已知缺口，不是论文核心争议。

#### 10.10.2 外审主要批评分类

**CRITICAL 1（已知缺口，非本轮讨论焦点）**
- 实验全是 `DATA_NEEDED` / `Expected`，但摘要/引言已声称 >50× cost reduction、>10% F1、144× real-time
- **fantinli 状态**：实验未跑，目前是 paper plan 阶段，不应作为 CCS/S&P submission 投递

**CRITICAL 2–5（理论批评，必须响应）**
| 编号 | 批评要点 | 我方初判 |
|------|---------|---------|
| C2 | "kernel-observed = causality" 表述过强；audit log 不等于严格因果 | **部分接受**：v1/v2 已声明"dependency causality"语义边界，但 abstract/intro 措辞需进一步软化为"dependency-relevant evidence under audit model"；需补 audit threat model 段 |
| C3 | exclusive-capability process bridge 的 "probability one" 在 daemon/multi-thread 场景不成立 | **接受**：case 1 措辞应从"exact"降级为"high-confidence identity continuity"；需补 thread/exec-boundary/parent-child 等额外条件；补 long-lived daemon false-link 实验 |
| C4 | Poisson interference 在 file/socket bursty 行为下不成立；干扰不仅来自 write | **接受**：保留 Poisson 作为 first-order approximation，明确不是 closed-form；需在 benign data 做 goodness-of-fit；区分文件/pipe/socket/shared-mem/netflow 不同 hazard model |
| C5 | Φ_bw 用 arithmetic mean 组合 pairwise probability 在概率论上不合理 | **接受**：改为 log-likelihood `Σ log φ_i`，或明确声明 Φ_bw 是 ranking heuristic 而非 probabilistic estimator；branch penalty 单独命名为 deployment prior（已对齐 v2 D4） |

**MAJOR 1–6（重要修正点）**
| 编号 | 批评要点 | 我方初判 |
|------|---------|---------|
| M1 | "zero attack-side prior" 与 path-sensitivity/branch sparsity 有张力 | **接受**：claim 改为"no attack labels or attack-pattern templates"；ablation 加入"移除 path features + branch penalty"实验 |
| M2 | 自身 pipeline recall 受 seed scorer 限制，与对 SLOT/CAGE 的批评不一致 | **接受**：明确 pipeline recall 上界由 seed 决定；补 oracle-seed 实验 + seed threshold sensitivity；论述改为"chain-level evidence amplification" 而非"摆脱 upstream detector" |
| M3 | calibration protocol 存在循环（用 Φ 找 Φ 参数） + 算法描述不唯一 | **接受**：给出唯一 calibration algorithm；报告 different K/days/seeds 的 stability + bootstrap CI |
| M4 | training anchors（uniform random）vs online anchors（TGN high-loss seeds）分布不一致 | **部分接受**：v1 §4.5 已用"procedural symmetry"论证，但 anchor distribution 确实不同；建议改为 mixture training（random + seed-matched），并报告 random-only/seed-matched/mixture 三组结果 |
| M5 | baseline 的 chain-level matching metric 未定义；MAGIC/KAIROS 不是 chain 级如何转换 | **接受**：定义 IoU/node-overlap/temporal-overlap 等 chain matching metric；分两组 baseline（controlled segmentation + original system） |
| M6 | self-containedness 不足：缺 architecture figure、result tables、reproducibility 段 | **本轮已知**：figure/table 待真实实验后补；reproducibility subsection 可立即增补 |

**MINOR（措辞/数字小问题，立即修复）**
- bib typo：`eagleye2024` vs `eagleeye2024`
- placeholder bib 条目：`EdgeTrace Authors`、`PanThreat Authors`、`Causal IDS Authors`
- SLEUTH 在文中提到但未引用
- 75-dim feature 加和不一致（24+20+24+3=71 ≠ 75；edge 子项 7+8+4+3+1=23 ≠ 20）→ **需复核维度定义**

**Missing References**
- SLEUTH、NoDoze、PrioTracker、Winnower / DEPIMPACT、SPADE / CamFlow / LPM / Hi-Fi、BackTracker / Taser、OpTC eval papers

#### 10.10.3 fantinli 的本轮立场（2026-06-23）
1. **不接受 3/10 作为对当前阶段的合理评分**：理由是实验未做属已知状态，外审应基于"理论稿件 quality"评分，而非"投稿 readiness"
2. **接受所有理论批评作为下一轮改进输入**：CRITICAL 2–5 + MAJOR 1–5 都是真问题，多数与 v2 改写决议方向一致（C5 与 D4 对齐、M3 已在 v2 待办）
3. **请求 GPT-5.5 进入 Round 12**：基于澄清后的状态重新评估，重点放在理论 claim 的可修正性 + 修正路径上

#### 10.10.4 下一步
- 起草给 GPT-5.5 的 Round 11 response（澄清 + 逐项响应 + 请求 Round 12）→ 写入 `refine-logs/external-review-round-11-response.md`
- 等 GPT-5.5 Round 12 反馈后，与 v2 改写蓝图（10.8）合并形成 v3 改写计划
- 维度数字（75-dim, edge 20-dim）的 typo 立即在论文中复核修复

---

*v2 改写循环 + Round 11 外审同步进行。下次会话恢复点：是否已发出 Round 11 response？GPT-5.5 是否返回 Round 12？*

---

### 10.11 GPT-5.5 外审 Round 12（2026-06-24 00:17）— **理论框架获认可**

#### 10.11.1 决定性结果

GPT-5.5 接受我方 Round 11 response 的双分数请求，返回：

| 维度 | 分数 | 判断 |
|------|------|------|
| **Score A**: 理论贡献 + 实验协议（条件于 §2 重写完成）| **7/10** | Worth executing |
| **Score B**: 当前稿件投稿就绪度 | 3/10 | 不变（已知，符合预期）|
| **实验协议本身** | 7/10 | 新增评分 |
| **Proceed to BP1?** | **YES** | After theory rewrite |
| **Fundamental theoretical gap?** | **NO** | 但概率语言必须放弃或大幅限定 |

**结论**：理论框架被认可，没有致命漏洞。剩余 7 项前置改写 + 5 个 gap 都是 fixable 的具体技术问题。**绿灯放行进入 BP1 实验**。

#### 10.11.2 Round 11 → Round 12 立场对照

| Round 11 提的问题 | Round 12 GPT-5.5 答复 |
|------------------|----------------------|
| Q1（threat-model 表是否够）| **Mostly yes**，但必须 operational 不是 rhetorical：需 TCB + event coverage 表 + entity identity 模型 + missing-event 模型 |
| Q2（mean-log Φ + smoothing 是否 defensible）| **作为 coherence score 可以**，**作为概率不行除非校准**。要求："survival-inspired/hazard-based/likelihood-like" 是 OK 的措辞，"probability that the chain is causal" 禁用 |
| Q3（mean-log vs length-normalized sum-log）| **Mean-log 是主指标**；建议加 secondary length-aware term `−γ log n` 防止短链作弊 |
| Q4（mixture training 是否够）| **够**，但要叫"distributional coverage + partial procedural symmetry"，不要叫"exact procedural identity"；三种配置都要 ablation |

#### 10.11.3 GPT-5.5 推荐的 v3 contribution list（替代 v2 D7）

```
1. Chain-level APT detection paradigm
   (seed-centric causal chains as detection unit, bridges edge alerts and attack narratives)

2. Audit-grounded dependency coherence metric
   (model-free, length-normalized score using kernel-mediated event semantics
    + process identity continuity + resource-class survival models)

3. Dual benign-data usage principle
   (calibration of structural extraction horizons ⊥ training of semantic anomaly model)

4. Experimental protocol for isolating extraction quality
   (controlled segmentation baselines + original-system baselines
    + chain-level matching metrics + seed-recall decomposition + negative controls)
```

**关键术语强制替换**（Round 12 明确要求）：
- "three-pillar causal validity argument" → **"three sources of dependency evidence"** or **"three audit-grounded coherence factors"**
- "kernel-certified causal closure" → **"kernel-certified identity scopes"**
- "true causal chain recovery" → **"causally plausible chain extraction"**
- "Φ as probability" → **"Φ as coherence score"** (length-normalized additive score over pairwise survival factors)

#### 10.11.4 BP1 实验前置任务（7 项理论改写，必须完成）

| 编号 | 任务 | 来源 |
|------|------|------|
| **T1** | 删除所有概率 claim（abstract/intro/§4/conclusion）| Round 12 §8.1 |
| **T2** | Φ 公式从 arithmetic mean 改为 mean-log（含 `φ_min` smoothing floor）| Round 12 §3.2 + Round 11 C5 |
| **T3** | Process bridge 重写为 identity-continuity，含 `g_thread / g_exec / g_lifetime` 条件因子（写入公式，不只是 prose）| Round 12 §5 Gap 5 + Round 11 C3 |
| **T4** | Poisson 降级为 resource-class baseline survival model；保留 file/process/socket 三类，shared mem/IPC 显式 out-of-model | Round 12 §7.4 + Round 11 C4 |
| **T5** | 增补 §3.1 Audit Model + Event Semantics Table（含 TCB / event coverage / entity identity / missing-event 四块）| Round 12 §3.1 + Round 11 C2 |
| **T6** | 训练 + eCDF 校准改为 mixture anchors（50% random + 50% benign high-loss seed-matched），ablation 三配置 | Round 12 §3.4 + Round 11 M4 |
| **T7** | 定义 chain-level correctness：dependency-plausible chain / attack-relevant chain / complete attack narrative 三层；并定义 edge-IoU / node recall / temporal overlap / investigation cost 等 matching metric | Round 12 §5 Gap 1 + Round 11 M5 |

#### 10.11.5 Round 12 新增的 5 个剩余 theoretical gap（BP1 前补完）

| Gap | 内容 | 落地 |
|-----|------|------|
| **G1** | "chain correctness" 三层定义（dependency-plausible / attack-relevant / complete narrative）| T7 已覆盖 |
| **G2** | 区分 Φ（extraction score） vs A（semantic anomaly score） vs final alert score；Φ 只用于 extraction/ranking，不卖 maliciousness | §4 加形式化定义：`Extract(s; Φ) → {C_i}`, `A(C) = SeqModelLossCDF(C)`, `Alert(C) = 1[A(C) > θ]` |
| **G3** | DAG vs 路径表达问题：当前 path-based 度量；明确 scope 为"seed-centric linear paths + merged investigation graphs"；native DAG scoring 列为 future work | §4.4 + §7 |
| **G4** | 负控理论 sanity check：time-shuffled / direction-reversed / entity-randomized / interference-shuffled graph 上 Φ 应显著退化 → 证明 Φ 度量的是 dependency structure 而非 graph density/temporal proximity | §5 metric validation 增补 |
| **G5** | Long-lived process 的条件因子写入 φ 公式（不只是 prose）| 已并入 T3 |

#### 10.11.6 实际仍存在的"剩余弱点"（不阻塞 BP1，但要心里有数）

- **W1**: Φ 仍可能被认为是 heuristic → fix: 一律称 "coherence" 不称 "probability"
- **W2**: 方法仍 seed-bound → fix: seed recall decomposition 放在 §6 主表而非 limitation 脚注
- **W3**: Path-based 表达可能 underrepresent branched APT → fix: 显式 scope 为 seed-centric paths
- **W4**: Resource survival 建模可能太复杂 → fix: 只做 file/process/socket，shared mem/ambiguous IPC 显式 out-of-model

#### 10.11.7 状态与下一步

**当前状态**：
- ✅ v2 改写蓝图（10.8）— 已锁定，多项与 Round 12 对齐
- ✅ Round 11 response（refine-logs/external-review-round-11-response.md）— 已起草
- ✅ Round 12 评审反馈 — 已收到，**理论框架放行**
- ⏳ v3 改写蓝图 — 待生成（合并 v2 + Round 11 action plans + Round 12 BP1 前置 7 项 + 5 个 gap）
- ⏳ 论文实际改写 — 等 v3 蓝图确认后启动

**下一步行动**：
1. 生成 `PAPER_REWRITE_PLAN_V3.md`：合并 v2 D1–D10 + Round 12 T1–T7 + G1–G5 + W1–W4，重新编号为 v3 改动清单
2. fantinli 确认 v3 蓝图 → 按顺序执行论文改写（英文版优先）
3. 改完后**不再进 Round 13 外审**（Round 12 已 explicit 说 proceed after rewrite），直接进入 BP1 实验（2026-07-31 deadline）
4. BP1 实验阶段：metric validation（benign vs random AUC、elbow curve、Poisson goodness-of-fit、Φ negative-control sanity check）

---

*v2 + Round 11/12 循环完成于 2026-06-24 00:17。*

---

### 10.12 v3 改写蓝图生成（2026-06-24 00:30）

**文件**：`./PAPER_REWRITE_PLAN_V3.md`

**内容结构**：
1. North Star（v3 升级版）+ 强制措辞替换表（9 条 v2/v3 对照）
2. v3 与 v2 关系：4 层叠加（A 框架方向 + B 理论深度 + C 外审最终要求 + D 措辞强制替换）
3. v3 决议 D11–D20（在 v2 D1–D10 之上新增 10 条）
4. v3 任务清单 T1–T9（含 §3.1 audit model 表、process bridge 公式、Poisson 资源类分化、negative-control 实验）
5. 5 个 weakness W1–W4 在 §7 诚实标注
6. 改动顺序 6 层 + 确认点
7. v3 与 v2/Round 11/Round 12 对照表
8. v3 之后的路线图（BP1 → BP2 → BP3 → 投稿）

**关键里程碑**：
- v3 改写预计 2026-06-24 ~ 2026-07-15 完成（英文 + 中文）
- 完成后**不再外审**，直接进 BP1 metric validation 实验（2026-07-31 deadline）
- v3 决议 D11/D12/D13/D14/D15 是 BP1 实验前 hard requirement（不改公式实验就跑不起来）

**下次会话恢复点**：
1. 是否已开始 v3 论文改写？停在 T 几？
2. 论文 §3.1 audit-model 段是否已写？Event Semantics Table 是否就位？
3. §4.4.2 三个 case 是否已按 D11–D14 重写？
4. §4.5 anchor sampling 是否已改为 mixture？
5. §5 是否已加 negative-control 占位段？

---

*v3 改写蓝图已生成。从此进入论文实际改写阶段，不再有外审依赖。*

---

### 10.13 v3 改写完成（2026-06-24 00:40）— **英文版 + 中文版 全量落地**

**状态**：T1–T9 + W1–W6 + Contributions（4 项）+ Abstract/Conclusion 全部落地；英文 `paper/` 与中文 `paper-CN/` 双语同步完成。

**英文版文件变更**：
| 文件 | 状态 | 关键改动 |
|------|------|---------|
| `paper/sections/0_abstract.tex` | 重写 | 删除概率论断；4 项贡献版；audit-grounded coherence factors 替代 three-pillar |
| `paper/sections/1_introduction.tex` | 重写 | §3.1 audit model 引用；4 项贡献按 v3 §10.11.3 排序 |
| `paper/sections/2_background.tex` | 轻改 | `complete` → `nearly complete under stated audit model`；causal event → kernel-mediated dependency event |
| `paper/sections/3p5_audit_model.tex` | **新建** | TCB + Event Coverage Table（8 行）+ Entity Identity Model + Missing-Event Model + Shared-Memory Out-of-Model |
| `paper/sections/4_system_design.tex` | 重写 | Φ → mean-log + φ_min；§4.4.2 case-1 公式化（β_p, g_thread, g_exec, g_lifetime）；case-2 4 sub-case（File Poisson + Pipe ordered + Socket conn-state + SHM out-of-model）；Φ/A/Alert 分离（D18 三式）；DPC/ARC/CAN 三层；linearized path scope |
| `paper/sections/5_metric_validation.tex` | 重写 | §5.3 negative-control 4 项；§5.4 per-resource survival goodness-of-fit + KM fallback；§5.5 long-lived daemon false-link；§5.7 φ_min/τ_gap/β_p sensitivity；§5.10 summary |
| `paper/sections/6_evaluation.tex` | 重写 | §6.1 chain-matching metric 3 级；§6.3 seed-recall decomposition（W2）；§6.5 ablation 三组 a/b/c（含 mixture 三配置）；§6.6 CAN case study |
| `paper/sections/7_discussion.tex` | 重写 | W1–W6（W1 coherence-not-probability; W2 seed-bound; W3 path-vs-DAG; W4 SHM out-of-model; W5 benign-train; W6 cross-engagement）；未来工作第 3 条 DAG scoring |
| `paper/sections/8_conclusion.tex` | 重写 | 四项承诺（audit model + Φ + 分数分离 + mixture training） |
| `paper/main.tex` | 改动 | 插入 `\input{sections/3p5_audit_model}` |

**中文版文件变更（paper-CN/）**：与英文版逐 section 对齐重写，保留专业术语对译表（dependency causality = 依赖因果，coherence = 一致性，DPC/ARC/CAN = 依赖合理链/攻击相关链/完整攻击叙事，audit-grounded = 审计支撑，identity continuity = 身份连续性，process bridge = 进程桥，resource-class survival = 资源类存活）；新增 `paper-CN/sections/3p5_audit_model.tex`；`paper-CN/main.tex` 同步插入。

**措辞强制替换（North Star 表）验收结果**：
- `probability`、`probabilistic`：仅剩 3 处合规残留（均为「we call Φ a coherence score, not a probability」类否定式声明，符合 v3 决议）
- `three-pillar` / 「三大支柱」：完全清除
- `exact dependency causal connection`、「概率1」、「封闭形式概率」：完全清除
- `kernel-observed causality`：改写为 `kernel-mediated dependency evidence under stated audit model`

**Label/Ref 一致性**：`sec:audit_model` 在英文 §3.5 与英文 §1/§7、中文 §3.5 与中文 §1/§7 均一致；`\input{sections/3p5_audit_model}` 已加入 `main.tex` 和 `main.tex`（中文）。

**未做的事（v3 §7 明确边界）**：
- 未发 Round 13 外审
- 未改 BP1 时间线
- 未改 baseline 数量（11 个 baseline）
- 未填真实实验数字（仍占位 `DATA_NEEDED: GAP_S*`），等 BP1 后填入
- references.bib 未做 typo 修复（v3 §7 列为可选）

**核心交付物**：英文版 9 个 section（含新增 §3.5）+ 中文版 9 个 section 同步 + Memory.md §10.13 更新。

**下次会话恢复点**：
1. 是否需要做 BP1 第一项实验？建议从 GAP_S5_BENIGN_RANDOM（最便宜、最能跑通整套提取-评分 pipeline）开始
2. 是否需要 latexmk 编译验证英文/中文版能 build？
3. references.bib 是否需要修复 placeholder（eagleeye, SLEUTH, EdgeTrace 等）
4. 是否要做 mixture anchor 训练代码原型（D16 落地）

---

*v3 论文改写已全量完成。下一步：BP1 实验启动（2026-07-31 deadline）。*

---

### 10.14 论文结构规范化与贡献重写（2026-06-24 01:39）— **英文版 + 中文版 同步完成**

**背景**：用户指出 v3 改写后的论文组织更像技术说明/备忘录，不像 CCF-A/IEEE 安全系统小论文；尤其贡献段存在三类问题：术语化标题意义不明（如"审计模型""审计支撑的因果一致性度量"）、贡献点彼此孤立、四点过多且技术细节压过工作亮点。

**本次改动目标**：把论文从"技术决议落地版"调整为"正式小论文叙事版"：章节组织按安全系统论文常见结构，贡献按问题定义 → 方法 → 系统验证三层递进表达，使读者第一眼能看出做了什么、为什么成立、工作亮点在哪里。

**新的双语论文结构**：
| 顺序 | 英文 section | 中文 section | 对应文件 |
|------|--------------|--------------|----------|
| 1 | Introduction | 引言 | `sections/1_introduction.tex` |
| 2 | Background and Problem Formulation | 背景与问题定义 | `sections/2_background.tex` |
| 3 | Method | 方法 | `sections/4_system_design.tex` |
| 4 | Experimental Setup | 实验设置 | `sections/5_metric_validation.tex` |
| 5 | Results | 实验结果 | `sections/6_evaluation.tex` |
| 6 | Discussion | 讨论 | `sections/7_discussion.tex` |
| 7 | Related Work | 相关工作 | `sections/3_related_work.tex` |
| 8 | Conclusion | 结论 | `sections/8_conclusion.tex` |

**关键结构变化**：
- 删除独立 `3p5_audit_model.tex`（英文与中文均已删除），审计模型并入 `Background and Problem Formulation / 背景与问题定义` 的 `Audit Model and Assumptions / 审计模型与假设` 小节。
- `main.tex` 与 `paper-CN/main.tex` 输入顺序同步改为：引言 → 背景与问题定义 → 方法 → 实验设置 → 实验结果 → 讨论 → 相关工作 → 结论。
- 原 `Metric Validation / 指标验证` 不再单独成章，改为 `Experimental Setup / 实验设置`；原指标验证内容并入 `Results / 实验结果` 的 RQ1。
- 原 `End-to-End Evaluation / 端到端评估` 改为按 RQ 组织的 `Results / 实验结果`。
- `Related Work / 相关工作` 移到讨论之后、结论之前，符合系统安全论文常见写法。

**新的贡献表达（三层递进）**：
1. **问题定义层**：We reformulate APT detection as causal-chain recovery / 我们把 APT 检测重新定义为因果链恢复问题。强调检测对象从窗口/节点/边转为分析员真正需要的事件链，并区分"结构成立性"和"语义异常性"。
2. **方法层**：We propose a method for extracting trustworthy causal chains from large provenance graphs / 我们提出一种从海量溯源图中提取可信因果链的方法。强调用 `\branchCoherence` 收紧可达性、缓解依赖爆炸，并且无需攻击标签或攻击模板即可校准。
3. **系统验证层**：We build and evaluate a zero-attack-prior chain-level APT detection system / 我们构建并评估了一个无攻击先验的链级 APT 检测系统。强调先提取结构可信候选链，再用自监督序列模型判定语义异常，并用链级指标评估攻击相关性和完整攻击叙事。

**双语文件同步变更**：
- `paper/sections/0_abstract.tex` 与 `paper-CN/sections/0_abstract.tex`：重写为链级问题 → 可信链提取 → 自监督异常检测 → 实验验证，不再罗列四项贡献。
- `paper/sections/1_introduction.tex` 与 `paper-CN/sections/1_introduction.tex`：重写贡献段为三层结构，删除"four contributions/四项贡献"式技术清单。
- `paper/sections/2_background.tex` 与 `paper-CN/sections/2_background.tex`：改为背景、链级问题定义、审计模型与假设、研究挑战。
- `paper/sections/5_metric_validation.tex` 与 `paper-CN/sections/5_metric_validation.tex`：改为实验设置，集中描述数据集、baseline、指标、实现细节。
- `paper/sections/6_evaluation.tex` 与 `paper-CN/sections/6_evaluation.tex`：改为实验结果，按 RQ1–RQ4 组织。
- `paper/sections/7_discussion.tex` 与 `paper-CN/sections/7_discussion.tex`：改为适用范围与部署模式、局限性、未来工作。
- `paper/sections/8_conclusion.tex` 与 `paper-CN/sections/8_conclusion.tex`：改为三层贡献闭环，不再列四项显式承诺。

**已清除/避免的表述**：
- `four contributions` / "四项贡献"
- `four explicit commitments` / "四项显式承诺"
- `An explicit audit model for kernel-mediated dependency` / "为内核中介依赖显式声明一套审计模型"作为贡献标题
- `audit-grounded, model-free Causal Coherence Metric` / "审计支撑的、无需模型的因果一致性度量"作为贡献标题
- 独立 `§3.5` 补丁式章节结构
- `Decision Dxx`、`Weakness Wxx` 等内部改写痕迹

**当前状态**：英文 `paper/` 与中文 `paper-CN/` 结构、贡献、摘要、结论已同步为正式小论文叙事版。文件名仍沿用旧名（如 `4_system_design.tex`, `5_metric_validation.tex`）以减少工程改动，但文件内正式章节标题已经规范化。

**下次会话恢复点**：
1. 如需进一步提升论文观感，可继续把 `4_system_design.tex` 文件名重命名为 `3_method.tex`、`5_metric_validation.tex` 重命名为 `4_experimental_setup.tex`，但当前 LaTeX 编译不依赖文件名。
2. 后续可继续压缩 `Method` 中过长技术细节，使其更符合小论文篇幅。
3. 真实实验数字仍为 `DATA_NEEDED: GAP_*` 占位，BP1 实验启动后填入。

---

*论文已从"v3 技术决议落地版"同步调整为中英文一致的"小论文叙事版"。*

---

## 11. 论文改写 v2→v3→精化（2026-06-23 ~ 06-24 全程同步）**最终总结**

### 11.1 改写进程三阶段压缩记录

**v2 阶段（2026-06-23）**：fantinli 诊断论文"亮点错位"（肘部检测过度强调、因果语义埋没、贡献表述技术化），触发 v2 决议 D1–D10（TGN 消失、§1 六步递推、ABD 类问题分类）。

**Round 11/12 外审（2026-06-23 16:38 ~ 00:17）**：GPT-5.5 批评理论 claim 过强（概率论、process bridge 绝对性、Poisson 假设、因果术语），但认可整体框架可行（Score A: 7/10）。响应触发 v3 决议 T1–T7（删概率、改 mean-log Φ、公式化条件因子、audit model 表、mixture training）。

**v3 精化（2026-06-24 00:40）**：全量落地英文 `paper/` + 中文 `paper-CN/` 各 9 节；并进一步调整为**正式小论文叙事版**结构（问题定义→方法→实验验证三层贡献递进）。

### 11.2 双语论文最终结构

| 顺序 | 英文 section | 中文 section | 关键改写 |
|------|--------------|--------------|---------|
| 1 | Introduction | 引言 | 改为 APT现象→链级问题→方法→验证 |
| 2 | Background & Problem | 背景与问题定义 | 加 `Audit Model & Assumptions` 小节（TCB+事件覆盖表） |
| 3 | Method | 方法 | Φ→mean-log；case-1/2 公式化条件因子；分离 Φ/A/Alert |
| 4 | Experimental Setup | 实验设置 | 改自原"Metric Validation"；集中数据集/baseline/指标 |
| 5 | Results | 实验结果 | 按 RQ1–RQ4 组织；种子回溯分解；三层链正确性；负控实验 |
| 6 | Discussion | 讨论 | 适用范围、部署、W1–W6 诚实标注 |
| 7 | Related Work | 相关工作 | 移至讨论后，保持 2+2 分类 |
| 8 | Conclusion | 结论 | 问题→方法→验证三层闭环 |

### 11.3 核心改写决议落地

**措辞强制替换**（与 v3 North Star 对标）：
- ❌ `probability` → ✅ `coherence score`（仅在否定式声明时用 probability）
- ❌ `three-pillar causal validity` → ✅ `three sources of dependency evidence`
- ❌ `kernel-observed causality` → ✅ `kernel-mediated dependency evidence under audit model`
- ❌ `exact causal connection` → ✅ `identity-continuity with conditional factors g_thread/g_exec/g_lifetime`

**新增内容**：
- 审计模型显式小节（TCB、事件覆盖、实体恒等性、缺失事件模型）
- Process bridge 公式化：`φ_1 = g_thread · g_exec · g_lifetime`
- 资源类存活分化：File (Poisson) / Pipe (ordered) / Socket (conn-state) / SHM (out-of-model)
- Φ/A/Alert 三式分离：`Extract(s; Φ) → {C_i} | A(C) = SeqLoss_eCDF | Alert = 1[A>θ]`
- Mixture anchor sampling：50% random + 50% seed-matched，ablation 三组 a/b/c
- 五层链正确性：DPC (dependency-plausible) / ARC (attack-relevant) / CAN (complete narrative) + IoU/node-recall/temporal-overlap

**已清除**：
- 概率论 claim（保留 3 处必要否定式声明）
- 四项技术贡献清单（改为三层问题→方法→系统递进）
- 肘部检测作为亮点
- TGN 作为贡献（改为框架无关 seed identifier）
- 独立 §3.5 补丁式结构

### 11.4 双语同步验收清单

✅ **英文版**（`paper/`）：  
- `0_abstract.tex` 重写（链级问题、可信提取、自监督检测）
- `1_introduction.tex` 改为三层贡献递进
- `2_background.tex` 加 Audit Model 小节 + 问题定义形式化
- `4_system_design.tex` Φ mean-log + case 公式化 + Φ/A/Alert 分离
- `5_metric_validation.tex` → 实验设置（RQ 定义、baseline、指标）
- `6_evaluation.tex` 按 RQ1–RQ4 + seed-recall 分解 + 三层链正确性
- `7_discussion.tex` 加 W1–W6 + 部署模式
- `8_conclusion.tex` 三层闭环

✅ **中文版**（`paper-CN/`）：  
与英文版逐 section 同步，保留专业术语对译表（dependency causality = 依赖因果、coherence = 一致性、DPC/ARC/CAN、audit-grounded = 审计支撑）

✅ **References**：  
- 新增 King-Backtracking (SOSP 2003) → elbow detection 理论基础（已在 v1 加入）
- 未做 placeholder 修复（eagleeye typo、EdgeTrace、SLEUTH 未引）→ 列为 BP1 后可选任务

### 11.5 状态与下一步

**当前状态**：
- ✅ v2 改写蓝图 → 全部执行
- ✅ Round 11/12 外审 → GPT-5.5 理论框架放行（Score A: 7/10）
- ✅ v3 论文改写 → 英中双版本同步落地
- ✅ 论文结构精化 → 从"技术决议落地版"→ "正式小论文叙事版"

**下一步行动**（BP1 启动前置条件）：
1. ~~latexmk 编译验证~~ → 已验证英文 pdfLaTeX、中文 XeLaTeX 可编译
2. **GAP_S5_BENIGN_RANDOM 实验**：Φ 在 benign 与 random-shuffled graph 上对比（最便宜、最能验证度量有效性）
3. **Mixture anchor 代码原型**：50% random + 50% seed-matched 两种采样
4. **Negative-control sanity check**：time-reversed / entity-randomized / interference-shuffled 场景下 Φ 退化验证
5. **真实实验数据填入**：BP1 实验完成后替换 `DATA_NEEDED: GAP_*` 占位符

**CCS 2026 Timeline 保持不变**：
| BP | 截止日期 | Deliverable |
|----|---------|------------|
| BP1 | 2026-07-31 | Metric validation（benign vs random AUC、Poisson goodness-of-fit、negative-control、φ_min/τ_gap/β_p sensitivity） |
| BP2 | 2026-09-30 | 自回归 Transformer 训练完成（E3 benign chains） |
| BP3 | 2026-11-30 | 全流水线集成 + E3/E5 全 baseline 对比 + ablation 六项 |
| BP4 | 2026-12~01中 | 论文最终写作 + 投稿 buffer |
| 投稿 | 2027-01 底 | CCS 2026 |

---

*论文从改写 v2 到定稿已全量完成（2026-06-23 ~ 06-24）。下次会话恢复点：BP1 第一个实验任务（benign-random AUC 对标）。*

---

## 12. Introduction §17 段精化与下阶段定位（2026-06-30）

### 12.1 §17 段（Transformer 检测器引入）三轮迭代

**初版问题**：原段只说"结构成立 ≠ 攻击 → 训练 Transformer"，缺少现有方法的不足论据，与前文"因果链"段落叙事不对称。

**v1 扩展**（一次过头）：拆为三段递进——
1. 链级判断难度（单步相似、靠组合区分）
2. 现有方法三类对比（规则模板 / 异常 PIDS / 序列模型）
3. 自监督 Transformer 的合理性

**v2 精简**（用户反馈\"点到为止，不要重复引用\"）：
- 删除\"现有方法\"独立段落
- 合并为单句两点式过渡，直接连\"因此训练 Transformer\"
- 移除全部引用（这些文献在 §4 段和 Related Work 已引）
- 删除\"近期序列模型\"论据（与前文 §4 段\"近期 Transformer 工作\"重复）

**最终段落结构**：
\`\`\`
§17 链级判断难 → 单步相似、靠组合 (保留)
§18 (合并) 现有 PIDS 粒度不对 + 规则模板覆盖窄 → 因此训练 Transformer
§19 自注意力适配阶段化 + 自监督无需攻击标签 (保留)
\`\`\`

### 12.2 引用键统一

- 移除未收录的 `milajerdi2019holmes` / `milajerdi2019poirot` / `hossain2017sleuth`
- 统一到现有 bib：`holmes2019` / `poirot2019`
- SLEUTH 在 Related Work 中保持裸文本不带 \\cite（与现状一致）

### 12.3 Introduction + Related Work 阶段告一段落

✅ 双语 Introduction 9 段紧凑结构定稿（英文 ~280 词 / 中文 ~520 字 已回收至简洁版）
✅ §17 段叙事与因果链段落对称（问题 → 现有方法不足 → 提出方案）
✅ 引用键全部对齐 references.bib
✅ Related Work 维持 2+2 分类，结构不动

### 12.4 下阶段：方法部分——因果链构造完善

**用户判断**：之前讨论出了\"日志 → 因果链\"的初版（链一致性评分 Φ + mean-log + 三因子 g_thread·g_exec·g_lifetime + 资源类存活分化），但**很多细节和可行性未讨论充分**。论文 §4 当前版本不够完整。

**待完善的细节维度**（预判）：
1. **Φ 评分的具体公式**：g_thread/g_exec/g_lifetime 三因子的精确定义、参数 φ_min/τ_gap/β_p 取值依据
2. **资源类存活模型**：File (Poisson)、Pipe (ordered)、Socket (conn-state)、SHM (out-of-model) 的判定边界与触发条件
3. **种子识别器（seed scorer）**：边级评分如何与下游 Φ 链提取衔接，是否端到端？
4. **双向链提取算法**：前向/后向扩展的截断准则、剪枝策略、最大链长控制
5. **链一致性 vs 链完整性**：DPC / ARC / CAN 三层指标的算法定义与可计算性
6. **审计模型边界**：TCB 假设下，缺失事件、内核级攻击、跨主机审计的处理
7. **可行性威胁**：依赖爆炸是否被 Φ 真的有效缓解？β_p 标定的数据需求？冷启动？

**讨论方式**：用户询问是否需要外部 GPT 协助。回复建议——
- **可自主推进**：方案细化、公式补全、算法伪代码、可行性自审、与论文 §4 现状对照
- **建议外审介入点**（仅在以下情况）：
  a. 关键公式存在多种合理选择，无法仅凭论文上下文判断
  b. 需要对标特定 baseline（如 Sentient/EagleEye 的链构造细节）但缺乏原文
  c. 涉及理论 claim（如 Poisson 假设是否会再次被批）需要红队挑战
- **默认路径**：先自主完善初版 → 形成可质询的草稿 → 用户决定是否再走 Round 13 外审

**下次会话恢复点**：
- 读取当前 `paper/sections/3_method.tex` 与 `paper-CN/sections/3_method.tex`
- 对照 §11.3 的核心改写决议（Φ mean-log、case-1/2、Φ/A/Alert 分离）
- 逐节梳理\"日志 → 因果链\"流水线：seed → bidirectional extension → Φ scoring → truncation → 输出链集 {C_i}
- 补全公式定义、算法伪代码、可行性自审三件套
