# 论文贡献分析

---

## 一、贡献声明

**唯一的贡献声明**：我们提出了一个模型无关的因果相干性度量（Causal Coherence Metric, Φ_bw），以及一个仅从良性数据自动发现 OS 自然因果视野的无监督校准协议。

其他所有组件——Causal Chain Extractor 算法、自回归 Transformer、eCDF 检测头——都是支撑这套度量体系的工作机制。Transformer 在这篇论文里的地位等同于实验仪器：不声称它是贡献，但它不是随便选的。

---

## 二、为什么这不是增量工作

### 2.1 已有方法的共同缺陷

所有前人方法把"链提取"当作一个**切分问题**——怎么把大图切成小块/小序列。切分质量由下游模型效果间接验证。一条链好不好，只能靠训练一个模型跑一遍才知道。

| 方法 | 切分策略 | 根本缺陷 |
|------|---------|---------|
| EagleEye (eCrime 2024) | 固定时间窗口 | 因果无关的事件被塞进同一个窗口 |
| Sentient (AAAI 2026) | 随机游走场景分割 | 可能逆因果边走，方向错误 |
| GET-AID (ESORICS 2025) | 时间子图 | 时间相近 ≠ 因果相关 |
| SPARSE (2024) | 规则基语义路径评分 | 需要专家规则和威胁情报，检测不了新攻击 |
| CAGE / SLOT / EdgeTrace | 先检测节点/边，后拼接成路径 | 链质量被上游检测 recall 卡死——漏一个节点链就断了 |

**共同的根本问题**：没有人先定义"什么是好链"再提取。所有人都是先切了再说，模型说好就是好。

### 2.2 我们的根本不同

把链提取当作一个**度量问题**——先定义什么是"好链"，然后直接度量。**不需要训练任何模型就能知道一条链的因果结构质量。**

这就是不可替代性的根源：别人是"切了再说"，我们是"先定义好，然后按定义切，模型只是验证"。

---

## 三、子贡献拆解

### 3.1 Causal Coherence Metric (Φ_bw)

这不是"又一个 similarity metric"。不可替代性来自三点：

#### (a) 三分法 φ 函数

```
φ(e_i, e_{i+1}):

  Identity-preserving bridge (d_i=0, node=subject):
    exp(-α · d_i)
    进程身份由内核保证，时间间隔无关紧要。β≈0。

  Stateful bridge (d_i=0, node=file/netflow):
    exp(-α · d_i) · exp(-β · Δt_i)
    文件/套接字是共享资源，可被第三方覆写。时间越久因果越不可靠。

  Indirect path (0 < d_i ≤ δ):
    exp(-α · d_i) · exp(-β · Δt_i)
    概率性因果连接，时间施加衰减。
```

**为什么这个三分法不是 ad-hoc**：它来自 OS 的基本原理。进程是 capability（内核保证内存空间独占，PID 不可伪造），文件是 shared resource（任何有权限的进程可随时修改）。provenance graph 的 node type schema 已经编码了这个区分，无需额外标注。

#### (b) 分支加权惩罚 (Structural Sparsity Prior)

```
Φ_bw(C) = Φ(C) · exp(-λ · BF(C))
```

BF(C) = 链中所有非终端节点的平均出度。

正常进程（Firefox 开网页 50 条 WRITE、编译过程上千条事件）有 power-law 高分支出度。攻击链（nginx exploit → shell → wget → exfiltrate）是近似线性的——每步一个因果后继。这个惩罚项让攻击链在排序中胜过良性高分支链。

λ 不需要人工调——通过良性数据分位数自动校准。

#### (c) 模型无关可验证性

不需要等到 Transformer 训练完才知道 metric 好不好。Benign chains vs Random chains 的 Φ_bw 分布直方图 + AUC，在训练任何模型之前就能验证 metric 的区分能力。10 条攻击链在这个阶段是**case study**，不是 statistical evidence——统计证据来自 benign vs random 的对比。攻击链作为结构化流程，预测也具有高物理相干性（遵守 OS 物理规律），但它们在语义上偏离——留给 Transformer 去发现。

---

### 3.2 无监督校准协议

**定义 metric 不难，参数怎么定才是难点。** 如果 δ 需要人工调，"heuristic parameter tuning" 就是直接拒稿信号。

#### Elbow Detection

在良性数据上固定种子，δ 从 1 变到 10，画出 Φ-δ 曲线，找肘部（二阶导数最负处）——这就是 OS 的自然因果视野。

**为什么肘部一定存在**：随着 δ 增大，先是真正有因果关联的事件被纳入（Φ 上升），然后是无意义关联被强行拉入（Φ 上升放缓），最后所有链都回溯到 init/PID 1（Φ 反而下降——整个 OS 的事件都被进来了）。肘部是有效因果和噪声的边界。OS 的因果深度是有限的。

**跨 OS 自动适配**：Linux auditd 和 Windows ETW 日志粒度不同，同一个 δ=3 在两个 OS 上含义完全不一样。肘部会在不同 OS 上自动落到不同位置。**这个自动适配性才是贡献的核心，metric 公式本身只是载体。**

#### 为什么不是 trivial maximization

如果校准目标是"最大化 Φ"，最优解是 α=0, β=0, δ=∞——所有链的 Φ=1，完全无意义。肘部方法不存在这个问题：超过肘部后增大的 δ 拉进来的是噪声，Φ 不再上升。肘部天然惩罚"过度宽松"。

---

### 3.3 自回归 Transformer（非贡献，但选择有论证）

**定位**：验证 Coherence Metric 有效性的实验仪器。不声称是贡献。物理学家不会声称"我们发明了显微镜"——但需要解释为什么选电镜而不是光学镜。

**为什么是自回归而非 MLM/BERT**：Provenance graph 中因果严格向前流动。MLM 允许模型向前看未来的事件来重建过去的事件——可以"cheat"。自回归强制模型仅从历史因果事件构建表示。当攻击链偏离良性自回归分布时，预测误差 spike。这和 Coherence Metric 的因果方向性一脉相承。

**为什么是序列 Transformer 而非 Graph Transformer**：Sentient 和 GET-AID 都在图空间做 attention。我们选择序列 Transformer 是因为因果链天然是序列化的——事件按因果方向排列，时序编码保留间隔信息。图 attention（如 GAT）丢失了事件的严格顺序。这是在方法论上和 Sentient/GET-AID 的区别。

---

## 四、Reviewer 视角的攻防

### 正面评价

> "The Causal Coherence Metric is model-free, verifiable before any model training, and the calibration protocol is genuinely unsupervised. The three-case φ function's grounding in OS capability vs. shared resource semantics is principled, not ad-hoc. The elbow method for discovering causal horizon is elegant. The structural sparsity prior exploits a genuine power-law property of OS process trees."

### 可能的攻击 & 防御

**攻击 1**: "The metric is just three exponential decays multiplied together. What's the theoretical guarantee that high Φ_bw correlates with attack relevance?"

**防御**: "Attack relevance is **not claimed** as a property of Φ_bw. Φ_bw measures causal structural integrity — it tells you which chains genuinely follow OS causality. Whether a causally-coherent chain is an attack is the Transformer's job. **Separation of concerns**: metric = physical causality, Transformer = semantic anomaly. High Φ_bw is necessary but not sufficient for attack detection — the attack chain in E3 has high Φ_bw (attacks follow OS physics), but so do many benign chains. The Transformer disambiguates."

**攻击 2**: "The elbow method is just a heuristic. Why not use MDL or Bayesian model selection?"

**防御**: "MDL on dense provenance graphs is computationally prohibitive (requires computing description length over 268K nodes and 29.7M edges). The elbow method is deterministic, interpretable, and verifiable — the Φ-δ curve can be plotted and inspected. We show empirically on E3 + E5 that the elbow produces parameters that transfer across datasets. Formal model selection is future work."

**攻击 3**: "EagleEye already does Transformer on provenance sequences. This is EagleEye + a graph traversal heuristic."

**防御**: "EagleEye's fixed windows mix causally unrelated events. Our causal chains follow provenance edge direction. This is not a minor preprocessing difference — we ablate causal tracing vs fixed windows and show >10% absolute F1 improvement. Furthermore, EagleEye requires labeled malware samples for training (binary classifier). Our method trains entirely on benign data (self-supervised autoregressive), requiring zero attack labels — a fundamentally different and more realistic threat model."

**攻击 4**: "DARPA E3 only has 10 ground-truth attack chains. This is not statistically significant."

**防御**: "The 10 attack chains are **case studies** for the end-to-end pipeline, not statistical evidence. Our statistical claims rest on: (a) benign vs random chain Φ_bw separation (abundant data, model-free), (b) chain-level F1 computed across thousands of benign chains and 10 attack chains — we report per-chain metrics, not aggregate-only, and use bootstrap confidence intervals. We also validate on StreamSpot and DARPA E5 to demonstrate consistency across multiple attack instances."

---

## 五、一句话总结

> 我们证明了，通过一个模型无关的因果相干性度量——根植于 OS 的 capability-vs-shared-resource 原理，参数通过良性数据上的肘部检测自动发现——提取出的因果链在 APT 检测上始终优于窗口基、随机游走基、子图基和后处理拼接基的链提取方法，且在跨 OS 环境中参数自动适配。
