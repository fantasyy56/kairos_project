# Paper Rewrite Plan — v2

> **版本：v2**
> **日期：2026-06-23**
> **作者：fantinli + AI 协作**
> **范围：英文版 `paper/` + 中文版 `paper-CN/`**
> **前置文档：**
> - `Memory.md` §10（本轮增量）
> - 现有论文 `paper/sections/*.tex` 与 `paper-CN/sections/*.tex`
> - v1 改动已合入：§1 因果必要性段、§4.4.2 因果有效性论证、§4.4.3 进程生命周期、§4.5 双用途分工

---

## 0. 本次改写的 north star（必须铭记）

> **真正的亮点是把 APT 检测从"哪个区域可疑"重新定义为"恢复攻击的因果叙事"，并第一次给出"链的因果质量"这个本来不存在的可度量概念。**
>
> 工具（肘部检测、TGN、Branch-Weighted Coherence、Node Profiler 等）一律不进 abstract / contribution / conclusion，只在 §4 实现描述中出现。

任何修改若违反这一条，立即回滚。

---

## 1. 本轮改写要解决的元问题

v1 把"因果合法性"和"双用途分工"等理论论证补上去了，但**叙事重心没调**——仍然在以"我们做了一个有许多组件的系统"的姿态写论文。本轮要做两件事：

### 元问题 A：亮点错位
- 工具被当作亮点（A 类七项），真亮点被埋没（B 类五项），重要论证缺失（C 类三项）。
- 见下文 §3 全清单。

### 元问题 B：§1 的逻辑层次平铺
- 现在 §1 是"事实陈列 + 三个 limitation + 我们的方法"。
- 要改成"现象层（APT + 系统日志）→ 必要性合流 → 唯一剩余的技术难点 → Our approach"的递推叙事。
- limitation 不再单独成节，而是融入"现有方法在技术难点上各自如何不到位"。

---

## 2. 本轮改写的 framing 决议（铭记 v1 教训：决议先于动手）

### 决议 D1：TGN 在叙事核心中"消失"，不仅仅是换措辞
- **原方案（v1 之前）**：在 abstract / contributions / §4.3 反复声明"reused from KAIROS"。
- **本轮决议**：abstract / introduction / conclusion 完全不出现 TGN 三个字母；§4.3 章节标题去掉 "TGN"，改成 generic 的 "Seed Identification"；正文第一句明确 "framework is agnostic to the choice of edge-level detector"，KAIROS TGN 作为本工作具体实现的一种选择被提到。
- **rationale**：照搬感（fantinli 提出）+ 戏份错位（AI 诊断 A2）双重原因。这样未来真的要改 TGN 时论文核心叙事不需要重写。

### 决议 D2：§1 改用"现象层 → 必要性合流 → 技术难点 → Our approach"6 步递推
- **APT 现象层**只能从 APT 这一类攻击的本身特点（多步、低速、单步合法）讲起，**不能**从 DARPA 数据集特点讲起。DARPA 在论文中只能作为 evaluation 用的实例。
- **Provenance 现象层**讲内核全程在场 + 边级因果天然 + 完整防篡改。
- **必要性 + 可信性合流**这一段要让因果不再是"一种可选技术"，而是"两个现象层事实联合起来强迫只有因果是恰当语言"。
- **技术难点**只剩链级 over-approximation，由此引出 Our approach。
- 三个原 limitation 改写成"现有方法如何在这个技术难点上各自不到位"，融入 Our approach 段。

### 决议 D3：因果语义边界（dependency causality）必须在 abstract 出现一次
- v1 已在 §4.4.2 显式声明，但只此一处。
- abstract 加一句让 reviewer 看 abstract 三秒就知道我们在做哪种因果，避免"什么因果"的反复盘问。

### 决议 D4：Branch-Weighted Coherence 降级为 deployment-time refinement
- **不**整段去掉（fantinli 之前已锁定 ablation 含此项；保留实验数字）。
- **但**：abstract / contributions / conclusion 不再以"core metric"姿态强调它。Φ_bw 在 §4.4.2 末段以 "a deployment-time refinement that exploits a structural prior" 的措辞出现，明确写它**不是**度量本身，而是基于经验观察的实用增量。
- 保留 §7 limitations 中"may not hold for ransomware/worm"那段诚实标注。

### 决议 D5：Cross-platform → Cross-dataset
- 整篇论文里 "cross-platform automatic adaptation" 全部改成 "cross-dataset adaptation across DARPA Transparent Computing engagements"。
- 在 §7 future work 里点明"Windows ETW / OpTC 等真正跨平台评估留待未来工作"。

### 决议 D6：肘部检测下沉
- abstract / contributions / conclusion 只讲"discovery of the natural causal horizon from benign data"。
- 算法名词（elbow / 拐点）只在 §4.4.3 算法描述里出现一次，作为 implementation note，**不强调其名字**。

### 决议 D7：双用途分工 + 三层因果有效性 提升为 contribution
- 把 v1 已经写进 §4.4.3 / §4.5 的两段分工论证，从"埋藏在 §4 中"提升为 contribution 第二项。
- 三层因果有效性（边级内核观测 / 进程桥独占性 / 共享资源桥泊松干扰）从"埋藏在 §4.4.2"提升为 contribution 第一项的明确组成部分。
- contribution list 从 4 项 → 4 项，但内涵重排：

```
原 contribution list (v1):
  1. Causal Coherence Metric (with structural sparsity prior)
  2. Unsupervised calibration protocol (elbow-detection method)
  3. End-to-end detection system (with TGN reused from KAIROS)
  4. Empirical validation on DARPA TC

新 contribution list (v2):
  1. Chain-level detection paradigm grounded in dependency causality
     (含三层有效性论证 + Φ 度量 + 将 chain 从 post-hoc artifact 提升为 first-class detection unit)
  2. Principled benign-data dual usage
     (含 process-lifecycle calibration + extractor-procedural symmetry training)
  3. End-to-end system & empirical validation
     (TGN/Transformer/eCDF 等都是 instantiation, 一句话带过；DARPA E3/E5 cross-dataset)
  4. (可选第 4 项) Open-source release
```

### 决议 D8：abstract 字数预算
- 一段 abstract 控制在 ~250 词以内。
- 必进的两条最锋利论证：B1（kernel-observed vs inferred）、B2（chain-level as detection unit）。
- 其余下沉到 introduction。

### 决议 D9：先英文后中文，中文版减少机翻味
- 英文版改完 → fantinli 确认 → 再改中文版。
- 中文版**不**逐句翻译，以"在英文版的论证骨架上重新中文写作"为目标。
- 保留中文版里已有的成熟措辞（如 v1 §1 / §4.4.2 / §4.5 那几段）作为本轮的母版。

### 决议 D10：Memory.md 增量同步而非重写
- 本轮新增 §10 章节，不动 §1–§9。
- 历史路径（如 `/Users/lijunyou/代码/...`）保持不变——它们是当时真实发生过的事的记录。

---

## 3. 全清单：本轮 12 个具体改动 (decisions D1–D10 落地到改动 X1–X12)

### X1. Abstract 重写（同时影响 §0 英文 + 中文）
- **去掉**：基于肘部检测的校准协议、cross-platform、structural sparsity prior、reused from KAIROS、TGN 字样
- **加入**：
  - 第 1 句：定位到 "first APT detection system that operates directly at the granularity of causal event chains"
  - 第 2 句：声明 dependency causality 语义 + kernel-observed vs inferred
  - 第 3 句：陈述两个核心 contribution（causal validity argument + dual benign data usage）
  - 第 4 句：empirical highlight（保留 [X]% F1 占位 + 50× investigation cost reduction，cross-dataset 措辞）
  - 第 5 句：zero attack-side prior

### X2. §1 全章重组：6 步递推叙事
- 完全替换现有 §1 第 1-19 行，保留贡献清单和路线图但重排内容
- 新结构：
  - **§1.1 (无小标题，开篇段)**：APT 现象层（多步、低速、单步合法）—— 攻击是什么
  - **§1.2 (无小标题)**：Provenance 现象层（kernel-mediated, edge-level causality observed）—— 数据是什么
  - **§1.3**：必要性 + 可信性合流——为什么因果是这个问题的唯一恰当语言
  - **§1.4**：唯一剩下的技术难点（chain-level over-approximation）——需要解决什么
  - **§1.5**：Our approach + 4 项 contributions（按决议 D7 重排）
  - **§1.6**：路线图（保留现有最后一段）
- 三个原 limitation enumerate 列表删除，融入 §1.4 一段散文论述

### X3. Contributions list 重排（按 D7）
- 新 4 项见上文 D7
- 措辞要使每一项都正面声明"我们带来了什么"，不是"我们没带来什么的解释"

### X4. §3 Related Work 局部调整
- 第 18 行 "we do not claim novelty in the Transformer architecture" 保留
- 第 26 行 "weak individual signals can be amplified by the Transformer's self-attention over the full causal context" 保留
- 第 34 行 "previously empty position in the design space: model-free causal chain quality measurement" 保留但调整措辞为更中性的 "an under-explored direction: defining and measuring causal chain quality before extraction"
- **不**做大重排，因为 §1 已经承载了主要叙事

### X5. §4 整体结构调整
- §4.2 Node Profiler **从独立 subsection 降级**为 §4.3 Seed Identification 第二段（feature engineering description）
- §4.3 章节标题：`TGN Seed Identification` → `Seed Identification`
- §4.3 第一句：明确 "framework is agnostic to the choice of edge-level anomaly detector; we adopt KAIROS's pretrained TGN as one instantiation"
- §4.4 (Causal Coherence Metric) 加新开篇段 "Design Principle: Separation of Physical Causality and Semantic Anomaly"（落地 B4）
- §4.5.1 "Why Autoregressive" 整 subsection **删除**，并入 §4.5 Architecture and Training 一句话
- §4.6 (Detection via Component-wise eCDF) 末段加一句 "this aggregation rule is orthogonal to our causal contribution; we describe it for reproducibility"

### X6. §4.4.2 Φ_bw 段调整
- 现 v1 三个 case 的 OS 原理论证 + Poisson 推导保留
- "Branch-Weighted Coherence" 标题 + 公式保留
- 但**新增**一句话开头："Equation~\ref{eq:phi_bw} introduces a deployment-time refinement that exploits a structural prior; it is **not** part of the causal coherence definition itself but a precision-improving heuristic motivated by empirical observation."
- 保持 §7 limitations 现有诚实标注

### X7. §4.4.3 校准协议措辞调整
- 现 v1 进程生命周期论证保留
- 但**移除**对"elbow-detection"作为 selling point 的强调
- 第 1 段措辞从"We propose an elbow-detection protocol"改成"We propose a **calibration protocol** that discovers the natural causal horizon of an operating system from benign data alone. Concretely, the protocol identifies the inflection point on the $\chainCoherence$-vs-$\hoplimit$ curve..."（hopkin / inflection / elbow 三选一作为算法术语，不再是亮点术语）

### X8. §6 Cross-Dataset 措辞调整
- §6.2 标题 "Cross-Dataset Generalization" 保留
- "automatic cross-platform adaptation" → "cross-dataset adaptation across DARPA Transparent Computing engagements"
- §6.2 expected outcome 中"OS-specific adaptation"→"engagement-specific adaptation"

### X9. §7 Discussion 增加 framing 段
- 加一段 "Why Chain-Level Detection Was Out of Reach"（落地 C3）
- 内容：chain-level detection 长期没人做不是因为有 fundamental 障碍，是因为没有"chain quality 不依赖 attack pattern 知识"的定义；本工作正是补这个缺口

### X10. §8 Conclusion 重写
- 同 abstract 的口径调整（不提 elbow / cross-platform / TGN reused / structural sparsity prior 作为亮点）
- 强调三件事：
  - chain-level detection paradigm
  - dependency causality + kernel-observed edges
  - dual benign data usage with independent theoretical foundations

### X11. References 不动
- 这一轮不增加引用
- King-Backtracking 已在 v1 中加入，足够

### X12. 中文版同步改写
- 不逐句翻译英文版
- 在英文版改完后，以现有中文版 §1 / §4.4.2 / §4.4.3 / §4.5 v1 段落为母版，按英文版新结构在中文论证骨架上重新写作
- 减少"机器翻译感"的具体手段：
  - 长定语前置 → 短句串联
  - 被动语态 → 主动语态
  - 形式主语 → 实体主语
  - 直译的英文连接词（"因此"、"由此"）→ 中文自然连接

---

## 4. 改动顺序与确认点

按下列顺序，在每个确认点等 fantinli 拍板后再继续：

```
英文版改动:
  X1 (abstract) → 确认 ●
  X2 + X3 (intro 全章) → 确认 ●
  X4 (related work 局部) → 确认 ●
  X5 (§4 结构) + X6 + X7 (§4.4.2/3) → 确认 ●
  X8 + X9 (§6/§7) → 确认 ●
  X10 (conclusion) → 确认 ●

中文版改动 (英文版整体确认后):
  X12 全部按英文版新结构重写，分节 → 确认 ●

最后:
  Memory.md §10 总结 → 完成
```

每个确认点 fantinli 可以选择：
- **GO**：直接进入下一改动；
- **HOLD**：当前改动有需要调整的地方，就地修复后再 GO；
- **ROLLBACK**：当前改动方向错了，回滚到改动前。

---

## 5. 不在本轮做的事（明确划界，避免边界蔓延）

- **不**做实验或跑代码——本轮纯文本改写
- **不**新增引用（除非 GPT-5.5 review 强烈要求）
- **不**改 §5 metric validation 的实验设计（该节实验占位待真实数据后再确认）
- **不**改 §6 main results table 的具体数字（占位 [X] 等数字保留）
- **不**改 main.tex 的 documentclass（已在 v1 切到 IEEEtran，本轮不动）
- **不**改 references.bib

---

## 6. 与 GPT-5.5 外审的关系

本 PLAN 与英文版 v2 改动完成后，作为外审材料发给 GPT-5.5 review。
外审 prompt 详见 `auto-paper-improvement-loop/SKILL.md` Step 2 模板。
本 PLAN **不**发给 reviewer——只发改完的论文（防止 reviewer-bias）。

---

## 7. 附：v1 已合入但需要在 v2 中保护的内容

下列内容在 v1 改写中已经合入论文，本轮 v2 必须保护、不得意外覆盖：

- §1: "Why causality is intrinsic to APT detection" 那一段（v1 加入）
- §1: "kernel-observed vs inferred" 那一段（v1 加入）
- §4.4.2: "Causal validity of φ" paragraph + Poisson 推导（v1 加入）
- §4.4.2: 三个 case 的合法性升级措辞（v1 加入）
- §4.4.3: "Choice of calibration chains: process lifecycles" paragraph（v1 加入）
- §4.5: "Training chains: distributional symmetry" paragraph（v1 加入）

v2 是**在 v1 之上的进一步重构**，而非推翻 v1。

---

*生成于 2026-06-23 由 fantinli + AI 在 PAPER_REWRITE_PLAN v1（隐式存在于会话）基础上整理为 v2 显式蓝图。*
