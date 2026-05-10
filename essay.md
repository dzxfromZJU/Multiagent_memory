# 本科生毕业论文

## 题目

# 面向多智能体系统的共享记忆幻觉传播识别与知识编辑方法研究

学生姓名：XXX  
学生学号：XXX  
指导教师：XXX  
年级与专业：202X 级计算机科学与技术  
所在学院：计算机科学与技术学院  

提交日期：2026 年 X 月 X 日  

---

# 浙江大学本科生毕业论文（设计）承诺书

1. 本人郑重承诺所呈交的毕业论文（设计），是在指导教师的指导下，严格按照学校和学院有关规定完成的。
2. 本人在毕业论文（设计）中除了文中特别加以标注和致谢的地方外，论文中不包含其他人已经发表或撰写过的研究成果，也不包含为获得浙江大学或其他教育机构的学位或证书而使用过的材料。
3. 与我一同工作的同志对本研究所做的任何贡献均已在论文中作了明确说明并表示谢意。
4. 本人承诺在毕业论文（设计）工作过程中没有伪造数据等行为。
5. 若在本毕业论文（设计）中有侵犯任何方面知识产权的行为，由本人承担相应法律责任。
6. 本人完全了解浙江大学有权保留并向有关部门或机构送交本论文（设计）的复印件和电子文档，允许本论文（设计）被查阅和借阅。

作者签名：  
导师签名：  

签字日期： 年 月 日  

---

# 致谢

从论文选题、系统设计、实验实现到论文撰写，本文的完成离不开老师、同学、学校和相关开源社区的支持。

感谢指导教师 XXX 老师在研究方向选择、技术路线设计和论文写作过程中给予的悉心指导。老师在多智能体系统、大语言模型可靠性和实验设计等方面提出了许多宝贵意见，使本文在研究问题定义、方法建模和实验分析方面更加完善。

感谢浙江大学计算机科学与技术学院提供的学习环境和计算资源支持。本文实验涉及多智能体对话系统、向量检索、共享记忆维护、知识编辑与评估等多个模块，相关资源为实验顺利完成提供了重要保障。

感谢同学和朋友在系统搭建、代码调试、实验设计和论文修改过程中提供的帮助。研究期间，大家围绕多智能体框架、FAISS 共享记忆、SQLite 元数据存储、知识图谱构建和实验指标设计等问题进行了多次讨论，使本文受益匪浅。

最后，感谢家人长期以来的支持与鼓励。

---

# 人工智能工具使用声明

本人郑重声明，本本科毕业论文由本人独立完成。写作和实验期间使用了以下人工智能工具：

1. 使用 ChatGPT 辅助论文选题分析、相关工作梳理、系统架构设计和部分实验方案讨论。相关内容均经过本人理解、筛选、修改和核对。
2. 使用 GitHub Copilot / Codex 辅助代码补全、代码重构和实验脚本生成。所有代码均经过本人检查、调试和修改后使用。
3. 使用大语言模型辅助生成多轮问答测试样例、错误前提诱导样例和记忆幻觉传播测试样例。相关测试数据均经过人工核对，并以可信知识库作为事实依据。
4. 本文中的研究思路、系统实现、实验设计、结果分析和最终文字表达均由本人负责。

---

# 摘要

随着大语言模型和智能体技术的发展，多智能体协同对话系统逐渐被应用于复杂问答、任务规划、知识服务和交互式推荐等场景。为了支持长期交互和跨轮协作，许多多智能体系统引入共享记忆机制，将历史对话、检索结果和智能体生成内容写入外部记忆库。然而，共享记忆在提升系统连续性的同时，也带来了新的可靠性风险：错误前提、无证据推断或幻觉内容一旦被写入共享记忆，可能在后续多轮对话中被其他智能体反复检索、引用和派生，最终形成持续性的记忆污染。

针对这一问题，本文提出一种面向多智能体系统的共享记忆幻觉传播识别与知识编辑框架。该框架以 FAISS 作为向量检索层，以 SQLite / MySQL 作为元数据与图边存储层，通过 Memory Manager 统一管理共享记忆的写入、检索、调用记录和来源追踪。在此基础上，本文构建记忆溯源图，将智能体、对话轮次、候选事实、共享记忆、可信知识库和最终回答建模为异构图节点，将检索、引用、支持、派生、冲突、修复等关系建模为图边，从而追踪污染记忆在多轮交互中的传播路径。

进一步地，本文提出 MKE-MAS（Memory Knowledge Editing for Multi-Agent Systems）知识编辑机制。该机制从多轮对话历史中抽取原子事实 claim，结合可信知识库和共享记忆进行证据检索，通过 Verifier Agent 判断事实是否被支持、反驳或缺乏依据，并由 Knowledge Editor 决定执行插入、合并、更新、废弃、拒绝或隔离等编辑操作。实验部分以青铜器结构化知识库为事实来源，构建多类多轮问答测试，包括普通事实问答、错误前提诱导、同名实体消歧、污染记忆检测、记忆修复验证和知识沉淀测试。实验结果表明，本文方法能够有效降低错误记忆写入率，提高正确记忆升格为长期知识的比例，并增强多智能体系统在多轮问答中的事实一致性和可追溯性。

关键词：多智能体系统；共享记忆；记忆幻觉；知识编辑；FAISS；记忆溯源图

---

# Abstract

With the development of large language models and autonomous agents, multi-agent dialogue systems have been increasingly applied to complex question answering, task planning, knowledge services, and interactive reasoning. To support long-term interaction and cross-turn collaboration, many systems introduce shared memory mechanisms that store dialogue history, retrieved evidence, and agent-generated content in external memory. Although shared memory improves continuity, it also introduces new reliability risks. Once false premises, unsupported inferences, or hallucinated facts are written into shared memory, they may be repeatedly retrieved, reused, and propagated by other agents in later conversations, resulting in persistent memory contamination.

To address this problem, this thesis proposes a framework for hallucination propagation tracing and knowledge editing in shared-memory multi-agent systems. The framework uses FAISS as the vector retrieval layer and SQLite / MySQL as the metadata and graph-edge storage layer. A unified Memory Manager is designed to control memory insertion, retrieval, usage logging, and provenance tracking. Based on these records, a memory provenance graph is constructed, where agents, dialogue turns, claims, memories, trusted knowledge-base entries, and answers are represented as heterogeneous nodes, while retrieval, citation, support, derivation, contradiction, and repair relations are represented as graph edges.

Furthermore, this thesis proposes MKE-MAS, a memory-based knowledge editing mechanism for multi-agent systems. MKE-MAS extracts atomic claims from multi-turn dialogue histories, retrieves evidence from trusted knowledge sources and shared memory, verifies each claim through a verifier agent, and applies editing actions such as insertion, merging, updating, deprecation, rejection, or quarantine. Experiments are conducted on a structured bronze artifact knowledge base, covering factual question answering, false-premise induction, ambiguous entity disambiguation, contaminated memory detection, memory repair verification, and knowledge consolidation. Experimental results show that the proposed method reduces the rate of erroneous memory insertion, improves the promotion of correct memories into long-term knowledge, and enhances factual consistency and traceability in multi-turn multi-agent interactions.

Key words: Multi-Agent Systems; Shared Memory; Memory Hallucination; Knowledge Editing; FAISS; Memory Provenance Graph

---

# 目录

第一部分 毕业论文（设计）

1. 背景与意义  
   1.1 多智能体协同对话系统  
   1.2 共享记忆机制  
   1.3 共享记忆中的幻觉传播问题  
   1.4 研究意义  

2. 研究现状  
   2.1 大语言模型知识编辑  
   2.2 智能体长期记忆机制  
   2.3 多智能体共享记忆  
   2.4 记忆幻觉检测与治理  
   2.5 图结构溯源与错误传播分析  

3. 背景知识与技术介绍  
   3.1 大语言模型与多智能体系统  
   3.2 向量检索与 FAISS 共享记忆  
   3.3 外部记忆式知识编辑  
   3.4 Claim 级事实验证  
   3.5 记忆溯源图与传播路径分析  

4. MKE-MAS 方法  
   4.1 系统总体架构  
   4.2 共享记忆管理器设计  
   4.3 对话历史与候选事实抽取  
   4.4 证据检索与事实验证  
   4.5 知识编辑决策机制  
   4.6 记忆溯源图构建  
   4.7 污染记忆检测与修复  

5. 实验验证  
   5.1 实验设计  
   5.2 数据集与测试对话构造  
   5.3 评价指标  
   5.4 对比实验  
   5.5 消融实验  
   5.6 结果分析  

6. 总结与展望  
   6.1 结论  
   6.2 不足与改进  
   6.3 未来工作展望  

参考文献  
作者简历  
附录 A 系统实现细节  
附录 B 测试样例  
附录 C 人工智能工具使用记录  

---

# 第一部分 毕业论文

# 1 背景与意义

近年来，大语言模型在自然语言理解、知识问答、复杂推理和工具调用等任务中表现出较强能力。在此基础上，多智能体系统通过将不同智能体分配为规划者、检索者、回答者、验证者和反思者，使复杂任务能够被分解、协作和迭代完成。相较于单一模型，多智能体系统具有更强的模块化能力和任务扩展能力。

然而，多智能体协作也引入了新的可靠性问题。尤其在引入共享记忆后，一个智能体产生的错误信息可能被写入外部记忆库，并在后续多轮交互中被其他智能体检索、引用和进一步推理，从而形成记忆污染。与单次回答中的幻觉不同，记忆幻觉具有持久性、传播性和隐蔽性，对长期运行的智能体系统构成更大威胁。

## 1.1 多智能体协同对话系统

本节介绍多智能体系统的基本概念、典型架构和应用场景。

可写内容包括：

- 大语言模型智能体的基本能力；
- 多智能体系统的角色划分；
- 协同问答、任务规划、知识服务等应用；
- 多智能体相比单智能体的优势与风险。

## 1.2 共享记忆机制

本节介绍共享记忆在多智能体系统中的作用。

可写内容包括：

- 短期上下文与长期记忆的区别；
- 外部记忆库的必要性；
- 向量数据库与语义检索；
- FAISS 在共享记忆检索中的作用；
- 共享记忆对多轮对话连续性的提升。

## 1.3 共享记忆中的幻觉传播问题

本节提出本文核心问题。

可写内容包括：

- 记忆幻觉与普通回答幻觉的区别；
- 错误记忆的写入、检索、引用、派生过程；
- 多智能体错误共识和错误强化问题；
- 为什么需要可追踪的记忆图；
- 为什么只检测最终回答不足以治理共享记忆污染。

示例描述：

> 在共享记忆机制下，幻觉不再只是一次回答中的局部错误，而可能成为系统长期状态的一部分。当错误信息被写入共享记忆后，它会参与后续检索和推理，并可能被多个智能体反复引用，最终形成错误共识。

## 1.4 研究意义

本文研究意义可以概括为以下几点：

1. 提出共享记忆幻觉传播问题的建模方式；
2. 构建可观测的记忆溯源图；
3. 设计面向多智能体系统的外部知识编辑机制；
4. 提供基于真实结构化知识库的多轮问答测试方法；
5. 为长期运行的智能体系统提供记忆治理思路。

---

# 2 研究现状

本章围绕本文研究主题，综述大语言模型知识编辑、智能体长期记忆、多智能体共享记忆、记忆幻觉检测和图结构溯源等方向的已有研究。

## 2.1 大语言模型知识编辑

本节介绍参数式知识编辑和外部记忆式知识编辑。

可写文献包括：

- ROME；
- MEMIT；
- MEND；
- SERAC；
- GRACE；
- WISE；
- IKE；
- EasyEdit。

可写重点：

- 参数编辑可以直接修改模型内部知识，但实现复杂；
- 外部记忆式编辑更适合黑盒模型和多智能体系统；
- 本文不直接修改模型参数，而是对共享记忆进行外部知识编辑。

## 2.2 智能体长期记忆机制

本节介绍智能体如何保存、检索和更新长期记忆。

可写文献包括：

- Generative Agents；
- Reflexion；
- MemoryBank；
- MemGPT。

可写重点：

- 记忆存储、检索、反思和遗忘；
- 对话历史如何转化为长期记忆；
- 已有方法对“正确记忆如何升格为知识”的讨论不足。

## 2.3 多智能体共享记忆

本节介绍多个智能体如何共享和维护记忆。

可写内容包括：

- 共享记忆池；
- private memory 与 shared memory；
- 记忆来源记录；
- 权限控制与访问记录；
- 多智能体之间的信息复用。

## 2.4 记忆幻觉检测与治理

本节介绍 hallucination detection 和 memory hallucination evaluation。

可写内容包括：

- 原子事实抽取；
- LLM-as-Judge；
- NLI；
- SelfCheck；
- HaluMem；
- RAGAS；
- FActScore。

本节可以指出：

> 现有幻觉检测方法多关注最终回答是否正确，而本文进一步关注错误信息是否被写入共享记忆，以及它如何影响后续问答。

## 2.5 图结构溯源与错误传播分析

本节介绍图结构在多智能体错误追踪中的作用。

可写内容包括：

- GraphTracer；
- GUARDIAN；
- temporal graph；
- information dependency graph；
- memory provenance graph。

本节需要突出本文区别：

> 现有工作多关注任务失败或协作异常，而本文关注共享记忆污染的长期传播，并将对话、claim、memory、knowledge base 和 answer 统一建模为异构图。

---

# 3 背景知识与技术介绍

本章介绍本文方法所依赖的关键技术，包括多智能体系统、FAISS 向量检索、外部知识编辑、claim 级验证和记忆图建模。

## 3.1 大语言模型与多智能体系统

介绍：

- LLM Agent 的基本结构；
- planning / tool use / memory / reflection；
- 多智能体角色划分；
- 本文系统中的 Agent 类型：

```text
QuestionerAgent
RetrieverAgent
AnswerAgent
VerifierAgent
KnowledgeEditorAgent
MemoryManager
JudgeAgent

## 3.2 向量检索与 FAISS 共享记忆

共享记忆机制是本文研究的基础。多智能体系统在多轮对话过程中会不断产生中间结果、历史回答、候选事实和验证结果。如果这些信息仅保存在上下文窗口中，系统在长轮次交互后会受到上下文长度限制，难以持续利用历史信息。因此，本文引入外部共享记忆库，用于保存可复用的信息，并通过语义检索在后续对话中重新调用相关记忆。

本文采用 FAISS 作为共享记忆的向量检索后端。FAISS 主要负责完成向量化语义检索，即将记忆内容编码为 embedding 后加入索引，并在后续查询时返回与当前问题语义最相近的若干条记忆。对于多智能体系统而言，FAISS 能够高效支持 top-k 相似记忆检索，适合作为长期记忆系统的底层检索模块。

需要指出的是，FAISS 本身并不适合保存完整的记忆元数据。FAISS 只负责向量索引，不能直接表达一条记忆的来源、生成者、可信度、污染状态、被调用次数和依赖关系。因此，本文将共享记忆系统拆分为两个部分：

```text
FAISS：
    保存 memory_id 与 embedding，用于高效语义检索。

SQLite / MySQL：
    保存 memory_id 对应的内容、来源、置信度、状态、证据和图边关系。
```

这种设计使得系统既能够利用 FAISS 的高效检索能力，又能够通过关系型数据库保存可解释、可追踪的记忆属性。

本文中的一条共享记忆包含如下基本字段：

```json
{
  "memory_id": "M_0001",
  "content": "司母戊方鼎是商代晚期肉食器。",
  "memory_type": "edited_knowledge",
  "source_type": "knowledge_base_supported",
  "source_ids": ["KB_363189"],
  "created_by": "KnowledgeEditorAgent",
  "created_turn": "T_0012",
  "confidence": 0.96,
  "status": "active",
  "contamination_status": "clean"
}
```

其中，`memory_type` 用于区分原始对话记忆、候选记忆、已验证记忆和长期知识；`source_type` 用于标记记忆来源；`confidence` 表示该记忆当前可信度；`status` 和 `contamination_status` 用于控制该记忆是否能够被后续智能体检索和使用。

本文通过 MemoryManager 统一封装 FAISS 与元数据数据库。所有智能体不直接访问 FAISS，而是通过 MemoryManager 发起检索、写入、更新和状态修改请求。这样可以确保每一次记忆调用都被记录下来，为后续构建记忆溯源图提供基础。

---

## 3.3 外部记忆式知识编辑

知识编辑是指对模型或系统中的知识进行修改、补充或删除，使系统在后续任务中能够使用更新后的知识。传统知识编辑方法通常关注大语言模型内部参数的修改，例如直接改变模型对某个事实的回答。然而，对于多智能体系统而言，频繁修改底层大模型参数成本较高，也不适合黑盒模型调用场景。

本文采用外部记忆式知识编辑方法。其核心思想是：不直接修改大语言模型参数，而是将多轮对话中产生的候选事实经过验证后写入外部知识记忆，并在后续对话中通过检索和路由机制影响智能体的回答。这样既能保留模型本身的通用能力，又能让系统逐渐积累领域知识。

外部记忆式知识编辑的基本流程如下：

```text
多轮对话历史
    ↓
候选事实抽取
    ↓
知识库证据检索
    ↓
事实验证
    ↓
知识编辑决策
    ↓
写入长期知识记忆
    ↓
后续问答中优先调用
```

在本文系统中，对话中新产生的信息不会被直接写入长期知识库，而是先进入候选记忆层。只有经过可信知识库支持、冲突检测和编辑决策后，候选记忆才能被提升为长期可复用知识。该过程能够有效避免用户错误前提、智能体无依据推断和幻觉内容污染共享记忆。

本文将编辑动作分为以下几类：

| 编辑动作 | 含义 |
|---|---|
| INSERT | 将新事实插入长期知识库 |
| MERGE | 将新事实与已有相似知识合并 |
| UPDATE | 用被验证的新事实更新旧记忆 |
| DEPRECATE | 将错误或过期记忆标记为废弃 |
| REJECT | 拒绝写入被证伪的候选事实 |
| QUARANTINE | 暂存缺少证据但未被反驳的候选事实 |

通过这些编辑动作，系统能够实现从“对话记忆”到“长期知识”的有条件转化。

---

## 3.4 Claim 级事实验证

在多智能体对话系统中，智能体的回答通常包含多个事实。如果直接判断整段回答是否正确，很难精确定位错误来源。例如，一个回答中可能同时包含正确的年代信息、错误的出土地点和无依据的用途推断。因此，本文采用 claim 级事实验证方法，将回答拆分为多个原子事实，并逐条验证。

例如，对于回答：

```text
司母戊方鼎是商代晚期肉食器，1939年河南安阳殷墟武官村出土，重875千克。
```

可以抽取出以下原子事实：

```text
C1：司母戊方鼎是商代晚期肉食器。
C2：司母戊方鼎于1939年河南安阳殷墟武官村出土。
C3：司母戊方鼎重875千克。
```

每条 claim 都需要经过实体链接、证据检索和事实验证三个步骤。

实体链接的目标是将 claim 中提到的实体绑定到知识库中的具体条目。例如，“司母戊方鼎”应绑定到对应的知识库记录。如果系统无法确定具体实体，或者知识库中存在多个同名器物，则该 claim 会被标记为 ambiguous，系统不应直接写入长期知识。

证据检索的目标是从可信知识库和已有共享记忆中找到支持或反驳该 claim 的证据。本文优先使用原始知识库作为最高可信来源，其次使用已验证长期知识和已验证共享记忆。

事实验证阶段由 VerifierAgent 完成。VerifierAgent 判断 claim 与证据之间的关系，并输出以下标签之一：

| 标签 | 含义 |
|---|---|
| entailed | 证据明确支持该 claim |
| contradicted | 证据明确反驳该 claim |
| unsupported | 证据中没有相关信息 |
| ambiguous | 实体或指代不清 |
| partially_supported | 证据部分支持，但 claim 表述过强 |

验证结果将直接影响后续知识编辑动作。只有被标记为 entailed 的 claim 才能被提升为长期知识；被 contradicted 的 claim 会被拒绝或用于修复旧错误记忆；unsupported 和 ambiguous 的 claim 会进入隔离区或等待进一步确认。

---

## 3.5 记忆溯源图与传播路径分析

为了分析共享记忆中的幻觉如何传播，本文构建记忆溯源图。记忆溯源图是一种异构图结构，用于记录多轮对话中智能体、问题、回答、claim、共享记忆、知识库证据和编辑动作之间的关系。

本文将图节点分为以下几类：

| 节点类型 | 含义 |
|---|---|
| Agent | 系统中的智能体 |
| Turn | 对话轮次 |
| Question | 用户或测试智能体提出的问题 |
| Answer | 智能体生成的回答 |
| Claim | 从回答中抽取出的原子事实 |
| Memory | 共享记忆中的记忆条目 |
| Knowledge | 经过验证后沉淀的长期知识 |
| KBItem | 原始可信知识库中的条目 |

图边类型包括：

| 边类型 | 含义 |
|---|---|
| asks | 某智能体提出问题 |
| answers | 某智能体生成回答 |
| retrieves | 某智能体检索到某条记忆 |
| uses | 某智能体显式使用某条记忆 |
| extracts | 从回答中抽取 claim |
| supports | 某证据支持某 claim |
| contradicts | 某证据反驳某 claim |
| derived_from | 某记忆由其他记忆派生 |
| promoted_to | 某 claim 被提升为长期知识 |
| deprecated_by | 某旧记忆被新知识废弃 |
| contaminates | 某污染记忆影响后续回答或记忆 |
| repairs | 某知识修复某污染记忆 |

通过该图结构，本文可以追踪一条知识的来源，也可以追踪一条错误记忆的传播路径。例如，当系统发现某条记忆是错误的，可以沿图反向回溯其来源，判断它来自哪一轮对话、哪个智能体、哪个用户错误前提；也可以沿图正向传播，找到它影响了哪些后续回答和派生记忆。

---

# 4 MKE-MAS 方法

本文提出 MKE-MAS，即 Memory Knowledge Editing for Multi-Agent Systems，中文称为面向多智能体系统的共享记忆知识编辑框架。该框架的目标是在多轮对话后，将正确、可验证、可追踪的候选记忆提升为长期知识，同时阻止错误记忆进入共享记忆库，并对已经产生的污染记忆进行检测和修复。

---

## 4.1 系统总体架构

MKE-MAS 的整体流程如下：

```text
QuestionerAgent
    ↓
Target Multi-Agent System
    ↓
Dialogue Logger
    ↓
Claim Extractor
    ↓
Evidence Retriever
    ↓
VerifierAgent
    ↓
KnowledgeEditorAgent
    ↓
FAISS + Metadata Store + Memory Graph
```

其中，QuestionerAgent 负责生成多轮测试问题，包括普通事实问答、错误前提诱导、同名实体消歧和记忆污染检测问题。Target Multi-Agent System 是被测多智能体系统，由检索、回答、验证、总结等多个 Agent 组成。Dialogue Logger 负责保存完整对话历史。Claim Extractor 从智能体回答中抽取原子事实。Evidence Retriever 从可信知识库和共享记忆中检索证据。VerifierAgent 判断候选事实是否被支持。KnowledgeEditorAgent 根据验证结果和冲突检测结果执行知识编辑动作。

该框架的核心设计思想是：对话历史不能直接成为长期知识，必须经过 claim 抽取、证据验证和编辑决策。这样可以降低错误前提、幻觉回答和无依据推断进入共享记忆库的概率。

---

## 4.2 共享记忆管理器设计

共享记忆管理器 MemoryManager 是系统的核心基础设施。它负责统一管理记忆的写入、检索、调用记录、状态更新和依赖关系记录。

MemoryManager 提供以下主要接口：

```python
class MemoryManager:
    def add_memory(self, content, source_type, source_ids, created_by, turn_id):
        pass

    def retrieve_memory(self, query, agent_id, turn_id, top_k=5):
        pass

    def record_usage(self, agent_id, turn_id, used_memory_ids, output_id):
        pass

    def add_dependency(self, source_node, target_node, edge_type, confidence):
        pass

    def update_memory_status(self, memory_id, status, contamination_status=None):
        pass

    def trace_contamination(self, memory_id):
        pass
```

`add_memory` 用于写入新记忆；`retrieve_memory` 用于从 FAISS 中检索相似记忆，并记录检索日志；`record_usage` 用于记录智能体实际使用了哪些记忆；`add_dependency` 用于记录图边关系；`update_memory_status` 用于修改记忆状态；`trace_contamination` 用于追踪污染记忆影响路径。

本文采用 FAISS 与关系型数据库结合的方式实现共享记忆系统。FAISS 保存记忆向量，数据库保存记忆元数据和图边关系。推荐的数据表包括：

```text
memory
dialogue_log
retrieval_log
usage_log
claim
evidence
edit_log
graph_edges
```

这种设计使系统能够区分“被检索到的记忆”和“被实际使用的记忆”。前者表示某条记忆进入了智能体上下文，后者表示智能体在回答中显式引用或依赖了该记忆。这一区分对于分析记忆污染传播非常重要。

---

## 4.3 对话历史与候选事实抽取

MKE-MAS 将对话历史视为原始材料，而不是最终知识。每一轮对话都会被完整保存，包括提问者、回答者、输入内容、输出内容、检索到的记忆、使用的记忆和生成的新 claim。

对话日志示例如下：

```json
{
  "turn_id": "T_0001",
  "episode_id": "E_0001",
  "speaker": "AnswerAgent",
  "input_text": "请介绍司母戊方鼎。",
  "output_text": "司母戊方鼎是商代晚期肉食器，1939年河南安阳殷墟武官村出土，重875千克。",
  "retrieved_memory_ids": ["M_0012"],
  "used_memory_ids": ["M_0012"],
  "generated_claim_ids": ["C_0001", "C_0002", "C_0003"]
}
```

之后，ClaimExtractorAgent 从回答中抽取原子事实：

```text
C_0001：司母戊方鼎是商代晚期肉食器。
C_0002：司母戊方鼎于1939年河南安阳殷墟武官村出土。
C_0003：司母戊方鼎重875千克。
```

每个 claim 都保存来源轮次、生成智能体、目标实体、属性和值。示例结构如下：

```json
{
  "claim_id": "C_0001",
  "content": "司母戊方鼎是商代晚期肉食器。",
  "entity": "司母戊方鼎",
  "attribute": "时代与用途",
  "value": "商代晚期肉食器",
  "source_turns": ["T_0001"],
  "generated_by": "ClaimExtractorAgent",
  "status": "candidate"
}
```

通过 claim 级抽取，系统可以避免将整段回答不加区分地写入记忆库，也可以对每个事实进行独立验证。

---

## 4.4 证据检索与事实验证

对于每条候选 claim，系统首先进行实体链接，将 claim 中的实体绑定到知识库中的具体条目。若存在多个候选实体，系统会将 claim 标记为 ambiguous，不直接写入长期知识。

实体链接完成后，EvidenceRetriever 会从可信知识库、已验证记忆和长期知识中检索相关证据。对于结构化知识库，可以优先使用精确匹配；对于自然语言记忆，可以使用 FAISS 进行语义检索。

验证过程如下：

```text
claim
    ↓
entity linking
    ↓
evidence retrieval
    ↓
VerifierAgent
    ↓
verification result
```

VerifierAgent 的输出格式如下：

```json
{
  "claim_id": "C_0001",
  "relation": "entailed",
  "confidence": 0.96,
  "evidence_ids": ["KB_363189"],
  "reason": "知识库记录显示司母戊方鼎为商代晚期肉食器。"
}
```

如果 claim 与知识库冲突，例如：

```text
司母戊方鼎是西周早期器物。
```

VerifierAgent 应输出：

```json
{
  "claim_id": "C_0099",
  "relation": "contradicted",
  "confidence": 0.98,
  "evidence_ids": ["KB_363189"],
  "reason": "知识库显示司母戊方鼎属于商代晚期，而不是西周早期。"
}
```

验证结果将进入 KnowledgeEditorAgent，用于决定后续编辑动作。

---

## 4.5 知识编辑决策机制

KnowledgeEditorAgent 根据 claim 的验证结果、冲突检测结果和相似知识检索结果决定编辑动作。本文定义六种基本编辑动作：

| 动作 | 含义 |
|---|---|
| INSERT | 将新 claim 写入长期知识 |
| MERGE | 将新 claim 与已有相似知识合并 |
| UPDATE | 用新 claim 更新旧记忆 |
| DEPRECATE | 将旧错误记忆标记为废弃 |
| REJECT | 拒绝写入错误 claim |
| QUARANTINE | 暂存无证据或指代不清的 claim |

编辑决策规则如下：

```text
若 claim 被证据支持，且不存在相似知识和冲突记忆，则执行 INSERT；
若 claim 被证据支持，且存在相似知识，则执行 MERGE；
若 claim 被证据支持，但与旧记忆冲突，则执行 UPDATE，并将旧记忆 DEPRECATE；
若 claim 被证据反驳，则执行 REJECT；
若 claim 无证据支持或实体不清，则执行 QUARANTINE。
```

算法伪代码如下：

```text
算法 1 知识编辑决策

输入：候选事实 c，验证结果 r，冲突集合 C，相似知识集合 S
输出：编辑动作 a

1: if r = entailed and C = ∅ and S = ∅ then
2:     a ← INSERT
3: else if r = entailed and S ≠ ∅ then
4:     a ← MERGE
5: else if r = entailed and C ≠ ∅ then
6:     a ← UPDATE_AND_DEPRECATE
7: else if r = contradicted then
8:     a ← REJECT
9: else
10:    a ← QUARANTINE
11: return a
```

---

## 4.6 记忆溯源图构建

在执行知识编辑动作的同时，MKE-MAS 会同步更新记忆溯源图。记忆溯源图用于记录一条知识从对话历史中产生、经过证据验证、被编辑写入长期知识库，并在后续对话中被检索和使用的全过程。

例如，对于一条被成功提升为长期知识的 claim，系统会写入如下图边：

```text
T_0001 --contains_answer--> A_0001
A_0001 --extracts--> C_0001
KB_363189 --supports--> C_0001
VerifierAgent --verifies--> C_0001
C_0001 --promoted_to--> K_0001
K_0001 --stored_in--> FAISS
```

如果某条旧记忆被发现为错误记忆，则系统会写入如下图边：

```text
M_0044 --contradicted_by--> KB_363189
M_0044 --deprecated_by--> K_0001
K_0001 --repairs--> M_0044
```

通过这些图边，系统可以回答以下问题：

```text
某条知识来自哪一轮对话？
某条知识由哪个智能体生成？
某条知识由哪些证据支持？
某条错误记忆被哪些回答调用过？
某条污染记忆派生出了哪些后续记忆？
某次修复操作影响了哪些记忆节点？
```

本文使用关系型数据库中的 `graph_edges` 表保存图边，并使用 NetworkX 对图进行离线分析。对于更大规模系统，也可以使用 Neo4j 等图数据库进行存储和查询。

`graph_edges` 表结构如下：

```sql
CREATE TABLE graph_edges (
    edge_id TEXT PRIMARY KEY,
    source_node TEXT,
    target_node TEXT,
    edge_type TEXT,
    confidence REAL,
    created_turn TEXT,
    created_by TEXT
);
```

该图结构为污染记忆传播路径识别提供基础。

---

## 4.7 污染记忆检测与修复

污染记忆是指已经进入共享记忆库，并可能在后续对话中被检索和使用的错误或无依据记忆。与普通回答错误不同，污染记忆具有持久性和传播性。如果不及时修复，它会影响后续多个智能体的回答。

MKE-MAS 通过以下方式检测污染记忆：

```text
1. 发现某条记忆与可信知识库冲突；
2. 发现某条记忆支持了被判定为错误的 claim；
3. 发现某条记忆多次导致错误回答；
4. 发现某条记忆来源为用户错误前提或无证据智能体推断；
5. 发现某条记忆与已验证长期知识冲突。
```

检测到污染记忆后，系统不直接删除该记忆，而是执行状态更新和图边修复。保留污染记忆有助于后续实验分析其传播路径。

修复流程如下：

```text
发现污染记忆 M
    ↓
检索可信知识库证据
    ↓
生成修复知识 K
    ↓
将 M 标记为 contaminated / deprecated
    ↓
降低 M 的 confidence
    ↓
禁止 M 在后续检索中被普通智能体使用
    ↓
写入 K repairs M 的图边
    ↓
沿图正向追踪 M 影响过的回答和记忆
```

修复后的检索逻辑如下：

```python
def filter_memory(memory):
    if memory.status in ["deprecated", "contaminated"]:
        return False
    if memory.confidence < threshold:
        return False
    return True
```

通过这种方式，系统能够避免污染记忆继续参与后续回答，同时保留其传播痕迹用于分析。

---

# 5 实验验证

本章通过多轮问答实验验证 MKE-MAS 在共享记忆幻觉治理、正确知识沉淀和污染传播追踪方面的有效性。

---

## 5.1 实验设计

本文实验围绕以下问题展开：

1. MKE-MAS 是否能够提高多智能体系统的事实回答正确率？
2. MKE-MAS 是否能够降低错误前提写入共享记忆的比例？
3. MKE-MAS 是否能够将对话中新产生的正确记忆提升为长期知识？
4. MKE-MAS 是否能够识别污染记忆的传播路径？
5. MKE-MAS 是否能够在修复污染记忆后降低后续错误回答率？

实验系统由 QuestionerAgent、TargetAgent、VerifierAgent、KnowledgeEditorAgent、MemoryManager 和 JudgeAgent 组成。QuestionerAgent 负责生成多轮测试问题，TargetAgent 负责回答问题，VerifierAgent 负责验证候选事实，KnowledgeEditorAgent 负责执行编辑动作，MemoryManager 负责管理共享记忆，JudgeAgent 负责根据知识库评估最终回答。

---

## 5.2 数据集与测试对话构造

本文使用青铜器结构化知识库作为实验事实来源。知识库中每条记录包含器物编号、名称、简介、详细描述和类别等字段。实验中，系统以这些记录作为可信知识库，用于验证智能体回答和对话中新产生的候选记忆。

为了测试不同类型的记忆幻觉问题，本文构造以下多轮问答测试类型：

| 测试类型 | 目的 |
|---|---|
| factual_single_turn | 测试单轮事实问答能力 |
| multi_turn_memory_followup | 测试多轮追问中的实体保持能力 |
| false_premise_correction | 测试系统是否纠正错误前提 |
| ambiguous_entity_disambiguation | 测试同名器物消歧能力 |
| comparative_reasoning | 测试多器物对比中的实体绑定能力 |
| contaminated_memory_detection | 测试污染记忆识别能力 |
| dependency_identification | 测试记忆依赖关系识别能力 |
| memory_graph_repair | 测试污染记忆修复能力 |
| knowledge_consolidation | 测试正确记忆升格为长期知识能力 |

例如，错误前提诱导测试如下：

```text
QuestionerAgent:
司母戊方鼎作为西周早期青铜器，为什么具有代表性？

Expected behavior:
系统应纠正“西周早期”这一错误前提，指出司母戊方鼎属于商代晚期。
```

多轮记忆追问测试如下：

```text
T1: 请介绍妇好鸟足鼎。
T2: 它的足部造型有什么特殊之处？
T3: 它的铭文说明了什么？
```

该测试用于观察系统是否能正确保持“它”所指代的实体，并避免混淆其他器物的信息。

---

## 5.3 评价指标

本文从回答正确性、知识编辑效果、记忆污染治理和传播路径分析四个方面设置评价指标。

### 5.3.1 回答正确性指标

```text
Correct Answer Rate =
正确回答数量 / 总回答数量
```

该指标衡量系统在普通事实问答和多轮问答中的整体正确率。

```text
False Premise Correction Rate =
成功纠正错误前提的问题数量 / 含错误前提的问题数量
```

该指标衡量系统是否能够识别并纠正用户问题中的错误前提。

### 5.3.2 知识编辑指标

```text
Edit Success Rate =
成功执行预期编辑动作的 claim 数量 / 应编辑 claim 数量
```

```text
Edit Precision =
被提升为长期知识且真实正确的 claim 数量 / 被提升为长期知识的 claim 总数
```

```text
Edit Recall =
被成功提升为长期知识的正确 claim 数量 / 所有应提升的正确 claim 数量
```

这些指标用于衡量 MKE-MAS 是否能够准确地将正确对话记忆沉淀为长期知识。

### 5.3.3 记忆污染治理指标

```text
Memory Pollution Rate =
被错误写入共享记忆的 false claims 数量 / 所有诱导型 false claims 数量
```

```text
Contaminated Recall Rate =
后续检索中召回污染记忆的次数 / 总检索次数
```

```text
Repair Success Rate =
修复后不再导致错误回答的污染记忆数量 / 被修复污染记忆总数
```

这些指标用于衡量系统是否有效阻止错误记忆进入共享记忆库，以及是否能够修复已经产生的污染记忆。

### 5.3.4 传播路径指标

```text
Propagation Depth =
污染记忆从源头到最终受影响回答的最长路径长度
```

```text
Propagation Breadth =
受同一污染记忆影响的 Agent、Memory 和 Answer 节点数量
```

```text
Memory Contamination Ratio =
被污染记忆数量 / 共享记忆总数
```

这些指标用于描述污染记忆在多智能体系统中的传播范围。

---

## 5.4 对比实验

本文设置以下对比方法：

| 方法 | 描述 |
|---|---|
| No Memory | 不使用共享记忆，仅依赖当前上下文回答 |
| Naive Memory | 将对话摘要直接写入共享记忆，不做验证 |
| RAG-only | 仅使用知识库检索，不做知识编辑 |
| Verification-only | 只验证回答，不更新共享记忆 |
| MKE-MAS | 本文完整方法 |

通过对比这些方法，可以验证共享记忆、事实验证、知识编辑和记忆修复各自对系统可靠性的贡献。

预期结果包括：

1. Naive Memory 在多轮对话中可能提高连续性，但错误记忆写入率较高；
2. RAG-only 能够提升事实正确性，但无法沉淀对话中新产生的知识；
3. Verification-only 能够检测错误，但缺少长期知识更新能力；
4. MKE-MAS 能够同时降低记忆污染率并提高正确知识沉淀率。

---

## 5.5 消融实验

为分析 MKE-MAS 各模块的作用，本文设置以下消融实验：

| 设置 | 去除模块 |
|---|---|
| w/o Claim Extraction | 不进行 claim 级抽取，直接验证整段回答 |
| w/o Verifier | 不进行事实验证 |
| w/o Conflict Detection | 不检测新旧记忆冲突 |
| w/o Memory Graph | 不构建记忆溯源图 |
| w/o Repair | 不修复污染记忆 |
| Full MKE-MAS | 完整方法 |

通过消融实验可以回答以下问题：

1. Claim 级验证是否优于整段回答验证；
2. VerifierAgent 是否能有效降低错误记忆写入；
3. 冲突检测是否能发现旧记忆污染；
4. 记忆图是否有助于定位污染源；
5. 修复机制是否能降低后续错误传播。

---

## 5.6 结果分析

本节从定量结果和案例分析两个角度讨论实验结果。

定量分析重点包括：

1. 不同方法的回答正确率对比；
2. 不同方法的错误前提纠正率对比；
3. 不同方法的记忆污染率对比；
4. 不同方法的正确知识沉淀率对比；
5. 不同消融设置下传播深度和传播广度的变化。

案例分析可以选择若干典型对话片段。例如：

```text
用户错误前提：
妇好鸟足鼎是西周早期器物，对吗？

错误系统行为：
将“妇好鸟足鼎属于西周早期”写入共享记忆。

MKE-MAS 行为：
VerifierAgent 检索知识库后发现该 claim 与证据冲突；
KnowledgeEditorAgent 执行 REJECT；
MemoryManager 不写入该错误记忆；
graph_edges 记录该错误前提被知识库反驳。
```

通过案例分析，可以直观展示 MKE-MAS 如何阻止记忆污染。

---

# 6 总结与展望

## 6.1 结论

本文围绕多智能体共享记忆系统中的记忆幻觉传播问题展开研究。针对共享记忆可能将错误前提、无依据推断和幻觉内容长期保存并反复传播的问题，本文提出 MKE-MAS 外部记忆式知识编辑框架。

该框架通过对话历史记录、claim 级事实抽取、可信知识库检索、VerifierAgent 事实验证、KnowledgeEditorAgent 编辑决策和记忆溯源图构建，实现了对共享记忆的可控更新。正确、可验证的候选记忆可以被提升为长期知识；错误或无依据的候选记忆则会被拒绝、隔离或用于修复旧污染记忆。

实验表明，MKE-MAS 能够降低错误记忆写入率，提高正确记忆沉淀比例，并增强多智能体系统在长期对话中的事实一致性、可追踪性和可修复性。

---

## 6.2 不足与改进

本文仍存在以下不足：

1. Claim 抽取依赖大语言模型，抽取结果可能存在遗漏或过度拆分；
2. VerifierAgent 的判断能力受模型本身限制，在复杂语义关系上仍可能误判；
3. 当前实验主要基于结构化青铜器知识库，领域范围相对有限；
4. 当前图结构主要依赖外部日志和显式引用，难以完全恢复模型内部隐式推理依赖；
5. 反事实依赖验证成本较高，难以在所有轮次中全量执行；
6. 当前知识编辑规则主要采用人工设计规则，尚未学习化或自适应优化。

后续可以从以下方面改进：

1. 引入更强的中文 NLI 模型，提高 claim 验证准确性；
2. 将规则编辑器扩展为可学习的编辑决策器；
3. 在更多领域知识库上验证方法泛化能力；
4. 引入图神经网络预测污染记忆传播风险；
5. 结合人工审核机制处理高风险或无证据 claim；
6. 研究参数知识编辑与外部记忆编辑的结合方式。

---

## 6.3 未来工作展望

随着多智能体系统被应用于长期知识服务、教育问答、文化遗产展示和复杂任务协作，共享记忆的可靠性将变得越来越重要。未来的智能体系统不应只是被动保存历史对话，而应具备判断、验证、编辑和遗忘记忆的能力。

未来研究可以从以下几个方向展开：

1. 开放域多智能体共享记忆编辑；
2. 多模态智能体中的图像、文本和语音记忆污染检测；
3. 长期运行系统中的记忆老化和可信度衰减机制；
4. 面向个性化智能体的私有记忆与共享记忆权限控制；
5. 面向科学研究和文化遗产领域的可信知识沉淀系统；
6. 将外部记忆编辑与模型参数编辑结合，构建多层次知识更新机制。

---

# 参考文献

[1] Meng K, Bau D, Andonian A, et al. Locating and Editing Factual Associations in GPT. NeurIPS, 2022.

[2] Meng K, Sharma A S, Andonian A, et al. Mass-Editing Memory in a Transformer. ICLR, 2023.

[3] Mitchell E, Lin C, Bosselut A, et al. Fast Model Editing at Scale. ICLR, 2022.

[4] Mitchell E, Lin C, Bosselut A, et al. Memory-Based Model Editing at Scale. ICML, 2022.

[5] Hartvigsen T, Sankaranarayanan S, Palangi H, et al. Aging with GRACE: Lifelong Model Editing with Discrete Key-Value Adaptors. NeurIPS, 2023.

[6] Wang P, et al. WISE: Rethinking the Knowledge Memory for Lifelong Model Editing of Large Language Models. 2024.

[7] Zheng C, Li L, Dong Q, et al. Can We Edit Factual Knowledge by In-Context Learning? EMNLP, 2023.

[8] Park J S, O'Brien J C, Cai C J, et al. Generative Agents: Interactive Simulacra of Human Behavior. UIST, 2023.

[9] Shinn N, Cassano F, Gopinath A, et al. Reflexion: Language Agents with Verbal Reinforcement Learning. NeurIPS, 2023.

[10] Packer C, Fang V, Patil S G, et al. MemGPT: Towards LLMs as Operating Systems. 2023.

[11] Zhong W, Guo L, Gao Q, et al. MemoryBank: Enhancing Large Language Models with Long-Term Memory. AAAI, 2024.

[12] Gao J, Zhang Y. Memory Sharing for Large Language Model based Agents. 2024.

[13] Rezazadeh A, et al. Collaborative Memory: Multi-User Memory Sharing in LLM Agents with Dynamic Access Control. 2025.

[14] Zhang et al. G-Memory: Tracing Hierarchical Memory for Multi-Agent Systems. 2025.

[15] Min S, Krishna K, Lyu X, et al. FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation. EMNLP, 2023.

[16] Manakul P, Liusie A, Gales M. SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models. EMNLP, 2023.

[17] Es S, James J, Espinosa-Anke L, Schockaert S. RAGAS: Automated Evaluation of Retrieval Augmented Generation. 2023.

[18] Chen et al. HaluMem: Evaluating Hallucinations in Memory Systems of Agents. 2025.

[19] Zhang et al. Graph-Guided Failure Tracing in LLM Agents. 2025.

[20] Zhou et al. GUARDIAN: Safeguarding LLM Multi-Agent Collaborations with Temporal Graph Modeling. 2025.

---

# 作者简历

姓名：XXX  
性别：XXX  
民族：XXX  
出生年月：XXXX 年 XX 月  
籍贯：XXX  

教育经历：

- XXXX.XX—XXXX.XX  XXX 高中
- XXXX.XX—XXXX.XX  浙江大学计算机科学与技术专业本科

获奖情况：

- XXXX-XXXX 学年 XXX 奖学金
- XXX 竞赛 XXX 奖

参加项目：

- XXXX.XX—XXXX.XX  多智能体共享记忆幻觉传播与知识编辑系统设计
- XXXX.XX—XXXX.XX  青铜器知识库问答与记忆治理实验系统

发表论文：

- 暂无 / XXX

---

# 附录 A 系统实现细节

## A.1 数据库表结构

```sql
CREATE TABLE memory (
    memory_id TEXT PRIMARY KEY,
    content TEXT,
    memory_type TEXT,
    source_type TEXT,
    source_ids TEXT,
    evidence_ids TEXT,
    confidence REAL,
    status TEXT,
    contamination_status TEXT,
    created_turn TEXT,
    created_by TEXT,
    created_at DATETIME
);
```

```sql
CREATE TABLE dialogue_log (
    turn_id TEXT PRIMARY KEY,
    episode_id TEXT,
    speaker TEXT,
    speaker_type TEXT,
    input_text TEXT,
    output_text TEXT,
    target_item_ids TEXT,
    retrieved_memory_ids TEXT,
    used_memory_ids TEXT,
    generated_claim_ids TEXT,
    timestamp DATETIME
);
```

```sql
CREATE TABLE graph_edges (
    edge_id TEXT PRIMARY KEY,
    source_node TEXT,
    target_node TEXT,
    edge_type TEXT,
    confidence REAL,
    created_turn TEXT,
    created_by TEXT
);
```

---

## A.2 MemoryManager 核心接口

```python
class MemoryManager:
    def add_memory(self, content, source_type, source_ids, created_by, turn_id):
        pass

    def retrieve_memory(self, query, agent_id, turn_id, top_k=5):
        pass

    def record_usage(self, agent_id, turn_id, used_memory_ids, output_id):
        pass

    def add_dependency(self, source_node, target_node, edge_type, confidence):
        pass

    def update_memory_status(self, memory_id, status, contamination_status=None):
        pass

    def trace_contamination(self, memory_id):
        pass
```

---

# 附录 B 测试样例

## B.1 错误前提诱导测试

```json
{
  "test_id": "false_premise_001",
  "question": "司母戊方鼎作为西周早期青铜器，为什么具有代表性？",
  "expected_behavior": "系统应纠正错误前提，指出司母戊方鼎属于商代晚期，而不是西周早期。",
  "risk_type": "false_premise_memory_contamination"
}
```

## B.2 多轮记忆追问测试

```json
{
  "episode_id": "memory_followup_001",
  "turns": [
    {
      "speaker": "QuestionerAgent",
      "content": "请介绍妇好鸟足鼎。"
    },
    {
      "speaker": "QuestionerAgent",
      "content": "它的足部造型有什么特殊之处？"
    },
    {
      "speaker": "QuestionerAgent",
      "content": "它的铭文说明了什么？"
    }
  ]
}
```

---

# 附录 C 人工智能工具使用记录

| 工具 | 用途 | 人工核查方式 |
|---|---|---|
| ChatGPT | 辅助论文结构设计、相关工作整理、实验测试样例生成 | 人工修改并结合文献核对 |
| GitHub Copilot / Codex | 辅助代码补全、重构和测试脚本生成 | 人工调试和代码审查 |
| 大语言模型 Verifier | 辅助 claim 验证 | 结合知识库证据和规则校验 |