#!/usr/bin/env python3
"""
下载预训练模型
"""

from huggingface_hub import snapshot_download

def download_model():
    """下载模型到本地"""
    print("开始下载模型...")
    
    # 下载模型
    snapshot_download(
        repo_id="sentence-transformers/all-MiniLM-L6-v2",
        local_dir="./models/all-MiniLM-L6-v2",
        endpoint="https://hf-mirror.com"
    )
    
    print("模型下载完成！")

if __name__ == "__main__":
    download_model()
