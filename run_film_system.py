#!/usr/bin/env python3
"""
启动电影多智能体问答系统
"""

import os
import sys

def check_data_file():
    data_file = "film/kb_film.json"
    if os.path.exists(data_file):
        print("✓ 数据文件存在")
        return True
    else:
        print(f"✗ 数据文件不存在: {data_file}")
        return False

def main():
    """主函数"""
    print("=== 检查系统环境 ===")

    print("\n=== 启动电影多智能体问答系统 ===")

    # 运行系统
    try:
        import film.film_qa_system
        film.film_qa_system.main()
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
