#!/usr/bin/env python3
"""
向量数据库管理类
"""

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pickle
import os

class VectorDatabase:
    """向量数据库管理"""
    
    def __init__(self, db_path="vector_db", model_name="all-MiniLM-L6-v2", model_path=None):
        """初始化向量数据库"""
        self.db_path = db_path
        
        # 从本地加载模型或从Hugging Face下载
        if model_path and os.path.exists(model_path):
            print(f"从本地加载模型: {model_path}")
            self.model = SentenceTransformer(model_path)
        else:
            print(f"从Hugging Face加载模型: {model_name}")
            # 配置国内镜像源
            os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
            # 增加超时时间
            os.environ['TRANSFORMERS_DOWNLOAD_TIMEOUT'] = '300'
            self.model = SentenceTransformer(model_name)
        
        self.index = None
        self.id_to_text = {}
        self.next_id = 0
        
        # 创建存储目录
        os.makedirs(self.db_path, exist_ok=True)
        
        # 加载现有数据库
        self.load()
    
    def load(self):
        """加载向量数据库"""
        index_path = os.path.join(self.db_path, "index.faiss")
        id_map_path = os.path.join(self.db_path, "id_to_text.pkl")
        
        if os.path.exists(index_path) and os.path.exists(id_map_path):
            try:
                self.index = faiss.read_index(index_path)
                with open(id_map_path, "rb") as f:
                    data = pickle.load(f)
                    self.id_to_text = data["id_to_text"]
                    self.next_id = data["next_id"]
                print(f"加载向量数据库成功，包含 {len(self.id_to_text)} 条记录")
            except Exception as e:
                print(f"加载向量数据库失败: {e}")
                self.initialize_index()
        else:
            self.initialize_index()
    
    def initialize_index(self):
        """初始化向量索引"""
        # 获取模型嵌入维度
        sample_embedding = self.model.encode(["sample"])[0]
        dimension = len(sample_embedding)
        
        # 创建FAISS索引
        self.index = faiss.IndexFlatL2(dimension)
        self.id_to_text = {}
        self.next_id = 0
        print(f"初始化向量数据库，维度: {dimension}")
    
    def save(self):
        """保存向量数据库"""
        index_path = os.path.join(self.db_path, "index.faiss")
        id_map_path = os.path.join(self.db_path, "id_to_text.pkl")
        
        try:
            faiss.write_index(self.index, index_path)
            with open(id_map_path, "wb") as f:
                pickle.dump({
                    "id_to_text": self.id_to_text,
                    "next_id": self.next_id
                }, f)
            print(f"保存向量数据库成功，包含 {len(self.id_to_text)} 条记录")
        except Exception as e:
            print(f"保存向量数据库失败: {e}")
    
    def add_text(self, text):
        """添加文本到向量数据库"""
        # 生成嵌入向量
        embedding = self.model.encode([text])[0]
        
        # 添加到索引
        self.index.add(np.array([embedding]))
        
        # 保存文本与ID的映射
        self.id_to_text[self.next_id] = text
        self.next_id += 1
        
        # 自动保存
        if self.next_id % 10 == 0:
            self.save()
        
        return self.next_id - 1
    
    def search(self, query, top_k=5):
        """搜索相关文本"""
        # 生成查询向量
        query_embedding = self.model.encode([query])[0]
        
        # 搜索相似向量
        distances, indices = self.index.search(np.array([query_embedding]), top_k)
        
        # 整理结果
        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:  # FAISS用-1表示无结果
                results.append({
                    "text": self.id_to_text.get(idx, ""),
                    "distance": distances[0][i]
                })
        
        return results
    
    def add_knowledge_base(self, knowledge_base):
        """添加知识库到向量数据库"""
        for artifact_name, artifact_info in knowledge_base.items():
            # 构建文本表示
            text = f"{artifact_name}: {artifact_info.get('描述', '')} 年代: {artifact_info.get('年代', '')} 出土地点: {artifact_info.get('出土地点', '')}"
            self.add_text(text)
        self.save()
    
    def clear(self):
        """清空向量数据库"""
        self.initialize_index()
        self.save()