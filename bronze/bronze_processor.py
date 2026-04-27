import json
from pathlib import Path
from typing import Dict, List


class BronzeDataProcessor:
    """Load bronze artifact records and convert them into retrieval texts."""

    def __init__(self, data_file: str = "bronze_items.json") -> None:
        self.data_file = Path(data_file)
        self.data = self.load_data()

    def load_data(self) -> List[Dict[str, object]]:
        if not self.data_file.exists():
            raise FileNotFoundError(f"未找到青铜器数据文件: {self.data_file}")

        with self.data_file.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError(f"{self.data_file} 必须是 JSON 数组")
        return data

    def generate_text_representations(self) -> List[str]:
        texts: List[str] = []
        for item in self.data:
            name = str(item.get("name", "")).strip()
            category = str(item.get("category", "")).strip()
            summary = str(item.get("summary", "")).strip()
            detail = str(item.get("detail", "")).strip()
            if not name:
                continue

            text = (
                f"青铜器: {name}\n"
                f"分类: {category}\n"
                f"简介: {summary}\n"
                f"详细介绍: {detail}"
            )
            texts.append(text)
        return texts

    def count(self) -> int:
        return len(self.data)
