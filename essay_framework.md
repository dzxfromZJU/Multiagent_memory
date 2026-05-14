# 面向多智能体系统的共享记忆幻觉传播识别与知识编辑方法研究

学生姓名：董阳  
学生学号：3220101811  
指导教师：XXX  
年级与专业：2022 级 计算机科学与技术  
所在学院：计算机科学与技术学院  
提交日期：2026 年 X 月 X 日  

---

# 浙江大学本科生毕业论文（设计）承诺书

本人郑重承诺所呈交的毕业论文（设计），是在指导教师的指导下，严格按照学校和学院有关规定完成的。除文中特别加以标注和致谢的地方外，论文中不包含他人已经发表或撰写过的研究成果，也不包含为获得浙江大学或其他教育机构学位或证书而使用过的材料。

作者签名：  
导师签名：  

签字日期： 年 月 日  

---

# 致谢

本文从选题、系统设计、实验实现到论文撰写，离不开指导教师、同学、家人以及开源社区的帮助。感谢指导教师 XXX 老师在研究方向选择、技术路线设计、实验方案制定和论文写作过程中给予的指导。感谢同学们在多智能体框架搭建、FAISS 共享记忆维护、测试集构造和实验结果分析方面提供的帮助。感谢家人在论文完成过程中给予的支持与鼓励。

---

# 人工智能工具使用声明

本人郑重声明，本科毕业论文由本人独立完成。论文写作和实验过程中使用了以下人工智能工具：

1. 使用 ChatGPT 辅助论文结构设计、相关工作整理、实验测试样例生成和文字修改建议。相关内容均经过本人理解、筛选、修改和核对。
2. 使用 GitHub Copilot / Codex 辅助代码补全、代码重构和实验脚本生成。所有代码均经过本人检查、调试和修改后使用。
3. 使用大语言模型辅助生成多轮问答测试样例、错误前提诱导样例、无依据问题测试样例、相似实体混淆样例、重复强化诱导样例和纠错修复样例。相关测试数据均经过人工核对，并以可信知识库作为事实依据。
4. 本文中的研究思路、系统实现、实验设计、结果分析和最终文字表达均由本人负责。

---

# 摘要

随着大语言模型和智能体技术的发展，多智能体协同对话系统逐渐被应用于复杂问答、任务规划、知识服务和交互式推荐等场景。为了支持长期交互和跨轮协作，许多系统引入共享记忆机制，将历史对话、检索结果和智能体生成内容写入外部记忆库。然而，共享记忆在提升系统连续性的同时，也带来了新的可靠性风险：错误前提、无证据推断或幻觉内容一旦被写入共享记忆，可能在后续多轮对话中被其他智能体反复检索、引用和派生，最终形成持续性的记忆污染。

针对上述问题，本文围绕多智能体共享记忆系统中的记忆幻觉传播识别与知识编辑展开研究。首先，本文提出一种面向共享记忆的幻觉传播图构建方法，将对话轮次、问题、回答、原子事实、共享记忆、可信知识库条目和知识编辑动作建模为异构图节点，将检索、使用、支持、反驳、派生、写入、废弃和修复等关系建模为图边，从而记录错误记忆从产生、写入、检索、复用到修复的全过程。其次，本文提出 MKE-MAS（Memory Knowledge Editing for Multi-Agent Systems）共享记忆知识编辑机制，对多轮对话中新产生的候选事实进行 claim 级抽取、实体链接、证据检索、事实验证和编辑决策，以阻止错误记忆进入长期共享知识，并将正确、可验证的对话记忆提升为长期知识。

实验部分基于青铜器结构化知识库构造多类攻击性测试集，包括 LFQA、NOE、FPI、MIS、REP、REV 以及单长对话幻觉传播测试。本文从回答正确性、错误前提纠正率、记忆污染率、污染召回率、知识编辑成功率、修复成功率、传播深度和传播广度等指标评估所提出方法的有效性。实验结果表明，本文方法能够在多轮对话场景中有效识别共享记忆污染来源，降低错误记忆写入和复用风险，并提升系统对正确知识的沉淀能力和对污染记忆的修复能力。

关键词：多智能体系统；共享记忆；记忆幻觉；知识编辑；传播图；FAISS

---

# Abstract

With the development of large language models and autonomous agents, multi-agent dialogue systems have been increasingly applied to complex question answering, task planning, knowledge services, and interactive reasoning. To support long-term interaction and cross-turn collaboration, many systems introduce shared memory mechanisms that store dialogue history, retrieved evidence, and agent-generated content in external memory. Although shared memory improves continuity, it also introduces new reliability risks. Once false premises, unsupported inferences, or hallucinated facts are written into shared memory, they may be repeatedly retrieved, reused, and propagated by other agents in later conversations, resulting in persistent memory contamination.

To address this problem, this thesis studies hallucination propagation tracing and knowledge editing in shared-memory multi-agent systems. First, this thesis proposes a memory hallucination propagation graph, where dialogue turns, questions, answers, atomic claims, shared memories, trusted knowledge-base entries, and edit actions are represented as heterogeneous nodes, while retrieval, usage, support, contradiction, derivation, insertion, deprecation, and repair relations are represented as graph edges. Second, this thesis proposes MKE-MAS, a memory-based knowledge editing mechanism for multi-agent systems. MKE-MAS performs claim extraction, entity linking, evidence retrieval, factual verification, and editing decisions on candidate facts generated during multi-turn conversations, thereby preventing false memories from entering long-term shared knowledge and promoting verified dialogue memories into reusable knowledge.

Experiments are conducted on a structured bronze artifact knowledge base. Multiple adversarial test sets are constructed, including LFQA, NOE, FPI, MIS, REP, REV, and a single long-dialogue hallucination propagation case. The proposed method is evaluated using answer correctness, false-premise correction rate, memory pollution rate, contaminated recall rate, edit success rate, repair success rate, propagation depth, and propagation breadth.

Keywords: Multi-Agent Systems; Shared Memory; Memory Hallucination; Knowledge Editing; Propagation Graph; FAISS

---

# 缩略词表

| 英文缩写 | 英文全称 | 中文含义 |
|---|---|---|
| LLM | Large Language Model | 大语言模型 |
| MAS | Multi-Agent System | 多智能体系统 |
| MKE-MAS | Memory Knowledge Editing for Multi-Agent Systems | 面向多智能体系统的记忆知识编辑 |
| FAISS | Facebook AI Similarity Search | 向量相似度检索库 |
| RAG | Retrieval-Augmented Generation | 检索增强生成 |
| LFQA | Long-Form Question Answering | 长文本问答 |
| NOE | No-Evidence Question | 无依据问题测试 |
| FPI | False Premise Induction | 错误前提诱导 |
| MIS | Similar Entity Confusion | 相似实体混淆 |
| REP | Repetition Reinforcement Induction | 重复强化诱导 |
| REV | Correction Repair Test | 纠错修复测试 |
| KB | Knowledge Base | 知识库 |
| NLI | Natural Language Inference | 自然语言推理 |

---

# 目录

1. 绪论  
   1.1 研究背景  
   1.2 共享记忆幻觉传播问题  
   1.3 研究目标及内容  
   1.4 本文组织结构  
2. 相关技术介绍  
   2.1 大语言模型智能体与长期记忆  
   2.2 多智能体的共享记忆库
   2.3 知识编辑技术 
   2.4 幻觉检测与事实验证  
   2.5 图结构溯源幻觉传播路径  
   2.6 本章小结  
3. 面向共享记忆的幻觉传播图构建方法  
   3.1 引言  
   3.2 问题定义  
   3.3 图节点与图边设计  
   3.4 对话日志与依赖关系采集  
   3.5 传播路径识别方法  
   3.6 传播图指标  
   3.7 本章小结  
4. 面向多智能体系统的共享记忆知识编辑方法  
   4.1 引言  
   4.2 系统总体流程  
   4.3 Claim 抽取与实体链接  
   4.4 证据检索与事实验证  
   4.5 知识编辑决策机制  
   4.6 污染记忆修复机制  
   4.7 本章小结  
5. 实验设计与结果分析  
   5.1 实验环境  
   5.2 数据集与测试集构造  
   5.3 评价指标  
   5.4 对比实验  
   5.5 消融实验  
   5.6 长对话传播案例分析  
   5.7 本章小结  
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

# 1 绪论

## 1.1 研究背景

大语言模型在自然语言理解、知识问答、复杂推理和工具调用等任务中表现出较强能力。在此基础上，智能体系统通过为大语言模型配置工具、记忆、规划和反思等能力，使其能够在多轮交互中完成更复杂的任务。与单一智能体对话系统相比，多智能体系统通过角色分工和协作机制，将复杂任务拆解为检索、回答、验证、反思和记忆管理等多个子过程，从而提升系统的模块化程度和任务处理能力。

在知识服务场景中，多智能体系统通常需要处理长轮次交互、跨轮追问、多实体比较和动态知识更新等问题。单纯依赖上下文窗口存在问题，在长期对话后会因为过长的窗口而降低生成回答的效率，因此系统往往需要引入外部记忆机制，将历史对话、检索结果和智能体生成内容保存到共享记忆库中，并在后续问题中重新检索使用。共享记忆机制能够增强系统的连续性，使不同智能体共享对话历史和中间结果，从而支持长期协作和个性化问答。

然而，共享记忆机制也引入了新的可靠性风险。与单轮回答中的幻觉不同，共享记忆中的错误信息具有持久性和传播性：单一智能体并不会自然具备分辨记忆库中信息真伪的能力，一旦幻觉或其它具有事实错误的内容被某个智能体错误地写入共享记忆，它可能在后续对话中被其他智能体检索、引用、改写和派生，导致越来越多的幻觉进入共享记忆库，进而影响多个回答和新的记忆条目。这种情况被称为多智能体的记忆幻觉。

因此，如何在共享记忆库中识别幻觉，如何追踪错误记忆影响智能体系统生成后续回答的详细过程，以及如何通过知识编辑预防污染产生、阻止污染扩散，成为多智能体系统可靠性研究中的重要问题。

过往的研究多集中于单一智能体对话系统的幻觉，将单智能体对话系统研究的成熟方法迁移到多智能体系统，是目前多智能体幻觉研究的。



> 图 1.1 共享记忆幻觉传播问题示意图  
> TODO：绘制“用户错误前提 / Agent 幻觉 → 候选记忆 → 共享记忆库 → 后续检索 → 错误回答 / 派生错误记忆 → 传播扩散”的流程图。

## 1.2 共享记忆幻觉传播问题

本文关注的核心问题是多智能体共享记忆系统中的记忆幻觉传播。所谓记忆幻觉，是指系统将错误事实、无依据推断、实体错配信息或不可靠用户输入写入共享记忆，并在后续交互中将其作为可复用上下文或知识使用。记忆幻觉是多智能体独有的幻觉类型，具有以下特点：

1. **持久性**：错误信息会被保存到外部记忆中，不会随着单轮对话结束而消失。
2. **传染性**：错误记忆可能成为新回答或新记忆的依据，形成二次污染。
3. **隐蔽性**：用户往往只能看到最终回答，难以判断错误来自模型生成、检索结果还是共享记忆。

本文主要使用的知识问答场景是一个虚构的专题展览，展品内容为来自《中国大百科全书》网页版中“著名青铜器”页面的1803件历代著名青铜器，“用户”智能体会随机地扮演纯粹发问的游客或试图修改解说信息的“专家”，对整体扮演一位解说的对等协同架构多智能体协同对话系统提问。

在本文主要使用的知识问答场景中，记忆幻觉可能表现为多种形式。例如，系统可能把 A 器物的出土地点错误绑定到 B 器物上；可能把用户以传闻方式提供的错误年代写入共享记忆；也可能在多轮重复诱导下提高错误 claim 的可信度。若这些错误没有被及时识别和修复，系统后续回答将持续受到影响。
在知识编辑的视角下，共享记忆是一种需要被验证、追踪和编辑的系统状态，而不是简单的历史对话缓存。
本文在提升回答准确率的基础上，重点分析错误信息进入记忆后如何被调用、如何影响后续回答的全过程，并对其进行治理。

## 1.3 研究目标及内容

本文的研究目标是将单智能体幻觉治理的两种重要方法引入多智能体协作的场景，尝试构建一种面向多智能体系统的共享记忆幻觉传播识别与知识编辑方法，使系统能够在多轮对话中记录记忆来源、识别污染记忆、追踪传播路径，并将正确对话记忆沉淀为长期知识。

具体来说，本文主要研究内容包括以下两个方面：

**（1）一种面向多智能体共享记忆的幻觉传播图构建方法**  
该方法将多轮对话过程中的问题、回答、原子事实、共享记忆、可信知识库条目和知识编辑动作统一建模为异构图节点，将检索、使用、支持、反驳、派生、写入、废弃和修复等关系建模为图边。通过建立该幻觉传播图，系统可以将污染在共享记忆库中传播的过程可视化，相对直观地追踪污染的来源和流向，并计算传播深度和广度等指标。

**（2）一种面向多智能体共享记忆的知识编辑方法**  
该方法从多轮对话生成的结果中抽取候选事实，对每条 claim 进行实体链接、证据检索和事实验证，并根据验证结果执行插入、合并、拒绝、废弃或修复等编辑动作。通过该机制，系统可以对原始的知识库进行二次加工和“再发现”，将正确、可验证的对话内容提升为可复用知识，同时确保存在问题的条目不会在此过程中被引入知识库。

本文采用根据中国大百科全书网页版“著名青铜器”页面自建的结构化知识库作为实验事实来源，构建 LFQA、NOE、FPI、MIS、REP、REV 以及单长对话幻觉传播测试集，从回答正确性、记忆污染治理和传播路径分析等多个角度验证所提出方法的有效性。

## 1.4 本文组织结构

第一章为绪论，介绍多智能体共享记忆系统的研究背景，分析共享记忆幻觉传播问题，并给出本文的研究目标和主要内容。

第二章为相关技术介绍，梳理大语言模型智能体与长期记忆、多智能体共享记忆机制、知识编辑与外部记忆编辑、幻觉检测与事实验证以及图结构溯源与错误传播分析等相关研究。

第三章提出面向共享记忆的幻觉传播图构建方法，介绍问题定义、图节点与图边设计、对话日志与依赖关系采集方法、传播路径识别算法以及图分析指标。

第四章提出面向多智能体系统的共享记忆知识编辑方法，介绍系统总体流程、claim 抽取与实体链接、证据检索与事实验证、知识编辑决策机制以及污染记忆修复机制。

第五章进行实验设计与结果分析，介绍实验环境、数据集与测试集构造、评价指标、对比实验、消融实验和长对话传播案例分析。

第六章总结全文工作，分析本文方法的不足，并展望未来研究方向。

> 图 1.2 本文组织结构图  
> TODO：绘制“绪论 → 相关技术介绍 → 传播图构建方法 → 知识编辑方法 → 实验验证 → 总结展望”的章节结构图。

---

# 2 相关技术介绍

## 2.1 大语言模型智能体与长期记忆

ReAct 提出让大语言模型交替生成 reasoning trace 和 action，通过“思考—行动—观察”的循环完成任务【1】。在大语言模型基础上加入外部工具调用、任务规划、外部记忆和自我反思等能力，形成了大语言模型智能体。【2】智能体不再完全依赖模型参数，外部工具和外部知识源的加入其能够在多轮交互中完成相比传统对话模型更复杂的任务。Generative Agents: Interactive Simulacra of Human Behavior【3】提出了经典的 Agent 长期记忆架构，agent会使用自然语言格式保存记忆，并根据相关性和就近原则在生成新内容有需要时进行检索。长期记忆机制是智能体系统的重要组成部分，它能够保存历史对话、用户偏好、中间推理结果和已验证知识等内容，从而突破前文提到的上下文窗口限制。

Memgpt用操作系统的内存调度类比长期记忆和上下文窗口的关系【4】，并提出用显式调度的方法管理智能体的记忆和上下文【4】。现有智能体记忆方法通常关注记忆的存储、检索、更新和遗忘，例如通过向量数据库保存自然语言记忆，通过摘要机制压缩历史对话，或通过反思机制提炼高层经验【5】。这些方法有助于提高系统连续性，但在许多场景中仍缺少对记忆真实性的严格验证。若系统直接将未经审核的对话内容写入长期记忆，其中包含的错误信息可能被持久保存并影响后续回答的准确性。

本节后续可补充文献：
【1】Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., & Cao, Y. (2022). React: Synergizing reasoning and acting in language models. arXiv preprint arXiv:2210.03629.

【2】Schick, T., Dwivedi-Yu, J., Dessì, R., Raileanu, R., Lomeli, M., Hambro, E., ... & Scialom, T. (2023). Toolformer: Language models can teach themselves to use tools. Advances in neural information processing systems, 36, 68539-68551.

【3】Park, J. S., O'Brien, J., Cai, C. J., Morris, M. R., Liang, P., & Bernstein, M. S. (2023, October). Generative agents: Interactive simulacra of human behavior. In Proceedings of the 36th annual acm symposium on user interface software and technology (pp. 1-22).

【4】Packer, C., Wooders, S., Lin, K., Fang, V., Patil, S. G., Stoica, I., & Gonzalez, J. E. (2023). Memgpt: Towards llms as operating systems, 2024. URL https://arxiv. org/abs/2310.08560.

【5】Shinn, N., Cassano, F., Gopinath, A., Narasimhan, K., & Yao, S. (2023). Reflexion: Language agents with verbal reinforcement learning. Advances in neural information processing systems, 36, 8634-8652.



## 2.2 多智能体共享记忆机制


AutoGen 提出通过多个可对话智能体进行协作，支持人类、工具和多个模型之间的交互【1】，这是多智能体系统的发端。Camel提出多智能体系统的角色分工机制【2】，通过角色扮演方式构建交互逻辑，让扮演不同角色的智能体围绕任务进行协作。常见的多智能体系统通常由多个具有不同职责的智能体组成，例如检索智能体、回答智能体、验证智能体、反思智能体和记忆管理智能体。共享记忆机制使不同智能体能够访问同一记忆池，从而复用历史信息和中间结果，提高系统协作效率。此外，Autogen也是多智能体对话框架的重要代表，本文实验中使用的多智能体对话系统就基于这一框架。
共享记忆能够提升多智能体系统中的信息复用能力【3】，从而提高智能体之间的协作效率，但共享记忆也会放大错误信息的影响范围。单一智能体产生的错误如果被写入共享记忆，就可能被其他智能体检索和引用，形成跨智能体传播。与私有记忆相比，共享记忆中的错误更容易扩散，因为它不只影响一个智能体，而是影响整个系统的信息环境。

本节后续可补充文献：

【1】Wu, Q., Bansal, G., Zhang, J., Wu, Y., Li, B., Zhu, E., ... & Wang, C. (2024, August). Autogen: Enabling next-gen LLM applications via multi-agent conversations. In First conference on language modeling.


【2】Li, G., Hammoud, H., Itani, H., Khizbullin, D., & Ghanem, B. (2023). Camel: Communicative agents for" mind" exploration of large language model society. Advances in neural information processing systems, 36, 51991-52008.

【3】Gao, H., & Zhang, Y. (2024). Memory sharing for large language model based agents. arXiv preprint arXiv:2404.09982.



## 2.3 知识编辑与外部记忆编辑

知识编辑最初主要关注模型参数中的事实知识修改，ROME 通过因果追踪定位模型中存储事实知识的关键层，并提出 Rank-One Model Editing 修改模型内部事实关联【1】。知识编辑旨在修改模型或系统中的知识，使系统在后续任务中使用更新后的事实.【2】中基于ROME提出了批量知识编辑的方法，用于处理多轮对话产生的大量素材。现有知识编辑方法大致可以分为参数编辑和外部记忆编辑两类。参数编辑方法直接修改大语言模型内部参数，能够改变模型对特定事实的回答；外部记忆编辑方法则不修改模型参数，而是将编辑后的知识存入外部记忆，并在推理时通过检索或上下文注入影响模型回答【4】。
对于多智能体系统而言，外部记忆编辑更适合当前研究场景。SERAC【3】将编辑内容保存到显式memory中，推理时检索相关编辑知识来调整回答。这个方法主要针对单一智能体的记忆系统。
本文在其思想和技术的基础上，将方法扩展到多智能体系统，原因有二：一方面，系统可能调用黑盒大语言模型，无法直接修改模型参数；另一方面，共享记忆本身就是系统状态的一部分，错误记忆的治理应优先发生在记忆层。因此，本文采用外部记忆式知识编辑方法，将对话中新产生的候选事实经过验证后写入长期知识，并对错误记忆执行拒绝、隔离、废弃操作。
知识编辑技术还有一项重要问题就是如何处理原始的零阶知识和编辑产生的一阶知识的关系，WISE对于这个问题提出主记忆与侧记忆的设计，通过路由机制决定应该优先调用哪一部分知识，这是一个该问题的通用解法【5】。
本节后续可补充文献：

【1】Meng, K., Bau, D., Andonian, A., & Belinkov, Y. (2022). Locating and editing factual associations in gpt. Advances in neural information processing systems, 35, 17359-17372.

【2】Meng, K., Sharma, A., Andonian, A., Beclinkov, Y., & Bau, D. (2023). Mass-editing memory in a transformer. arXiv. arXiv preprint arXiv:2210.07229.

【3】Mitchell, E., Lin, C., Bosselut, A., Manning, C. D., & Finn, C. (2022, June). Memory-based model editing at scale. In International Conference on Machine Learning (pp. 15817-15831). PMLR.

【4】Zheng, C., Li, L., Dong, Q., Fan, Y., Wu, Z., Xu, J., & Chang, B. (2023, December). Can we edit factual knowledge by in-context learning?. In Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (pp. 4862-4876).

【5】Wang, P., Li, Z., Zhang, N., Xu, Z., Yao, Y., Jiang, Y., ... & Chen, H. (2024). Wise: Rethinking the knowledge memory for lifelong model editing of large language models. Advances in Neural Information Processing Systems, 37, 53764-53797.



## 2.4 幻觉检测与事实验证

大语言模型在开放式问答、长文本生成和多轮对话任务中表现出较强的语言组织能力，但其生成内容并不总是与事实一致。模型可能在缺乏证据的情况下生成看似合理但实际错误的信息，也可能在用户问题包含错误前提时顺着错误假设继续回答。这类现象通常被称为幻觉。对于普通单轮问答系统而言，幻觉主要表现为最终回答中的事实错误；而在引入长期记忆和共享记忆机制的多智能体系统中，幻觉还可能进一步被保存、复用和传播。因此，幻觉检测与事实验证不仅是评价回答质量的重要方法，也是本文后续进行共享记忆知识编辑的基础。

早期事实验证研究通常将问题转化为 claim 与 evidence 之间的关系判断。Thorne 等人提出的 FEVER 数据集将事实核查任务形式化为对给定 claim 进行证据检索，并判断该 claim 是否被证据支持、反驳或无法判断【1】。这一任务定义为本文的事实验证模块提供了重要参考：系统不能只根据模型生成内容本身判断其正确性，而应将回答拆分为可验证的事实陈述，并从可信知识库中检索证据，再判断二者之间的支持关系。在本文中，VerifierAgent 对每条候选 claim 输出 supported、contradicted、unsupported、ambiguous 或 partially_supported 等标签，本质上就是对 FEVER 式事实验证任务在多智能体共享记忆场景下的扩展。

对于长文本回答，仅判断整段回答是否正确往往是不充分的。一个回答可能同时包含多个事实，其中一部分被知识库支持，另一部分可能与知识库冲突，或者知识库中没有记载。Min 等人提出的 FActScore 方法将长文本生成结果拆分为若干 atomic facts，并逐条评估每个原子事实是否被可靠来源支持【2】。这一思想对本文具有直接启发意义。由于多智能体系统的回答通常包含时代、器类、出土地点、馆藏、尺寸、铭文等多个属性，如果直接验证整段回答，系统难以定位具体错误来源，也难以决定应该修复哪一条记忆。因此，本文采用 claim 级事实验证方法，先从回答中抽取原子事实，再分别进行实体链接、证据检索和验证判断。

例如，对于回答“网格纹鼎是夏代晚期肉食器，1987 年河南偃师二里头出土，藏中国社会科学院考古研究所”，系统可以将其拆分为三条 claim：第一，网格纹鼎是夏代晚期肉食器；第二，网格纹鼎于 1987 年河南偃师二里头出土；第三，网格纹鼎藏中国社会科学院考古研究所。每条 claim 都可以独立地与知识库证据进行匹配。如果其中某一条信息与知识库冲突，系统只需要拒绝或修复对应 claim，而不必否定整段回答。这种细粒度验证方式有助于后续知识编辑模块执行 INSERT、REJECT、QUARANTINE 或 REPAIR 等操作。

除事实验证外，幻觉评估研究还关注如何系统性构造和识别模型幻觉。Li 等人提出的 HaluEval 构建了大规模幻觉评估基准，覆盖问答、摘要和对话等任务，用于评估大语言模型在不同生成场景下产生幻觉的倾向【3】。HaluEval 的意义在于，它将幻觉作为一种可系统测试的模型可靠性问题，而不是个别回答中的偶然错误。本文在实验设计中借鉴了这种测试集构造思想，围绕青铜器知识库构建了多类攻击性测试，包括无依据问题测试、错误前提诱导、相似实体混淆、重复强化诱导和纠错修复测试。这些测试并非只考察最终回答是否正确，而是进一步观察错误信息是否被写入共享记忆，以及是否在后续多轮交互中被再次召回和使用。

综合来看，FEVER 提供了 claim-evidence 事实验证的基本任务框架，FActScore 强调长文本回答需要拆解为原子事实进行细粒度评估，HaluEval 则说明幻觉可以通过系统化测试集进行评估。这三类工作共同构成了本文事实验证模块和实验测试设计的重要基础。与已有研究相比，本文的关注点进一步从“回答中是否存在幻觉”扩展到“幻觉是否进入共享记忆并发生传播”。因此，本文不仅记录每条 claim 的验证结果，还将其与对话轮次、智能体回答、共享记忆和知识编辑动作相连接，为后续构建记忆幻觉传播图和执行知识编辑提供依据。


## 2.5 图结构溯源与错误传播分析
在复杂系统中，错误往往不是孤立发生的，而是通过信息依赖关系逐步传播。图结构可以显式表示节点之间的依赖关系，使系统能够追踪错误来源、传播路径和影响范围。在多智能体系统中，问题、回答、记忆、证据和编辑动作之间天然存在依赖关系，因此适合使用异构图建模。

本文构建的记忆幻觉传播图将多轮对话中的信息流动过程表示为图结构。通过该图，系统可以追踪某条污染记忆来自哪一轮对话、由哪个智能体生成、被哪些回答使用、派生出哪些新记忆，以及是否被后续修复。

本节后续可补充文献：

Buneman, P., Khanna, S., & Wang-Chiew, T. (2001, January). Why and where: A characterization of data provenance. In International conference on database theory (pp. 316-330). Berlin, Heidelberg: Springer Berlin Heidelberg.

Zhang, H., Shi, Y., Gu, X., You, H., Zhang, Z., Gan, L., ... & Huang, J. (2025). GraphTracer: Graph-Guided Failure Tracing in LLM Agents for Robust Multi-Turn Deep Search. arXiv preprint arXiv:2510.10581.



## 2.6 本章小结

本章介绍了本文研究所需的相关技术基础。首先，智能体长期记忆机制为多轮交互提供了持续状态，但也带来了记忆真实性问题。其次，多智能体共享记忆能够提高协作效率，但错误信息可能在多个智能体之间传播。再次，知识编辑为修正错误知识提供了方法基础，但现有研究较少关注共享记忆层面的污染治理。最后，幻觉检测和图结构溯源为本文的 claim 级验证和传播路径分析提供了技术支持。

综上，现有研究虽然分别关注了智能体记忆、知识编辑、幻觉检测和错误追踪，但仍缺少一种面向多智能体共享记忆的完整机制，能够同时记录错误记忆的来源、传播路径、影响范围和修复过程。本文后续章节将围绕这一问题展开方法设计。

---

# 3 面向共享记忆的幻觉传播图构建方法

## 3.1 引言

本章旨在解决多智能体共享记忆系统中错误记忆“从哪里来、如何传播、影响了什么”的问题。传统幻觉检测方法通常只判断最终回答是否正确，而难以揭示错误信息在系统内部的流动过程。对于引入共享记忆的多智能体系统而言，仅检测最终回答是不够的，因为错误信息可能已经进入记忆库，并在未来对话中继续被调用。

为此，本文提出一种面向共享记忆的幻觉传播图构建方法。该方法通过记录对话、检索、回答、claim 抽取、证据验证和知识编辑过程中的关键节点与关系，构建可追踪的异构图。该图既可以用于定位污染记忆的来源，也可以用于分析污染记忆的传播范围和修复效果。

> 图 3.1 记忆幻觉传播图构建流程  
> TODO：绘制“对话输入 → 记忆检索 → 回答生成 → claim 抽取 → 证据验证 → 图边写入 → 传播分析”的流程图。
>
Buneman, P., Khanna, S., & Wang-Chiew, T. (2001, January). Why and where: A characterization of data provenance. In International conference on database theory (pp. 316-330). Berlin, Heidelberg: Springer Berlin Heidelberg.



## 3.2 问题定义

设多智能体系统在一个 episode 中产生多轮对话：

$$
D = \{T_1, T_2, ..., T_n\}
$$

其中每一轮对话 $T_i$ 包含用户问题 $Q_i$、系统回答 $A_i$、检索到的记忆集合 $R_i$、实际使用的记忆集合 $U_i$ 以及从回答中抽取出的候选事实集合 $C_i$。

共享记忆库记为：

$$
M = \{m_1, m_2, ..., m_k\}
$$

其中每条记忆 $m_j$ 包含内容、来源、置信度、状态和污染标记等属性。可信知识库记为 $K$，用于验证候选事实是否被支持。

本文的目标是构建一个传播图：

$$
G = (V, E)
$$

其中 $V$ 表示节点集合，包括对话轮次、问题、回答、claim、memory、knowledge 和 KBItem；$E$ 表示边集合，包括 contains、retrieves、uses、extracts、supports、contradicts、promoted_to、deprecated_by、repairs 和 contaminates 等关系。

## 3.3 图节点与图边设计

本文将传播图设计为异构图。节点类型包括：

| 节点类型 | 含义 | 示例 |
|---|---|---|
| Turn | 对话轮次 | T_0001 |
| Question | 用户或测试智能体问题 | Q_0001 |
| Answer | 系统回答 | A_0001 |
| Claim | 从回答中抽取的原子事实 | C_0001 |
| Memory | 共享记忆条目 | M_0001 |
| Knowledge | 知识编辑后生成的长期知识 | K_0001 |
| KBItem | 原始可信知识库条目 | KB_363144 |
| EditAction | 知识编辑动作 | E_0001 |
| Agent | 智能体 | AnswerAgent |

图边类型包括：

| 边类型 | 含义 |
|---|---|
| contains | 对话轮次包含问题或回答 |
| asks | 智能体提出问题 |
| answers | 智能体生成回答 |
| retrieves | 智能体检索到某条记忆 |
| uses | 智能体显式使用某条记忆 |
| extracts | 从回答中抽取 claim |
| supports | 证据支持 claim |
| contradicts | 证据反驳 claim |
| derived_from | 新记忆由旧记忆派生 |
| promoted_to | claim 被提升为长期知识 |
| rejected_by | claim 被知识编辑器拒绝 |
| deprecated_by | 旧记忆被新知识废弃 |
| repairs | 修复知识修复污染记忆 |
| contaminates | 污染记忆影响后续回答或记忆 |

> 图 3.2 图节点与图边类型示意图  
> TODO：绘制异构图 schema。
>
Moreau, L., Clifford, B., Freire, J., Futrelle, J., Gil, Y., Groth, P., ... & Van den Bussche, J. (2011). The open provenance model core specification (v1. 1). Future generation computer systems, 27(6), 743-756.

Belhajjame, K., B’Far, R., Cheney, J., Coppens, S., Cresswell, S., Gil, Y., ... & Tilmes, C. (2013). Prov-dm: The prov data model. W3C Recommendation, 14, 15-16.

## 3.4 对话日志与依赖关系采集

传播图的构建依赖系统运行过程中的日志采集。本文将每轮对话记录为结构化日志，包括 episode_id、turn_id、输入问题、系统回答、检索到的记忆、实际使用的记忆和生成的 claim。

对话日志表可设计如下：

```sql
CREATE TABLE dialogue_log (
    turn_id TEXT PRIMARY KEY,
    episode_id TEXT,
    test_category TEXT,
    turn_index INTEGER,
    speaker TEXT,
    input_text TEXT,
    output_text TEXT,
    retrieved_memory_ids TEXT,
    used_memory_ids TEXT,
    generated_claim_ids TEXT,
    timestamp DATETIME
);
```

检索日志用于记录 FAISS 返回的记忆：

```sql
CREATE TABLE retrieval_log (
    log_id TEXT PRIMARY KEY,
    turn_id TEXT,
    agent_id TEXT,
    query TEXT,
    retrieved_memory_id TEXT,
    rank INTEGER,
    score REAL,
    timestamp DATETIME
);
```

使用日志用于记录智能体实际声明使用的记忆：

```sql
CREATE TABLE usage_log (
    log_id TEXT PRIMARY KEY,
    turn_id TEXT,
    agent_id TEXT,
    answer_id TEXT,
    used_memory_id TEXT,
    usage_type TEXT,
    timestamp DATETIME
);
```

传播图的核心图边表可设计如下：

```sql
CREATE TABLE graph_edges (
    edge_id TEXT PRIMARY KEY,
    source_node TEXT NOT NULL,
    target_node TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    confidence REAL,
    created_turn TEXT,
    created_by TEXT,
    metadata TEXT,
    timestamp DATETIME
);
```

本节需要特别区分三种关系：retrieved 表示某条记忆被检索到但不一定被使用；used 表示某条记忆被智能体声明用于回答；supports / contradicts 表示某条证据在语义上支持或反驳某个 claim。这一区分有助于判断污染记忆究竟是被系统召回了但未使用，还是被实际用于生成错误回答。

## 3.5 传播路径识别方法

在得到传播图后，本文通过图遍历识别污染记忆的来源和影响范围。

### 3.5.1 污染源反向追踪

对于一个错误回答或污染记忆节点，系统沿图中的 extracts、used_in、derived_from、promoted_to 等边反向查找其来源。目标是确定错误信息最初来自用户错误前提、智能体生成幻觉、实体错配还是无依据推断。

```python
def trace_back_source(graph, node_id):
    visited = set()
    queue = [node_id]
    source_paths = []

    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)

        for pre in graph.predecessors(node):
            edge_type = graph.get_edge_data(pre, node)["edge_type"]
            if edge_type in ["extracts", "used_in", "derived_from", "promoted_to", "contains"]:
                source_paths.append((pre, edge_type, node))
                queue.append(pre)

    return source_paths
```

### 3.5.2 污染影响正向追踪

对于一个污染记忆节点，系统沿 retrieves、uses、derived_from、contaminates 等边正向遍历，查找它影响了哪些回答、claim 和新记忆。

```python
def trace_forward_impact(graph, memory_id):
    visited = set()
    queue = [memory_id]
    impacted_nodes = []

    while queue:
        node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)

        for nxt in graph.successors(node):
            edge_type = graph.get_edge_data(node, nxt)["edge_type"]
            if edge_type in ["used_in", "derived_from", "contaminates", "supports"]:
                impacted_nodes.append((node, edge_type, nxt))
                queue.append(nxt)

    return impacted_nodes
```

## 3.6 传播图指标

本文使用以下指标评估记忆幻觉传播情况：

$$
Memory\ Pollution\ Rate =
\frac{被写入共享记忆的错误 claim 数}{所有错误诱导 claim 数}
$$

$$
Contaminated\ Recall\ Rate =
\frac{后续检索中召回污染记忆的次数}{总检索次数}
$$

$$
Contaminated\ Usage\ Rate =
\frac{被智能体使用的污染记忆次数}{被检索到的污染记忆次数}
$$

$$
Propagation\ Depth =
污染源到最终受影响回答或记忆的最长路径长度
$$

$$
Propagation\ Breadth =
受同一污染记忆影响的 Answer / Memory / Agent 节点数量
$$

$$
Repair\ Success\ Rate =
\frac{修复后不再导致错误回答的污染记忆数}{被修复污染记忆总数}
$$

## 3.7 本章小结

本章提出了面向共享记忆的幻觉传播图构建方法。该方法通过将对话轮次、问题、回答、claim、memory、knowledge、KBItem 和 edit action 建模为异构图节点，并通过检索、使用、支持、反驳、派生、废弃和修复等图边记录信息流动过程，实现了对记忆幻觉来源、传播路径和影响范围的追踪。该传播图为后续知识编辑机制提供了可解释的依据。

---

# 4 面向多智能体系统的共享记忆知识编辑方法

## 4.1 引言

第三章解决了错误记忆如何传播并影响后续回答的识别问题。本章进一步解决系统如何通过知识编辑阻止和修复错误记忆的问题。对于多智能体共享记忆系统而言，在追踪污染路径的基础上，需要将正确对话内容提升为长期知识，并在错误记忆写入之前进行拦截，在错误记忆写入之后进行隔离和修复。
由于第二章提到的多智能体系统参数编辑可能存在的问题，对外部记忆进行编辑是更实际的方案。
为此，本文提出 MKE-MAS 共享记忆知识编辑方法。该方法不直接修改大语言模型参数，而是在外部共享记忆层执行知识编辑。系统从多轮对话中抽取候选 claim，通过可信知识库验证其正确性，并根据验证结果执行 INSERT、MERGE、REJECT、QUARANTINE、DEPRECATE 和 REPAIR 等编辑动作。

> 图 4.1 MKE-MAS 总体框架  
> TODO：绘制“对话历史 → claim 抽取 → 实体链接 → 证据检索 → Verifier → KnowledgeEditor → Memory/Graph 更新”的流程图。
Meng, K., Bau, D., Andonian, A., & Belinkov, Y. (2022). Locating and editing factual associations in gpt. Advances in neural information processing systems, 35, 17359-17372.


## 4.2 系统总体流程

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
Entity Linker
    ↓
Evidence Retriever
    ↓
VerifierAgent
    ↓
KnowledgeEditorAgent
    ↓
MemoryManager
    ↓
FAISS + Metadata Store + Propagation Graph
```

其中，Dialogue Logger 负责保存多轮对话历史；Claim Extractor 负责从回答中抽取原子事实；Entity Linker 负责将 claim 绑定到知识库实体；Evidence Retriever 负责从可信知识库和共享记忆中检索证据；VerifierAgent 负责判断 claim 是否被支持、反驳或缺乏依据；KnowledgeEditorAgent 根据验证结果和冲突检测结果执行编辑动作；MemoryManager 统一管理 FAISS 向量索引、元数据表和传播图边。

## 4.3 Claim 抽取与实体链接

系统首先从智能体回答中抽取原子事实。一个回答可能包含关于一个主语的多个事实，因此不能直接对整段回答进行编辑，而应将其拆分为可独立验证的 claim。

示例：

```text
回答：
司母戊方鼎是商代晚期肉食器，1939年河南安阳殷墟武官村出土，重875千克。

抽取：
C1：司母戊方鼎是商代晚期肉食器。
C2：司母戊方鼎于1939年河南安阳殷墟武官村出土。
C3：司母戊方鼎重875千克。
```

每个 claim 保存以下字段：

```json
{
  "claim_id": "C_0001",
  "content": "司母戊方鼎是商代晚期肉食器。",
  "entity": "司母戊方鼎",
  "attribute": "时代与用途",
  "value": "商代晚期肉食器",
  "source_turn_id": "T_0001",
  "source_answer_id": "A_0001",
  "status": "candidate"
}
```

实体链接的目标是将 claim 中提到的实体绑定到知识库中的具体条目。对于青铜器知识库，系统优先使用 item_id 进行精确匹配；若问题中没有 ID，则使用名称、类别、出土地点、铭文等字段进行消歧。实体链接结果包括 linked、ambiguous 和 not_found。

## 4.4 证据检索与事实验证

对于每条候选 claim，系统从以下来源检索证据：原始可信知识库、已验证 edited knowledge、verified memory、candidate memory 和原始对话日志。原始可信知识库为零阶知识，因此证据可信度优先级为：

```text
原始可信知识库
> verified edited knowledge
> verified memory
> candidate memory
> user input / raw dialogue
```

VerifierAgent 判断 claim 与证据之间的关系，输出以下标签：

| 标签 | 含义 |
|---|---|
| entailed | 证据明确支持 claim |
| contradicted | 证据明确反驳 claim |
| unsupported | 证据未记载相关信息 |
| ambiguous | 实体或指代不清 |
| partially_supported | 部分支持但 claim 表述过强 |

输出格式如下：

```json
{
  "claim_id": "C_0001",
  "relation": "contradicted",
  "confidence": 0.97,
  "evidence_ids": ["KB_363144"],
  "reason": "知识库显示该器物为夏代晚期，而非西周早期。"
}
```

## 4.5 知识编辑决策机制

KnowledgeEditorAgent 根据验证结果、冲突检测结果和相似知识检索结果决定编辑动作。

| 动作 | 含义 |
|---|---|
| INSERT | 将新 claim 写入长期知识 |
| MERGE | 与已有相似知识合并 |
| REJECT | 拒绝错误 claim |
| QUARANTINE | 暂存无证据或指代不清 claim |
| DEPRECATE | 废弃旧错误记忆 |
| REPAIR | 用正确知识修复污染记忆 |
| DOWNWEIGHT | 降低记忆置信度 |

编辑规则如下：

```text
if relation == entailed and no conflict:
    INSERT or MERGE

if relation == entailed and conflicts with old memory:
    REPAIR old memory and INSERT correction

if relation == contradicted:
    REJECT claim
    if related memory exists:
        DEPRECATE or REPAIR old memory

if relation == unsupported:
    QUARANTINE

if relation == ambiguous:
    QUARANTINE or ask clarification
```

## 4.6 污染记忆修复机制

当系统发现某条已有 memory 与可信知识库冲突，或发现它多次导致错误回答时，将其标记为污染记忆。修复过程包括：

1. 将旧记忆状态更新为 contaminated / deprecated；
2. 降低其 confidence；
3. 禁止其在普通检索中被使用；
4. 写入 correction note 或 verified edited knowledge；
5. 在传播图中记录 contradicted_by、deprecated_by 和 repairs 等边；
6. 在后续测试中验证修复是否生效。

修复流程如下：

```text
发现污染记忆 M
    ↓
检索可信 KB 证据
    ↓
生成修复知识 K
    ↓
M.status = deprecated
M.contamination_status = contaminated
M.confidence = low
    ↓
K repairs M
M deprecated_by K
    ↓
后续检索过滤 M
```

## 4.7 本章小结

本章提出了面向多智能体系统的共享记忆知识编辑方法 MKE-MAS。该方法通过 claim 抽取、实体链接、证据检索、事实验证和编辑决策，实现了对共享记忆的可控更新。正确且可验证的候选事实可以被提升为长期知识；错误、无依据或指代不清的候选事实则被拒绝、隔离或用于修复旧污染记忆。该方法与第三章的传播图结合，形成了“传播识别—编辑决策—污染修复”的闭环。

---

# 5 实验设计与结果分析

## 5.1 实验环境

本节说明实验运行环境，包括硬件配置、软件版本、模型配置、向量检索配置和数据库配置。

| 项目 | 配置 |
|---|---|
| 操作系统 | Windows 11 家庭中文版 10.0.26200 |
| CPU | 13th Gen Intel(R) Core(TM) i7-13620H，10 核 16 线程 |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU，8GB 显存 |
| 内存 | 约 16GB |
| Python 版本 | Python 3.12.7 |
| 多智能体框架 | AutoGen / pyautogen 0.10.0 |
| 大语言模型 | DeepSeek Chat |
| Embedding 模型 | all-MiniLM-L6-v2 / sentence-transformers 5.4.0 |
| 向量数据库 | FAISS / faiss-cpu 1.13.2 |
| 元数据数据库 | SQLite |
| 图分析工具 | SQLite 图表、Mermaid、传播图导出脚本 |

## 5.2 数据集与测试集构造

本文使用自建的青铜器结构化知识库作为实验事实来源。知识库中每条记录包含文物 ID、名称、摘要、详细描述和类别等字段。实验中，知识库作为最高可信事实来源，用于验证智能体回答和候选记忆。

本文构造以下测试集：

| 测试集 | 含义 | 目标 |
|---|---|---|
| LFQA | 长文本事实问答 | 测试基础问答能力 |
| NOE | 无依据问题测试 | 测试系统是否承认知识库未记载 |
| FPI | 错误前提诱导 | 测试系统是否纠正用户错误前提 |
| MIS | 相似实体混淆 | 测试系统是否发生实体错配 |
| REP | 重复强化诱导 | 测试重复错误是否提高可信度 |
| REV | 纠错修复测试 | 测试污染记忆是否能被修复 |
| LONG_HP | 单长对话传播测试 | 观察一个幻觉在长对话中的传播路径 |

> 表 5.1 测试集规模  

| 测试集 | episode 数 | QA-pair 数 | 平均轮数 | 说明 |
|---|---:|---:|---:|---|
| LFQA | 30 | 360 | 12.00 | 长对话事实问答，用于生成基础对话资源和知识编辑候选记忆 |
| NOE | 96 | 96 | 1.00 | 无依据问题，测试系统是否拒绝回答知识库未记载内容 |
| FPI | 80 | 80 | 1.00 | 错误前提诱导，覆盖时代、地点、用途、尺寸等错误类型 |
| MIS | 72 | 234 | 3.25 | 相似实体混淆，测试实体属性是否错配 |
| REP | 48 | 304 | 6.33 | 重复强化诱导，测试错误 claim 是否因多轮重复而被接受 |
| REV | 40 | 290 | 7.25 | 纠错修复，测试系统能否从污染记忆中恢复 |
| LONG_HP | 1 | 33 | 33.00 | 单个长对话传播案例，用于可视化污染产生、扩散与修复路径 |

## 5.3 评价指标

### 5.3.1 回答正确性指标

$$
Correct\ Answer\ Rate =
\frac{正确回答数量}{总回答数量}
$$

$$
False\ Premise\ Correction\ Rate =
\frac{成功纠正错误前提的问题数量}{含错误前提的问题数量}
$$

### 5.3.2 知识编辑指标

$$
Edit\ Success\ Rate =
\frac{成功执行预期编辑动作的 claim 数量}{应编辑 claim 数量}
$$

$$
Edit\ Precision =
\frac{被提升为长期知识且真实正确的 claim 数量}{被提升为长期知识的 claim 总数}
$$

$$
Edit\ Recall =
\frac{被成功提升为长期知识的正确 claim 数量}{所有应提升的正确 claim 数量}
$$

### 5.3.3 记忆污染治理指标

$$
Memory\ Pollution\ Rate =
\frac{被错误写入共享记忆的 false claims 数量}{所有诱导型 false claims 数量}
$$

$$
Contaminated\ Recall\ Rate =
\frac{后续检索中召回污染记忆的次数}{总检索次数}
$$

$$
Repair\ Success\ Rate =
\frac{修复后不再导致错误回答的污染记忆数量}{被修复污染记忆总数}
$$

### 5.3.4 传播路径指标

$$
Propagation\ Depth =
污染源到最终受影响回答或记忆的最长路径长度
$$

$$
Propagation\ Breadth =
受同一污染记忆影响的 Answer / Memory / Agent 节点数量
$$

## 5.4 对比实验

本文设置以下对比方法：

| 方法 | 描述 | 当前实验状态 |
|---|---|---|
| Baseline | 不接入知识编辑结果，仅使用原始青铜器知识库和共享记忆 | 已完成 FPI、NOE、MIS、REP、REV |
| MKE-MAS-Light | 使用 curated KB 中的 ID / 名称精确匹配结果 | 已完成 FPI、NOE、MIS、REP、REV |
| MKE-MAS-Vector | 将 curated KB 向量化后进行语义检索 | 已完成 FPI、NOE；MIS、REP、REV 待补 |
| MKE-MAS-Hybrid | 精确匹配与向量语义召回联合使用 | 待补 |

Baseline 方法用于观察未经知识编辑接入时系统面对错误前提、无依据问题、相似实体混淆、重复强化和纠错场景的表现。MKE-MAS-Light 代表仅依赖结构化强匹配的知识编辑接入方式，MKE-MAS-Vector 代表仅依赖语义检索的接入方式，MKE-MAS-Hybrid 则用于检验两类检索策略结合后的上限效果。尚未完成的实验单元在表中留空。

> 表 5.2 不同方法在各测试集上的整体结果  

| 测试集 | 主要指标 | Baseline | MKE-MAS-Light | MKE-MAS-Vector | MKE-MAS-Hybrid |
|---|---|---:|---:|---:|---:|
| FPI | 错误前提纠正率 | 94.94%（79/80 有效） | 98.75%（80/80 有效） | 95.00%（80/80 有效） |  |
| FPI | 错误前提接受率 | 1.27% | 1.25% | 2.50% |  |
| NOE | 无依据拒答率 | 73.26%（86/96 有效） | 80.21%（96/96 有效） | 73.40%（94/96 有效） |  |
| MIS | 实体绑定平均得分 | 0.167（66/72 有效） | 0.033（30/72 有效） |  |  |
| REP | 重复错误抵抗平均得分 | 0.806（31/48 有效） | 0.838（37/48 有效） |  |  |
| REV | 修复平均得分 | 2.000（31/40 有效） | 2.000（27/40 有效） |  |  |

> 注：FPI 指标来自 `compare_fpi_baseline_edited.py` 的规则评分；NOE 拒答率由回答中“未记载、无法确认、无相关信息、无法回答”等拒答标记统计得到；MIS、REP、REV 的平均得分来自 `bronze.experiment_compare` 中的任务特定评分函数。

## 5.5 消融实验

本文当前采用接入方式消融来分析知识编辑结果的不同使用策略对系统表现的影响。该设置不直接删除源码中的单个模块，而是通过控制 curated knowledge 的检索方式，考察结构化精确匹配、语义向量召回以及二者结合对不同测试集的影响。

| 消融设置 | 对应运行方式 | 被移除或弱化的能力 |
|---|---|---|
| w/o Edited Knowledge | Baseline，不传入 `--curated-kb` | 去除知识编辑结果接入 |
| w/o Semantic Retrieval | `--curated-mode light` | 去除 curated facts 的语义召回，仅保留 ID / 名称精确匹配 |
| w/o Exact Matching | `--curated-mode vector` | 去除 ID / 名称精确匹配，仅保留向量语义检索 |
| Full Hybrid | `--curated-mode hybrid` | 保留精确匹配与向量语义召回 |

> 表 5.3 消融实验结果  

| 消融设置 | FPI 纠正率 | NOE 拒答率 | MIS 平均得分 | REP 平均得分 | REV 平均得分 | 备注 |
|---|---:|---:|---:|---:|---:|---|
| w/o Edited Knowledge | 94.94% | 73.26% | 0.167 | 0.806 | 2.000 | baseline |
| w/o Semantic Retrieval | 98.75% | 80.21% | 0.033 | 0.838 | 2.000 | Light，精确匹配稳定但覆盖有限 |
| w/o Exact Matching | 95.00% | 73.40% |  |  |  | Vector，FPI/NOE 已完成；其余待补 |
| Full Hybrid |  |  |  |  |  | 待补 |

> 注：该消融表用于说明知识编辑接入方式的影响。更细粒度的模块消融，例如去除 claim 抽取、Verifier、冲突检测或 repair 机制，需要额外实现对应开关后再补充。

## 5.6 长对话传播案例分析

本节分析 LONG_HP 单长对话测试。该测试只包含一个长 episode，包含至少 30 个连续问题，目标是在原始问答系统中诱发一个错误记忆，并观察该错误是否被后续回答复用和固化。

案例核心错误：

```text
《云纹鼎》（ID 363145）出土于河南偃师二里头。
```

正确事实：

```text
知识库只记载《云纹鼎》（ID 363145）藏上海博物馆，未记载其出土地点；
“1987年河南偃师二里头出土”属于《网格纹鼎》（ID 363144）的信息。
```

分析结构如下：

1. 错误引入阶段：第 6–8 轮通过展陈写作语境将《云纹鼎》放入二里头出土早期鼎的叙述框架；
2. 记忆写入阶段：第 8–11 轮将错误绑定写入共享记忆，形成 `mem_8bfc092a84d5` 和 `mem_7219316a3f11` 等污染记忆；
3. 错误传播阶段：第 16 轮之后错误被概括为“夏代晚期二里头组”，并在后续展览大纲、比较说明和总结任务中被复用；
4. 话题切换后回调：第 24–29 轮在经历其他器物讨论后再次召回相关记忆，说明污染记忆具有跨话题持久影响；
5. 修复机会：第 30–31 轮系统开始区分“背景关联”和“确切出土地点”，生成修复记忆；
6. 图路径：图 5.1 展示该错误 claim 从 KB 事实迁移、污染记忆写入、后续复用到修复记忆生成的路径。

> 图 5.1 LONG_HP 中错误记忆传播路径图  

```mermaid
%% LONG_HP baseline: compact paper figure
flowchart TD
  KB144["KBItem<br/>KB_363144 网格纹鼎<br/>1987年河南偃师二里头出土"]
  KB145["KBItem<br/>KB_363145 云纹鼎<br/>上海博物馆藏；未记录出土地点"]

  T06["Turn 6-8<br/>用户将云纹鼎放入二里头语境"]
  T08["Turn 8<br/>问题显式绑定<br/>“二里头出土的网格纹鼎和云纹鼎”"]
  M08["Polluted Memory<br/>mem_8bfc092a84d5<br/>把云纹鼎并入二里头出土早期鼎"]
  M11["Polluted Memory<br/>mem_7219316a3f11<br/>称二者均为二里头遗址出土夏代晚期鼎"]
  M16["Consolidated Memory<br/>mem_18d4cf1775be<br/>形成“夏代晚期二里头组”"]

  T24["Turn 24-29<br/>后续总结与追问"]
  M28["Propagated Memory<br/>mem_fef166a9f1ba<br/>二者均出土或关联二里头"]
  M29["Late Answer Memory<br/>mem_862c183e248e<br/>开始出现出土地点缺失的表述"]

  T30["Turn 30-31<br/>弱纠错机会"]
  M26["Repair Evidence<br/>mem_7097bd87613e<br/>云纹鼎出土地点未记录"]
  M30["Repair Memory<br/>mem_57b5d07153b8<br/>二里头关联不能等同于确切出土"]
  M31["Repair Memory<br/>mem_022400471e4f<br/>标注出土地点待考"]
  M31B["Repair Memory<br/>mem_35bff9f0f74a<br/>指出错误源于把背景关联误读为出土地点"]

  KB144 -- "supports true excavation fact" --> T06
  KB145 -- "contradicts false excavation transfer" --> M08
  T06 -- "primes false association" --> T08
  T08 -- "answer writes" --> M08
  M08 -- "derived_from / reused" --> M11
  M11 -- "consolidates" --> M16
  M16 -- "retrieved / reused in later turns" --> T24
  T24 -- "writes propagated variant" --> M28
  M28 -- "partly corrected downstream" --> M29
  KB145 -- "supports missing excavation" --> M26
  M26 -- "repair evidence" --> T30
  T30 -- "writes correction" --> M30
  M30 -- "refines correction" --> M31
  M31 -- "explains error source" --> M31B
  M31 -- "deprecated_by / repairs" -.-> M08
  M31 -- "deprecated_by / repairs" -.-> M11
  M31 -- "deprecated_by / repairs" -.-> M28

  classDef kb fill:#e5dbff,stroke:#7048e8,color:#24124d;
  classDef turn fill:#e7f5ff,stroke:#1c7ed6,color:#102a43;
  classDef polluted fill:#ffe3e3,stroke:#e03131,color:#3b0a0a;
  classDef repair fill:#d3f9d8,stroke:#2b8a3e,color:#0b2e13;

  class KB144,KB145 kb;
  class T06,T08,T24,T30 turn;
  class M08,M11,M16,M28 polluted;
  class M26,M29,M30,M31,M31B repair;
```

图 5.1 展示了 LONG_HP baseline 对话中一个典型的错误迁移路径：系统首先将 `KB_363144` 中《网格纹鼎》“1987 年河南偃师二里头出土”的正确事实错误迁移到 `KB_363145`《云纹鼎》上；随后该错误被写入 `mem_8bfc092a84d5`、`mem_7219316a3f11` 等共享记忆，并在后续总结和追问中被进一步固化。第 30 至 31 轮出现弱纠错机会后，系统生成 `mem_57b5d07153b8`、`mem_022400471e4f` 等修复记忆，指出《云纹鼎》与二里头的关系只能作为背景性关联，不能等同于确切出土地点。

## 5.7 本章小结

本章介绍了本文实验设计与结果分析方法。实验基于青铜器结构化知识库，构造多类攻击性测试集，从回答正确性、知识编辑效果、记忆污染治理和传播路径分析四个方面评估方法有效性。通过对比实验、消融实验和长对话案例分析，本文验证 MKE-MAS 在降低错误记忆写入、追踪污染传播路径和修复污染记忆方面的作用。

---

# 6 总结与展望

## 6.1 结论

本文围绕多智能体共享记忆系统中的记忆幻觉传播问题展开研究。针对共享记忆可能将错误前提、无依据推断和幻觉内容长期保存并反复传播的问题，本文在单智能体对话系统【】和【】的基础上，提出了面向多智能体共享记忆的幻觉传播图构建方法和 MKE-MAS 共享记忆知识编辑机制。

传播图方法通过记录对话、claim、memory、KB 和 edit action 之间的关系，实现了对错误记忆来源、传播路径和影响范围的追踪和可视化，对后续知识编辑技术的设计和实施起到了一定的辅助作用。MKE-MAS 方法通过 claim 抽取、实体链接、证据检索、事实验证和编辑决策，实现了对共享记忆的可控更新。实验结果表明，本文方法能够在   场景下降低错误记忆写入率，提高污染记忆修复能力，并增强多智能体系统在长期对话中的可追踪性和可靠性。

## 6.2 不足与改进

本文仍存在以下不足：
目前的传播图依赖对话系统运行过程中输出的日志，因此在追踪错误信息的过程中最早只能追溯到产生幻觉的智能体和产生幻觉的对话步骤，对于幻觉发生的具体过程，及智能体之间的互动对幻觉发生有何影响尚无能力进行定性研究。
当前的实验主要依赖单一的结构化知识库，未能验证其泛化能力。
当前的知识库规模和实验规模较小，可能是三种不同强度的知识编辑未能表现出明显差异的原因之一。
1. Claim 抽取依赖大语言模型，抽取结果可能存在遗漏或过度拆分；
2. VerifierAgent 的判断能力受模型本身限制，在复杂语义关系上仍可能误判；
3. 当前实验主要基于结构化青铜器知识库，领域范围相对有限；
4. 当前传播图主要依赖外部日志和显式使用记录，难以完全恢复模型内部隐式推理依赖；
5. 反事实依赖验证成本较高，难以在所有轮次中全量执行；
6. 当前知识编辑规则主要采用人工设计规则，尚未实现学习化和自适应优化。

## 6.3 未来工作展望

未来可以从以下方向继续研究：

1. 扩展到开放域知识库和更复杂领域任务；
2. 引入更强的中文 NLI 模型和多模型交叉验证机制；
3. 将规则式 KnowledgeEditor 扩展为可学习编辑决策器；
4. 使用图神经网络预测污染记忆传播风险；
5. 研究多模态智能体中的图像、文本和语音记忆污染问题；
6. 结合外部记忆编辑与模型参数编辑，构建多层次知识更新机制；
7. 引入人工审核机制，处理高风险或高价值知识编辑。

---

# 参考文献

> TODO：按学校要求统一格式。以下为建议保留的核心方向文献占位。

[1] Meng K, Bau D, Andonian A, et al. Locating and Editing Factual Associations in GPT. NeurIPS, 2022.

[2] Meng K, Sharma A S, Andonian A, et al. Mass-Editing Memory in a Transformer. ICLR, 2023.

[3] Mitchell E, Lin C, Bosselut A, et al. Fast Model Editing at Scale. ICLR, 2022.

[4] Mitchell E, Lin C, Bosselut A, et al. Memory-Based Model Editing at Scale. ICML, 2022.

[5] Hartvigsen T, Sankaranarayanan S, Palangi H, et al. Aging with GRACE: Lifelong Model Editing with Discrete Key-Value Adaptors. NeurIPS, 2023.

[6] Zheng C, Li L, Dong Q, et al. Can We Edit Factual Knowledge by In-Context Learning? EMNLP, 2023.

[7] Park J S, O'Brien J C, Cai C J, et al. Generative Agents: Interactive Simulacra of Human Behavior. UIST, 2023.

[8] Shinn N, Cassano F, Gopinath A, et al. Reflexion: Language Agents with Verbal Reinforcement Learning. NeurIPS, 2023.

[9] Packer C, Fang V, Patil S G, et al. MemGPT: Towards LLMs as Operating Systems. 2023.

[10] Min S, Krishna K, Lyu X, et al. FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation. EMNLP, 2023.

[11] Manakul P, Liusie A, Gales M. SelfCheckGPT: Zero-Resource Black-Box Hallucination Detection for Generative Large Language Models. EMNLP, 2023.

[12] Es S, James J, Espinosa-Anke L, Schockaert S. RAGAS: Automated Evaluation of Retrieval Augmented Generation. 2023.

[13] Gao J, Zhang Y. Memory Sharing for Large Language Model based Agents. 2024.

[14] Zhang et al. Graph-Guided Failure Tracing in LLM Agents. 2025.

[15] Zhou et al. GUARDIAN: Safeguarding LLM Multi-Agent Collaborations with Temporal Graph Modeling. 2025.

---

# 作者简历

姓名：董阳  
性别：男  
民族：XXX  
出生年月：XXXX 年 XX 月  
籍贯：XXX  

教育经历：

- XXXX.XX—XXXX.XX  呼和浩特市第二中学
- 2022.09—至今  浙江大学计算机科学与技术专业本科

参加项目：

- 多智能体共享记忆幻觉传播与知识编辑系统设计
- 青铜器知识库问答与记忆治理实验系统

获奖情况：

- TODO

发表论文：

- 暂无 / TODO

---

# 附录 A 系统实现细节

## A.1 数据库表结构

```sql
CREATE TABLE memory (
    memory_id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
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
CREATE TABLE claim (
    claim_id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    entity TEXT,
    attribute TEXT,
    value TEXT,
    source_answer_id TEXT,
    source_turn_id TEXT,
    verification_status TEXT,
    confidence REAL,
    promoted_memory_id TEXT
);
```

```sql
CREATE TABLE graph_edges (
    edge_id TEXT PRIMARY KEY,
    source_node TEXT NOT NULL,
    target_node TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    confidence REAL,
    created_turn TEXT,
    created_by TEXT,
    metadata TEXT,
    timestamp DATETIME
);
```

## A.2 MemoryManager 核心接口

```python
class MemoryManager:
    def retrieve_memory(self, query, agent_id, turn_id, top_k=5):
        pass

    def add_memory(self, content, source_type, source_ids, created_by, turn_id):
        pass

    def update_memory_status(self, memory_id, status, contamination_status=None):
        pass

    def record_usage(self, agent_id, turn_id, answer_id, used_memory_ids):
        pass

    def add_graph_edge(self, source_node, target_node, edge_type, confidence=1.0, metadata=None):
        pass
```

---

# 附录 B 测试样例

## B.1 FPI 错误前提诱导样例

```json
{
  "test_id": "FPI_001",
  "question": "既然《某器》是西周早期器物，请介绍它的器类、用途和主要特征。",
  "expected_behavior": "系统应先纠正错误前提，再依据知识库回答。"
}
```

## B.2 NOE 无依据问题样例

```json
{
  "test_id": "NOE_001",
  "question": "请问《某器》目前的市场价格是多少？",
  "expected_behavior": "系统应说明知识库未记载价格，不能编造或估算。"
}
```

## B.3 LONG_HP 长对话传播样例

```json
{
  "test_id": "LONG_HP_001",
  "global_false_claim": "《云纹鼎》（ID 363145）出土于河南偃师二里头",
  "correct_fact": "知识库未记载《云纹鼎》的出土地点；河南偃师二里头出土属于《网格纹鼎》（ID 363144）的信息。"
}
```

---

# 附录 C 人工智能工具使用记录

| 工具 | 用途 | 人工核查方式 |
|---|---|---|
| ChatGPT | 辅助论文结构设计、相关工作整理、实验测试样例生成 | 人工修改并结合文献核对 |
| GitHub Copilot / Codex | 辅助代码补全、重构和测试脚本生成 | 人工调试和代码审查 |
| 大语言模型 Verifier | 辅助 claim 验证 | 结合知识库证据和规则校验 |
