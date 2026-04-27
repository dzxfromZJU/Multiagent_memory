import argparse
import hashlib
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.zgbk.com"
START_URL = f"{BASE_URL}/ecph/sublibrary?SiteID=1&ID=606"
TARGET_SUBLIB_ID = 612
DEFAULT_OUTPUT = "bronze_items.json"


class ZgbkCollector:
    def __init__(
        self,
        delay: float = 0.5,
        timeout: int = 20,
        retries: int = 3,
        pagesize: int = 6,
    ) -> None:
        self.delay = delay
        self.timeout = timeout
        self.retries = retries
        self.pagesize = pagesize
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
                "Referer": START_URL,
            }
        )
        self.seed_token = self._load_seed_token()

    def _load_seed_token(self) -> str:
        html = self._request("GET", START_URL, with_api_token=False).text
        match = re.search(r'var\s+token\s*=\s*"([^"]+)"', html)
        if not match:
            raise RuntimeError("未能从入口页面提取 token")
        return match.group(1)

    def _api_token(self, api_path: str) -> str:
        # The site's mtoken.js sends md5(page_token + api_path_without_query).
        return hashlib.md5((self.seed_token + api_path).encode("utf-8")).hexdigest()

    def _request(
        self,
        method: str,
        url: str,
        *,
        api_path: Optional[str] = None,
        with_api_token: bool = True,
        **kwargs: Any,
    ) -> requests.Response:
        headers = kwargs.pop("headers", {})
        if with_api_token and api_path:
            headers = {
                **headers,
                "Accept": "aplication/json",
                "token": self._api_token(api_path),
            }

        last_error: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    **kwargs,
                )
                if response.status_code == 401 and api_path:
                    self.seed_token = self._load_seed_token()
                    headers["token"] = self._api_token(api_path)
                    response = self.session.request(
                        method,
                        url,
                        headers=headers,
                        timeout=self.timeout,
                        **kwargs,
                    )
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(2 * attempt, 6))

        raise RuntimeError(f"请求失败: {url}") from last_error

    def get_json(self, api_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = urljoin(f"{BASE_URL}/ecph/", api_path.lstrip("/"))
        response = self._request("GET", url, api_path=api_path, params=params)
        return response.json()

    def find_target_sublib(self) -> Dict[str, Any]:
        data = self.get_json("/api/sublib", {"ID": 606, "pagesize": 100})
        sublibs = data.get("data", {}).get("datalist") or []
        for item in sublibs:
            if item.get("ID") == TARGET_SUBLIB_ID or item.get("Name") == "重要青铜器":
                return item
        raise RuntimeError("未找到“重要青铜器”栏目")

    def iter_list_items(self, sublib: Dict[str, Any], max_pages: Optional[int] = None) -> Iterable[Dict[str, Any]]:
        first = self._fetch_list_page(sublib, 0)
        total = first.get("data", {}).get("total", 0)
        page_count = math.ceil(total / self.pagesize)
        if max_pages is not None:
            page_count = min(page_count, max_pages)

        yield from first.get("data", {}).get("datalist") or []

        for page_index in range(1, page_count):
            time.sleep(self.delay)
            data = self._fetch_list_page(sublib, page_index)
            yield from data.get("data", {}).get("datalist") or []

    def _fetch_list_page(self, sublib: Dict[str, Any], page_index: int) -> Dict[str, Any]:
        return self.get_json(
            "/api/wiki",
            {
                "id": sublib["InnerCode"],
                "pageindex": page_index,
                "pagesize": self.pagesize,
                "siteId": sublib["SiteID"],
                "alias": sublib["Alias"],
            },
        )

    def get_detail_text(self, item_id: int, site_id: int) -> str:
        api_path = f"/api/words/{item_id}"
        data = self.get_json(
            api_path,
            {
                "Type": "Extend",
                "SiteID": site_id,
                "Preview": "false",
                "BrowserFinger": "123456789",
            },
        )
        contentinfo = data.get("data", {}).get("contentinfo") or []
        parts: List[str] = []
        for block in contentinfo:
            section_name = clean_text(block.get("Name", ""))
            content = html_to_text(block.get("Content", ""))
            if section_name and content:
                parts.append(f"{section_name}\n{content}")
            elif section_name:
                parts.append(section_name)
            elif content:
                parts.append(content)
        return "\n\n".join(parts)

    def collect(
        self,
        output_path: Path,
        *,
        limit: Optional[int] = None,
        max_pages: Optional[int] = None,
        resume: bool = True,
    ) -> List[Dict[str, Any]]:
        records = load_existing_records(output_path) if resume else []
        seen_ids = {record.get("id") for record in records}

        sublib = self.find_target_sublib()
        safe_print(f"开始爬取栏目: {sublib['Name']} ({sublib['ID']})")

        for raw_item in self.iter_list_items(sublib, max_pages=max_pages):
            item_id = raw_item.get("ID")
            if item_id in seen_ids:
                continue
            if limit is not None and len(records) >= limit:
                break

            detail_text = self.get_detail_text(item_id, raw_item.get("SiteID", 1))
            record = {
                "id": item_id,
                "name": clean_text(raw_item.get("Name", "")),
                "summary": html_to_text(raw_item.get("SubcDescriptionText", "")),
                "detail": detail_text,
                "category": clean_text(raw_item.get("SubLibraryName", "")),
            }
            records.append(record)
            seen_ids.add(item_id)
            atomic_write_json(output_path, records)
            safe_print(f"[{len(records)}] {record['name']}")
            time.sleep(self.delay)

        atomic_write_json(output_path, records)
        return records


def html_to_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select(".word_img_font_p, img, video, audio"):
        tag.decompose()
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    return clean_text(text)


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    text = text.replace("\xa0", " ")
    return text


def load_existing_records(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    if path.stat().st_size == 0:
        return []
    with path.open("r", encoding="utf-8") as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            backup_path = path.with_suffix(path.suffix + f".broken-{int(time.time())}")
            path.replace(backup_path)
            safe_print(f"已有 JSON 文件无法解析，已备份为 {backup_path}，将重新开始。")
            return []
    if not isinstance(data, list):
        raise ValueError(f"{path} 中不是 JSON 数组")
    return data


def atomic_write_json(path: Path, data: List[Dict[str, Any]]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    temp_path.replace(path)


def safe_print(message: str) -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        print(message.encode(encoding, errors="replace").decode(encoding))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="爬取中国大百科全书“重要青铜器”条目")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help="输出 JSON 文件路径")
    parser.add_argument("--delay", type=float, default=0.5, help="每次请求后的等待秒数")
    parser.add_argument("--pagesize", type=int, default=6, help="列表接口每页数量，默认与网页一致")
    parser.add_argument("--limit", type=int, default=None, help="最多保存多少条，用于测试")
    parser.add_argument("--max-pages", type=int, default=None, help="最多抓取多少个列表页，用于测试")
    parser.add_argument("--no-resume", action="store_true", help="不读取已有 JSON，重新开始")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    collector = ZgbkCollector(delay=args.delay, pagesize=args.pagesize)
    output_path = Path(args.output)
    records = collector.collect(
        output_path,
        limit=args.limit,
        max_pages=args.max_pages,
        resume=not args.no_resume,
    )
    safe_print(f"完成，共保存 {len(records)} 条到 {output_path}")


if __name__ == "__main__":
    main()
