import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from autogen import AssistantAgent, GroupChat, GroupChatManager, UserProxyAgent

sys.path.append(str(Path(__file__).resolve().parents[1]))

from vector_db import VectorDatabase
from bronze.bronze_memory import ArchitectureMemory
from bronze.bronze_processor import BronzeDataProcessor


DEEPSEEK_API_KEY = "sk-ddccf24607e14709a73739f0dfcb9a4d"
MODEL_PATH = "./models/all-MiniLM-L6-v2"
BRONZE_DATA_FILE = "bronze_items.json"

SEQUENTIAL = "sequential"
PEER = "peer"

ARCHITECTURES: Dict[str, Dict[str, str]] = {
    SEQUENTIAL: {
        "label": "分析问题-回答-校对架构",
        "vector_db": "vector_db_bronze_sequential",
        "memory": "bronze_memory_sequential.json",
    },
    PEER: {
        "label": "对等协同架构",
        "vector_db": "vector_db_bronze_peer",
        "memory": "bronze_memory_peer.json",
    },
}


def safe_print(message: str = "") -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(message.encode(encoding, errors="replace").decode(encoding))


def llm_config() -> Dict[str, object]:
    os.environ["DEEPSEEK_API_KEY"] = DEEPSEEK_API_KEY
    return {
        "config_list": [
            {
                "model": "deepseek-chat",
                "api_key": DEEPSEEK_API_KEY,
                "base_url": "https://api.deepseek.com/v1",
            }
        ]
    }


def initialize_bronze_system(architecture: str) -> Tuple[VectorDatabase, ArchitectureMemory]:
    if architecture not in ARCHITECTURES:
        raise ValueError(f"未知架构: {architecture}")

    config = ARCHITECTURES[architecture]
    vector_db = VectorDatabase(db_path=config["vector_db"], model_path=MODEL_PATH)
    processor = BronzeDataProcessor(BRONZE_DATA_FILE)
    texts = processor.generate_text_representations()

    if not has_bronze_dataset(vector_db):
        safe_print(f"正在初始化青铜器知识库: {processor.count()} 条")
        existing = set(vector_db.id_to_text.values())
        added = 0
        for text in texts:
            if text not in existing:
                vector_db.add_text(text)
                existing.add(text)
                added += 1
        vector_db.save()
        safe_print(f"青铜器知识库初始化完成，新增 {added} 条")
    else:
        safe_print("青铜器知识库已存在，跳过初始化")

    memory = ArchitectureMemory(config["memory"], vector_db=vector_db)
    return vector_db, memory


def has_bronze_dataset(vector_db: VectorDatabase) -> bool:
    return any(str(text).startswith("青铜器: ") for text in vector_db.id_to_text.values())


def build_context(vector_db: VectorDatabase, memory: ArchitectureMemory, question: str) -> Tuple[str, List[str]]:
    results = vector_db.search(question, top_k=8)
    lines: List[str] = []
    raw_contexts: List[str] = []

    for index, item in enumerate(results, start=1):
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        distance = item.get("distance", "")
        raw_contexts.append(text)
        lines.append(f"[{index}] distance={distance}\n{text}")

    recent_memory = memory.get_recent_conversations(limit=3)
    memory_lines = []
    for item in recent_memory:
        memory_lines.append(
            f"用户: {item.get('user_question', '')}\n回答: {item.get('final_answer', '')}"
        )

    context = (
        "【检索到的青铜器知识】\n"
        + ("\n\n".join(lines) if lines else "无")
        + "\n\n【本架构最近对话记忆】\n"
        + ("\n\n".join(memory_lines) if memory_lines else "无")
    )
    return context, raw_contexts


def create_user_proxy() -> UserProxyAgent:
    return UserProxyAgent(
        name="User",
        system_message="你是青铜器知识问答系统的用户。",
        human_input_mode="NEVER",
        code_execution_config=False,
    )


def answer_with_sequential_architecture(
    question: str,
    vector_db: VectorDatabase,
    memory: ArchitectureMemory,
) -> Tuple[str, str]:
    context, supporting_context = build_context(vector_db, memory, question)
    agents = create_sequential_agents()
    manager = setup_sequential_group_chat(agents)

    message = f"""用户问题:
{question}

{context}

请按照“分析问题 -> 回答 -> 校对”的流程完成。本轮只允许基于上面的青铜器知识和本架构记忆回答；如果证据不足，请明确说明不知道或资料不足。"""

    chat_result = agents[0].initiate_chat(manager, message=message)
    history = extract_history(chat_result, manager)
    final_answer = find_last_message(history, "Answerer")
    validation = find_last_message(history, "Validator")

    if not final_answer:
        final_answer = find_last_non_user_message(history)

    memory.add_conversation(
        question,
        final_answer,
        architecture=ARCHITECTURES[SEQUENTIAL]["label"],
        validation=validation,
        supporting_context=supporting_context,
    )
    return final_answer, validation


def create_sequential_agents() -> List[object]:
    config = llm_config()
    user_proxy = create_user_proxy()

    analyzer = AssistantAgent(
        name="Analyzer",
        system_message=(
            "你是问题分析智能体。你的任务是识别用户想问的青铜器名称、器类、年代、出土地点、形制或比较关系，"
            "指出需要使用哪些检索证据。只做分析，不直接给最终答案。分析后以“分析完成，请回答智能体作答。”结尾。"
        ),
        llm_config=config,
        max_consecutive_auto_reply=1,
    )
    answerer = AssistantAgent(
        name="Answerer",
        system_message=(
            "你是回答智能体。你必须基于检索到的青铜器知识和本架构记忆回答用户问题。"
            "不要编造资料；如果上下文没有答案，说明资料不足。回答要适合一问一答长对话，清楚、直接、有依据。"
            "回答后以“回答完成，请校对智能体检查。”结尾。"
        ),
        llm_config=config,
        max_consecutive_auto_reply=1,
    )
    validator = AssistantAgent(
        name="Validator",
        system_message=(
            "你是校对智能体。检查回答是否完全受检索证据支持，是否存在记忆幻觉、过度推断或遗漏。"
            "如果通过，先写“校对通过”，再简述理由；如果不通过，先写“校对未通过”，说明问题并给出修正建议。"
        ),
        llm_config=config,
        max_consecutive_auto_reply=1,
    )
    return [user_proxy, analyzer, answerer, validator]


def setup_sequential_group_chat(agents: List[object]) -> GroupChatManager:
    def speaker_selection(last_speaker, groupchat):
        if last_speaker.name == "User":
            return next(agent for agent in agents if agent.name == "Analyzer")
        if last_speaker.name == "Analyzer":
            return next(agent for agent in agents if agent.name == "Answerer")
        if last_speaker.name == "Answerer":
            return next(agent for agent in agents if agent.name == "Validator")
        return None

    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=4,
        speaker_selection_method=speaker_selection,
    )
    return GroupChatManager(groupchat=group_chat, llm_config=llm_config())


def answer_with_peer_architecture(
    question: str,
    vector_db: VectorDatabase,
    memory: ArchitectureMemory,
) -> Tuple[str, str]:
    context, supporting_context = build_context(vector_db, memory, question)
    agents = create_peer_agents()
    manager = setup_peer_group_chat(agents)

    message = f"""用户问题:
{question}

{context}

请用“对等协同”的方式完成：各智能体从不同角度补充证据、互相纠偏，最后由最后一位发言者给出“最终协同回答”。只能基于上面的青铜器知识和本架构记忆回答；证据不足时必须说明。"""

    chat_result = agents[0].initiate_chat(manager, message=message)
    history = extract_history(chat_result, manager)
    final_answer = find_last_message(history, "FormAndUsePeer")
    if not final_answer:
        final_answer = find_last_non_user_message(history)

    collaboration_trace = "\n\n".join(
        f"{msg.get('name', '')}: {msg.get('content', '')}"
        for msg in history
        if msg.get("name") in {"FormAndUsePeer", "ChronologyPeer", "EvidencePeer"}
    )

    memory.add_conversation(
        question,
        final_answer,
        architecture=ARCHITECTURES[PEER]["label"],
        validation=collaboration_trace,
        supporting_context=supporting_context,
    )
    return final_answer, collaboration_trace


def create_peer_agents() -> List[object]:
    config = llm_config()
    user_proxy = create_user_proxy()

    form_peer = AssistantAgent(
        name="FormAndUsePeer",
        system_message=(
            "你是对等协同小组成员之一，关注青铜器的器类、形制、用途、纹饰和名称。"
            "你与其他成员地位平等，需要引用检索证据，避免编造。"
            "如果你是本轮最后一位发言者，请以“最终协同回答：”开头给出面向用户的答案。"
        ),
        llm_config=config,
        max_consecutive_auto_reply=1,
    )
    chronology_peer = AssistantAgent(
        name="ChronologyPeer",
        system_message=(
            "你是对等协同小组成员之一，关注年代、出土地、收藏地和历史背景。"
            "你需要补充或纠正同伴观点，所有判断都要受检索证据支持。"
        ),
        llm_config=config,
        max_consecutive_auto_reply=1,
    )
    evidence_peer = AssistantAgent(
        name="EvidencePeer",
        system_message=(
            "你是对等协同小组成员之一，关注证据边界、资料不足和记忆幻觉风险。"
            "你需要指出哪些内容有证据，哪些内容不能推断，并为最终回答提供约束。"
        ),
        llm_config=config,
        max_consecutive_auto_reply=1,
    )
    return [user_proxy, form_peer, chronology_peer, evidence_peer]


def setup_peer_group_chat(agents: List[object]) -> GroupChatManager:
    order = ["User", "FormAndUsePeer", "ChronologyPeer", "EvidencePeer", "FormAndUsePeer"]

    def speaker_selection(last_speaker, groupchat):
        next_index = len(groupchat.messages)
        if next_index < len(order):
            next_name = order[next_index]
            return next(agent for agent in agents if agent.name == next_name)
        return None

    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=5,
        speaker_selection_method=speaker_selection,
    )
    return GroupChatManager(groupchat=group_chat, llm_config=llm_config())


def extract_history(chat_result: object, manager: GroupChatManager) -> List[Dict[str, str]]:
    if chat_result and hasattr(chat_result, "chat_history"):
        return list(chat_result.chat_history)
    return list(manager.groupchat.messages)


def find_last_message(history: List[Dict[str, str]], name: str) -> str:
    for message in reversed(history):
        if message.get("name") == name:
            return str(message.get("content", "")).strip()
    return ""


def find_last_non_user_message(history: List[Dict[str, str]]) -> str:
    for message in reversed(history):
        if message.get("name") != "User":
            return str(message.get("content", "")).strip()
    return ""


def answer_question(
    architecture: str,
    question: str,
    vector_db: VectorDatabase,
    memory: ArchitectureMemory,
) -> Tuple[str, str]:
    if architecture == SEQUENTIAL:
        return answer_with_sequential_architecture(question, vector_db, memory)
    if architecture == PEER:
        return answer_with_peer_architecture(question, vector_db, memory)
    raise ValueError(f"未知架构: {architecture}")
