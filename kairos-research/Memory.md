# Session Memory — Kairos 改进方案讨论

> 最后更新：2026-06-17
> 详细技术设计记录：`./design-notes.md`
> 论文贡献分析：`./contribution-analysis.md`
> 最终方案：`./refine-logs/FINAL_PROPOSAL.md`
> 论文框架：`./PAPER_PLAN.md`

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
