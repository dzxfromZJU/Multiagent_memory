#!/usr/bin/env python3
"""
多智能体对话系统，用于测试记忆幻觉和知识编辑
"""

import os
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager
from autogen.agentchat.contrib.retrieve_assistant_agent import RetrieveAssistantAgent
from autogen.agentchat.contrib.retrieve_user_proxy_agent import RetrieveUserProxyAgent
import json

# 配置环境变量（如果需要）
os.environ['DEEPSEEK_API_KEY'] = 'sk-ddccf24607e14709a73739f0dfcb9a4d'

class MuseumKnowledgeBase:
    """博物馆知识库管理"""
    
    def __init__(self):
        # 初始化简单的博物馆文物知识库
        self.knowledge_base = {
            "文物1": {
                "名称": "青铜器爵",
                "年代": "商代晚期",
                "描述": "青铜爵是商代晚期的酒器，高20厘米，腹深12厘米，重1.5公斤。器身饰有饕餮纹，造型精美。",
                "出土地点": "河南安阳殷墟"
            },
            "文物2": {
                "名称": "青花瓷瓶",
                "年代": "明代宣德年间",
                "描述": "青花瓷瓶高35厘米，口径10厘米，底径12厘米。瓶身绘有缠枝莲纹，青花发色浓艳。",
                "出土地点": "景德镇窑"
            },
            "文物3": {
                "名称": "金缕玉衣",
                "年代": "西汉",
                "描述": "金缕玉衣由2000多片玉片用金丝编织而成，是汉代贵族的殓服。",
                "出土地点": "河北满城汉墓"
            }
        }
    
    def get_artifact_info(self, artifact_name):
        """获取文物信息"""
        return self.knowledge_base.get(artifact_name, None)
    
    def update_artifact_info(self, artifact_name, new_info):
        """更新文物信息（知识编辑）"""
        if artifact_name in self.knowledge_base:
            self.knowledge_base[artifact_name].update(new_info)
            return True
        return False
    
    def add_artifact(self, artifact_id, artifact_info):
        """添加新文物"""
        self.knowledge_base[artifact_id] = artifact_info
        return True
    
    def list_artifacts(self):
        """列出所有文物"""
        return list(self.knowledge_base.keys())

def create_agents():
    """创建智能体"""
    
    # 配置智能体
    config_list = [
        {
            "model": "deepseek-chat",
            "api_key": os.getenv("DEEPSEEK_API_KEY", "sk-ddccf24607e14709a73739f0dfcb9a4d"),
            "base_url": "https://api.deepseek.com/v1"  # DeepSeek的API端点
        }
    ]
    
    # 创建用户代理
    user_proxy = UserProxyAgent(
        name="User",
        system_message="你是一个博物馆参观者，对博物馆的文物很感兴趣。",
        human_input_mode="ALWAYS",
        code_execution_config=False,
    )
    
    # 创建博物馆讲解员智能体
    museum_guide = AssistantAgent(
        name="MuseumGuide",
        system_message="你是一名专业的博物馆讲解员，熟悉馆内的文物。请基于知识库中的信息回答问题，不要编造信息。",
        llm_config={"config_list": config_list},
    )
    
    # 创建知识管理员智能体
    knowledge_manager = AssistantAgent(
        name="KnowledgeManager",
        system_message="你是博物馆的知识管理员，负责管理和更新文物知识库。当发现信息错误或需要更新时，你可以修改知识库中的信息。",
        llm_config={"config_list": config_list},
    )
    
    return user_proxy, museum_guide, knowledge_manager

def setup_group_chat(user_proxy, museum_guide, knowledge_manager):
    """设置群聊"""
    agents = [user_proxy, museum_guide, knowledge_manager]
    
    group_chat = GroupChat(
        agents=agents,
        messages=[],
        max_round=50,
        speaker_selection_method="round_robin",
    )
    
    manager = GroupChatManager(
        groupchat=group_chat,
        llm_config={
            "config_list": [
                {
                    "model": "gpt-3.5-turbo",
                    "api_key": os.getenv("OPENAI_API_KEY", "your-api-key"),
                }
            ]
        },
    )
    
    return manager

def test_memory_illusion(manager, knowledge_base):
    """测试记忆幻觉"""
    print("\n=== 测试记忆幻觉 ===")
    print("1. 询问已知文物信息")
    print("2. 询问不存在的文物信息")
    print("3. 测试知识编辑功能")
    print("\n请输入测试序号：")

def main():
    """主函数"""
    # 初始化知识库
    knowledge_base = MuseumKnowledgeBase()
    
    # 创建智能体
    user_proxy, museum_guide, knowledge_manager = create_agents()
    
    # 设置群聊
    manager = setup_group_chat(user_proxy, museum_guide, knowledge_manager)
    
    # 测试记忆幻觉
    test_memory_illusion(manager, knowledge_base)
    
    # 启动对话
    user_proxy.initiate_chat(
        manager,
        message="你好，我想了解博物馆里的文物。",
    )

if __name__ == "__main__":
    main()
