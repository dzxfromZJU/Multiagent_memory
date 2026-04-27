#!/usr/bin/env python3
"""
电影数据处理工具
"""

import json
import os

class FilmDataProcessor:
    """电影数据处理器"""
    
    def __init__(self, data_file="film/kb_film.json"):
        """初始化数据处理器"""
        self.data_file = data_file
        self.data = self.load_data()
    
    def load_data(self):
        """加载数据"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载数据失败: {e}")
            return {}
    
    def extract_film_info(self):
        """提取电影信息"""
        films = []
        
        for key, entries in self.data.items():
            # 检查是否是电影条目
            is_film = False
            film_info = {"名称": key, "类型": "电影"}
            
            for entry in entries:
                if len(entry) >= 3:
                    property_name = entry[1]
                    property_value = entry[2]
                    
                    # 检查是否包含电影相关属性
                    if property_name in ["导演", "主演", "编剧", "出品时间", "类型", "Information"]:
                        is_film = True
                        film_info[property_name] = property_value
            
            if is_film:
                films.append(film_info)
        
        return films
    
    def extract_person_info(self):
        """提取人物信息（导演、演员等）"""
        persons = []
        
        for key, entries in self.data.items():
            # 检查是否是人物条目
            is_person = False
            person_info = {"名称": key, "类型": "人物"}
            
            for entry in entries:
                if len(entry) >= 3:
                    property_name = entry[1]
                    property_value = entry[2]
                    
                    # 检查是否包含人物相关属性
                    if property_name in ["Occupation", "Birth place", "Information"]:
                        is_person = True
                        person_info[property_name] = property_value
            
            if is_person:
                persons.append(person_info)
        
        return persons
    
    def generate_text_representations(self):
        """生成文本表示，用于向量数据库"""
        texts = []
        
        # 处理电影
        films = self.extract_film_info()
        for film in films:
            text = f"电影: {film.get('名称', '')}"
            if '导演' in film:
                text += f" 导演: {film['导演']}"
            if '主演' in film:
                text += f" 主演: {film['主演']}"
            if '类型' in film:
                text += f" 类型: {film['类型']}"
            if 'Information' in film:
                text += f" 简介: {film['Information']}"
            texts.append(text)
        
        # 处理人物
        persons = self.extract_person_info()
        for person in persons:
            text = f"人物: {person.get('名称', '')}"
            if 'Occupation' in person:
                text += f" 职业: {person['Occupation']}"
            if 'Birth place' in person:
                text += f" 出生地: {person['Birth place']}"
            if 'Information' in person:
                text += f" 简介: {person['Information']}"
            texts.append(text)
        
        return texts
    
    def save_processed_data(self, output_file="processed_film_data.json"):
        """保存处理后的数据"""
        processed_data = {
            "films": self.extract_film_info(),
            "persons": self.extract_person_info()
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, ensure_ascii=False, indent=2)
            print(f"处理后的数据已保存到 {output_file}")
        except Exception as e:
            print(f"保存数据失败: {e}")

if __name__ == "__main__":
    processor = FilmDataProcessor()
    
    # 提取电影和人物信息
    films = processor.extract_film_info()
    persons = processor.extract_person_info()
    
    print(f"提取到 {len(films)} 部电影")
    print(f"提取到 {len(persons)} 个人物")
    
    # 生成文本表示
    texts = processor.generate_text_representations()
    print(f"生成了 {len(texts)} 条文本表示")
    
    # 保存处理后的数据
    processor.save_processed_data()
