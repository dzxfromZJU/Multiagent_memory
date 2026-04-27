#!/usr/bin/env python3
"""
电影多智能体问答系统
"""

import os
import sys
import json
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager

# 添加父目录到Python路径
sys.path.append('..')
from vector_db import VectorDatabase
from film.film_processor import FilmDataProcessor

# 配置DeepSeek API密钥
os.environ['DEEPSEEK_API_KEY'] = 'sk-ddccf24607e14709a73739f0dfcb9a4d'

class CollectiveMemory:
    """共享记忆库管理"""
    
    def __init__(self, memory_file="collective_memory.json", vector_db=None):
        """初始化共享记忆库"""
        self.memory_file = memory_file
        self.vector_db = vector_db
        self.memory = self.load_memory()
    
    def load_memory(self):
        """加载共享记忆"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {"conversations": [], "knowledge": {}}
        except Exception as e:
            print(f"加载共享记忆失败: {e}")
            return {"conversations": [], "knowledge": {}}
    
    def save_memory(self):
        """保存共享记忆"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存共享记忆失败: {e}")
            return False
    
    def add_conversation(self, user_question, agent_response):
        """添加对话到共享记忆"""
        conversation = {
            "timestamp": os.path.getmtime(self.memory_file) if os.path.exists(self.memory_file) else None,
            "user_question": user_question,
            "agent_response": agent_response
        }
        self.memory["conversations"].append(conversation)
        self.save_memory()
        
        # 同时添加到向量数据库
        if self.vector_db:
            conversation_text = f"用户: {user_question} 系统: {agent_response}"
            self.vector_db.add_text(conversation_text)
    
    def add_knowledge(self, key, value):
        """添加知识到共享记忆"""
        self.memory["knowledge"][key] = value
        self.save_memory()
        
        # 同时添加到向量数据库
        if self.vector_db:
            knowledge_text = f"知识: {key} - {value}"
            self.vector_db.add_text(knowledge_text)
    
    def get_relevant_memory(self, query):
        """获取与查询相关的记忆"""
        if self.vector_db:
            # 使用向量数据库搜索
            results = self.vector_db.search(query, top_k=3)
            return results
        else:
            # 传统文本匹配
            relevant = []
            for conv in self.memory["conversations"]:
                if query in conv["user_question"] or query in conv["agent_response"]:
                    relevant.append(conv)
            return relevant

def create_agents(vector_db, collective_memory):
    """创建智能体"""
    
    # 配置智能体
    config_list = [
        {
            "model": "deepseek-chat",
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "base_url": "https://api.deepseek.com/v1"
        }
    ]
    
    # 创建用户代理（提问者）
    user_proxy = UserProxyAgent(
        name="User",
        system_message="你是一个电影爱好者，对电影、导演和演员有很多问题。请直接输入你的问题。",
        human_input_mode="TERMINATE",
        code_execution_config=False,
    )
    
    # 创建问题识别智能体
    question_analyzer = AssistantAgent(
        name="QuestionAnalyzer",
        system_message="""你是一个问题识别专家，负责分析用户的问题，确定问题类型（关于电影、导演还是演员），并提取关键信息。

请遵循以下规则：
1. 分析用户问题后，直接说"问题分析完成，请思索智能体回答"
2. 不要与思索智能体进行额外对话
3. 一轮分析后立即停止""",
        llm_config={"config_list": config_list},
        max_consecutive_auto_reply=1,
    )
    
    # 创建思索智能体
    thinker = AssistantAgent(
        name="Thinker",
        system_message="""你是一个思索专家，负责基于向量数据库中的信息，深入思考用户问题，生成详细的回答思路。

请遵循以下规则：
1. 基于向量数据库中的电影知识生成回答
2. 回答完成后，说"回答完成，请校对智能体检查"
3. 一轮回答后立即停止""",
        llm_config={"config_list": config_list},
        max_consecutive_auto_reply=1,
    )
    
    # 创建校对智能体
    validator = AssistantAgent(
        name="Validator",
        system_message="""你是一个校对专家，负责验证思索智能体的回答是否准确，是否基于向量数据库中的信息，避免幻觉。

请遵循以下规则：
1. 只进行一轮校对
2. 如果回答正确，说"校对通过，回答正确"
3. 如果发现问题，说"校对未通过，回答有误：[具体问题]"
4. 一轮校对后立即停止""",
        llm_config={"config_list": config_list},
        max_consecutive_auto_reply=1,
    )
    
    return user_proxy, question_analyzer, thinker, validator

def setup_group_chat(agents):
    """设置群聊"""

    # 简单的智能体选择逻辑，确保流程：用户 -> 分析 -> 思索 -> 校对 -> 用户
    def simple_speaker_selection(last_speaker, groupchat):
        messages = groupchat.messages

        # 统计各智能体的发言次数
        analyzer_count = sum(1 for msg in messages if msg.get("name") == "QuestionAnalyzer")
        thinker_count = sum(1 for msg in messages if msg.get("name") == "Thinker")
        validator_count = sum(1 for msg in messages if msg.get("name") == "Validator")

        # 如果上一个发言者是用户，且还没有分析，转到问题识别智能体
        if last_speaker.name == "User" and analyzer_count == 0:
            analyzer = next((agent for agent in agents if agent.name == "QuestionAnalyzer"), None)
            if analyzer:
                return analyzer

        # 如果问题识别智能体已经发言，且还没有思索，转到思索智能体
        elif last_speaker.name == "QuestionAnalyzer" and thinker_count == 0:
            thinker = next((agent for agent in agents if agent.name == "Thinker"), None)
            if thinker:
                return thinker

        # 如果思索智能体已经发言，且还没有校对，转到校对智能体
        elif last_speaker.name == "Thinker" and validator_count == 0:
            validator = next((agent for agent in agents if agent.name == "Validator"), None)
            if validator:
                return validator


    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=4,  # 严格限制总轮数：用户 -> 分析 -> 思索 -> 校对
        speaker_selection_method=simple_speaker_selection,
    )

    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config={
            "config_list": [
                {
                    "model": "deepseek-chat",
                    "api_key": os.getenv("DEEPSEEK_API_KEY"),
                    "base_url": "https://api.deepseek.com/v1"
                }
            ]
        },
    )

    return manager

def initialize_vector_db():
    """初始化向量数据库"""
    vector_db = VectorDatabase(
        db_path="vector_db_film",
        model_path="./models/all-MiniLM-L6-v2"
    )

    # 检查是否需要初始化电影数据
    if should_initialize_film_data(vector_db):
        print("检测到需要初始化电影数据...")
        processor = FilmDataProcessor()
        texts = processor.generate_text_representations()

        # 添加到向量数据库
        film_count = 0
        for text in texts:
            # 检查是否已经存在（避免重复）
            if not text_exists_in_vector_db(vector_db, text):
                vector_db.add_text(text)
                film_count += 1

        if film_count > 0:
            vector_db.save()
            print(f"电影数据初始化完成，新增了 {film_count} 条记录")
        else:
            print("电影数据已存在，无需新增")
    else:
        print("向量数据库已包含电影数据，跳过初始化")

    return vector_db


def should_initialize_film_data(vector_db):
    """检查是否需要初始化电影数据"""
    # 如果向量数据库为空，需要初始化
    if len(vector_db.id_to_text) == 0:
        return True

    # 检查是否包含电影相关数据
    film_related_queries = ["电影", "导演", "演员", "启动原始码", "杰克·葛伦霍"]
    film_found = False

    for query in film_related_queries:
        results = vector_db.search(query, top_k=2)
        for result in results:
            if any(keyword in result["text"] for keyword in ["电影", "导演", "演员"]):
                film_found = True
                break
        if film_found:
            break

    return not film_found


def text_exists_in_vector_db(vector_db, text):
    """检查文本是否已经存在于向量数据库中"""
    # 简单的文本匹配检查
    for existing_text in vector_db.id_to_text.values():
        if text == existing_text:
            return True
    return False

def main():
    """主函数"""
    # 初始化向量数据库
    vector_db = initialize_vector_db()
    
    # 初始化共享记忆库
    collective_memory = CollectiveMemory(vector_db=vector_db)
    
    # 创建智能体
    agents = create_agents(vector_db, collective_memory)
    
    # 设置群聊
    manager = setup_group_chat(agents)
    
    # 启动对话
    print("=== 电影多智能体问答系统 ===")
    print("你可以询问关于电影、导演和演员的问题，系统会通过多智能体协作回答你。")
    print("例如：'《启动原始码》的导演是谁？'、'杰克·葛伦霍演过哪些电影？'")
    
    # 开始对话循环
    while True:
        user_question = input("\n请输入你的问题（输入'退出'结束对话）：")
        if user_question == "退出":
            break
        
        print("\n=== 智能体协作处理中 ===")
        
        # 临时修改用户代理的模式，避免对话结束后的额外提示
        original_mode = agents[0].human_input_mode
        agents[0].human_input_mode = "NEVER"
        
        try:
            # 启动对话
            chat_result = agents[0].initiate_chat(
                manager,
                message=user_question,
            )
            
            # 检查校对结果并决定是否保存到共享记忆
            if chat_result and hasattr(chat_result, 'chat_history'):
                # 提取最终回答和校对结果
                final_response = ""
                validation_result = ""

                # 使用chat_history属性（新版本AutoGen）
                chat_history = chat_result.chat_history

                for msg in reversed(chat_history):
                    if msg.get("name") == "Thinker":
                        final_response = msg.get("content", "")
                    elif msg.get("name") == "Validator":
                        validation_result = msg.get("content", "")
                        break

                print(f"\n=== 最终回答 ===")
                print(final_response)
                print(f"\n=== 校对结果 ===")
                print(validation_result)

                # 根据校对结果决定是否保存到共享记忆
                if "校对通过" in validation_result or "回答正确" in validation_result:
                    # 校对通过，保存到共享记忆
                    collective_memory.add_conversation(user_question, final_response)
                    print("=== 对话已保存到共享记忆 ===")
                elif "校对未通过" in validation_result or "回答有误" in validation_result:
                    # 校对未通过，不保存到共享记忆
                    print("=== 校对未通过，对话未保存到共享记忆 ===")
                else:
                    # 默认情况下也保存，但标记为未校对
                    collective_memory.add_conversation(user_question, final_response)
                    print("=== 对话已保存到共享记忆（未明确校对） ===")
            else:
                print("=== 对话处理完成，但无法提取对话历史 ===")
        
        finally:
            # 恢复原来的模式
            agents[0].human_input_mode = original_mode
        
        print("\n=== 等待您的新问题 ===")

if __name__ == "__main__":
    main()