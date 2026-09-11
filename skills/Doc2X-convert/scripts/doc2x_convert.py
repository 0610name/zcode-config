#!/usr/bin/env python3
"""Convert PDF or image files to editable formats via the Doc2X API.

PDF:  preupload -> PUT file -> poll parse/status -> convert/parse
      -> poll convert/parse/result -> download + unzip.
Image (jpg/png <= 7M): sync POST parse/img/layout -> markdown (+ optional
base64 zip of image assets).

API docs: https://doc2x.noedgeai.com/help/zh-cn/
"""

import argparse
import base64
import io
import json
import os
import sys
import time
import zipfile

import requests

BASE_URL = "https://v2.doc2x.noedgeai.com"
# Shared local credentials file (git-ignored); future skills can reuse it.
CREDENTIALS_FILE = os.path.join(os.path.expanduser("~"), ".zcode", "credentials.json")
PDF_EXTS = {".pdf"}
IMG_EXTS = {".jpg", ".jpeg", ".png"}
POLL_INTERVAL = 2
PARSE_TIMEOUT = 15 * 60  # Doc2X kills parse tasks after 15 min

ERROR_HINTS = {
    "parse_task_limit_exceeded": "任务数超出上限，请稍后再试或清理未完成的任务",
    "parse_concurrency_limit": "解析页数超出并发上限",
    "parse_quota_limit": "Doc2X 额度不足，请到 open.noedgeai.com 查看余额",
    "parse_file_too_large": "文件过大（单文件上限 300M）",
    "parse_page_limit_exceeded": "页数过多（单文件上限 2000 页）",
    "parse_file_not_pdf": "文件不是有效的 PDF",
    "parse_timeout": "解析超时（超过 15 分钟）",
    "parse_file_lock": "文件被锁定（同文件一天内不能重复解析）",
    "parse_error": "解析失败",
}


class Doc2XError(Exception):
    pass


def api_headers(api_key):
    return {"Authorization": f"Bearer {api_key}"}


def check_response(resp):
    """Raise Doc2XError on HTTP or Doc2X business errors."""
    if resp.status_code == 429:
        raise Doc2XError("HTTP 429：请求过于频繁，超出速率限制，请稍后重试")
    if resp.status_code != 200:
        raise Doc2XError(f"HTTP {resp.status_code}：{resp.text[:200]}")
    body = resp.json()
    code = body.get("code")
    if code and code != "success":
        hint = ERROR_HINTS.get(code, body.get("msg", ""))
        raise Doc2XError(f"Doc2X 错误 [{code}]：{hint}")
    return body.get("data") or {}


def convert_pdf(api_key, path, to, model):
    headers = api_headers(api_key)

    # 1. preupload: get task uid + presigned upload url
    body = {"model": model} if model else {}
    data = check_response(
        requests.post(f"{BASE_URL}/api/v2/parse/preupload",
                      headers=headers, json=body, timeout=60))
    uid, upload_url = data["uid"], data["url"]

    # 2. upload the file itself (no auth header on the presigned PUT)
    with open(path, "rb") as f:
        resp = requests.put(upload_url, data=f, timeout=600)
    if resp.status_code != 200:
        raise Doc2XError(f"文件上传失败 HTTP {resp.status_code}：{resp.text[:200]}")

    # 3. poll parse status
    deadline = time.time() + PARSE_TIMEOUT
    while True:
        data = check_response(
            requests.get(f"{BASE_URL}/api/v2/parse/status",
                         headers=headers, params={"uid": uid}, timeout=60))
        status = data.get("status")
        if status == "success":
            break
        if status == "failed":
            raise Doc2XError(f"解析失败：{data.get('detail', '未知错误')}")
        if time.time() > deadline:
            raise Doc2XError("等待解析超时")
        print(f"解析中… {data.get('progress', 0)}%", file=sys.stderr)
        time.sleep(POLL_INTERVAL)

    # 4. request export
    export = {"uid": uid, "to": to}
    if to == "md":
        export["formula_mode"] = "dollar"  # keep $...$ math markers
    check_response(
        requests.post(f"{BASE_URL}/api/v2/convert/parse",
                      headers=headers, json=export, timeout=60))

    # 5. poll export result, then download the zip
    while True:
        data = check_response(
            requests.get(f"{BASE_URL}/api/v2/convert/parse/result",
                         headers=headers, params={"uid": uid}, timeout=60))
        if data.get("status") == "success":
            break
        if data.get("status") == "failed":
            raise Doc2XError("导出失败")
        if time.time() > deadline:
            raise Doc2XError("等待导出超时")
        time.sleep(POLL_INTERVAL)

    zip_url = data["url"].replace("\\u0026", "&")
    return requests.get(zip_url, timeout=600).content


def convert_image(api_key, path):
    with open(path, "rb") as f:
        data = check_response(
            requests.post(f"{BASE_URL}/api/v2/parse/img/layout",
                          headers=api_headers(api_key), data=f, timeout=300))
    pages = sorted(data.get("result", {}).get("pages", []),
                   key=lambda p: p.get("page_idx", 0))
    md = "\n\n".join(p.get("md", "") for p in pages)
    assets = None
    if data.get("convert_zip"):
        assets = base64.b64decode(data["convert_zip"])
    return md.encode("utf-8"), assets, ".md"


def write_result(content, assets, out_dir, stem):
    os.makedirs(out_dir, exist_ok=True)
    if content[:2] == b"PK":  # zip-family payload
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            names = z.namelist()
        if "[Content_Types].xml" in names:
            # docx exports are returned as the .docx itself (a zip of XML parts),
            # so save it whole instead of unpacking it.
            with open(os.path.join(out_dir, stem + ".docx"), "wb") as f:
                f.write(content)
        else:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                z.extractall(out_dir)
    else:
        with open(os.path.join(out_dir, stem + ".md"), "wb") as f:
            f.write(content)
    if assets is not None:
        with zipfile.ZipFile(io.BytesIO(assets)) as z:
            z.extractall(out_dir)
    return out_dir


def load_api_key(name):
    """Read an API key: environment variable first, then credentials.json."""
    key = os.environ.get(name)
    if key:
        return key
    try:
        with open(CREDENTIALS_FILE, encoding="utf-8") as f:
            return (json.load(f) or {}).get(name) or None
    except FileNotFoundError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Convert PDF/images via Doc2X API")
    parser.add_argument("file", help="PDF 或图片文件路径")
    parser.add_argument("--to", choices=["md", "tex", "docx"], default="md",
                        help="导出格式（仅 PDF 有效，图片固定输出 md）")
    parser.add_argument("--out", help="输出目录（默认 <文件名>_doc2x）")
    parser.add_argument("--model", choices=["v2", "v3-2026"], default="v2",
                        help="解析模型（仅 PDF 有效）")
    args = parser.parse_args()

    api_key = load_api_key("DOC2X_API_KEY")
    if not api_key:
        sys.exit(f"错误：未找到 Doc2X API key。\n"
                 f"请编辑 {CREDENTIALS_FILE}，填入获取的 key（格式 sk-xxx）：\n"
                 f'  {{ "DOC2X_API_KEY": "sk-你的key" }}\n'
                 f"获取 key: https://open.noedgeai.com")

    path = args.file
    if not os.path.isfile(path):
        sys.exit(f"错误：文件不存在：{path}")
    ext = os.path.splitext(path)[1].lower()
    stem = os.path.splitext(os.path.basename(path))[0]
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(path)),
                                       stem + "_doc2x")

    try:
        if ext in PDF_EXTS:
            content = convert_pdf(api_key, path, args.to, args.model)
            out = write_result(content, None, out_dir, stem)
        elif ext in IMG_EXTS:
            if os.path.getsize(path) > 7 * 1024 * 1024:
                sys.exit("错误：图片超过 7M 上限，请压缩后再试")
            content, assets, _ = convert_image(api_key, path)
            out = write_result(content, assets, out_dir, stem)
        else:
            sys.exit(f"错误：不支持的文件类型 {ext}（支持 {', '.join(sorted(PDF_EXTS | IMG_EXTS))}）")
    except Doc2XError as e:
        sys.exit(f"错误：{e}")
    except requests.RequestException as e:
        sys.exit(f"错误：网络请求失败：{e}")

    print(f"完成！结果已保存到：{out}")


if __name__ == "__main__":
    main()
