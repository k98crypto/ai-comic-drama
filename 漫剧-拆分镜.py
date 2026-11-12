#!/usr/bin/env python3
"""漫剧自动拆分镜（导演步骤的机械部分）

用法：
    python3 漫剧-拆分镜.py [epub路径] [html文件] [书名关键词]

只做不花钱、不调模型的部分：
- 从 epub 里按《书名》镜头标题切分章节（查理九世本身就是按镜头写的）
- 去重重复标题行，统计每镜头正文字数
- 按第一章已验证的口径估算镜数：楔子+镜头一共 2081 字 = 9 镜（每镜 5 秒），
  约 231 字/镜；单镜生成约 2-3 分钟（T4，含首帧），取 2.5 分钟估算 GPU 时间
- 输出每镜头一句话剧情（取正文前两句非对话行）和全书合计

不做的事：不写英文提示词、不调 LLM、不生成视频。
提示词仍按 ~/workspace/your_files/查理九世-吸血古堡-第一章-分镜表.md 的格式，
由 Muse/大模型按人物小传逐镜写；Kaggle 恢复后按分镜表跑 Wan 2.1。
仅供用户本人观看，不上传。
"""
import sys
import zipfile
import re

EPUB = sys.argv[1] if len(sys.argv) > 1 else (
    "/home/hatch/workspace/user/files/6E533749-1CF7-4EC5-A90C-E77662956866-"
    "查理九世 (雷欧幻像) (z-library.sk, 1lib.sk, z-lib.sk).epub")
HTML = sys.argv[2] if len(sys.argv) > 2 else "OEBPS/text00011.html"
BOOK = sys.argv[3] if len(sys.argv) > 3 else "吸血古堡"

CHARS_PER_SHOT = 231   # 第一章实测：2081 字 -> 9 镜
MIN_PER_SHOT = 2.5     # 分钟/镜（T4，含首帧图生成）


def load_lines(epub, html):
    z = zipfile.ZipFile(epub)
    h = z.read(html).decode("utf-8", "ignore")
    h = re.sub(r"<[^>]+>", "\n", h)
    return [l.strip() for l in h.split("\n") if l.strip()]


def split_book(lines, book):
    """切出指定书的楔子+镜头，返回 [(标题, 正文行列表)]。"""
    heads = []
    for i, l in enumerate(lines):
        if l.startswith("楔子") or l.startswith(f"《{book}》镜头"):
            heads.append((i, l))
    # 去重：连续重复的同一标题只留第一次
    dedup = []
    for i, l in heads:
        if dedup and dedup[-1][1] == l and i == dedup[-1][0] + 1:
            continue
        dedup.append((i, l))
    sections = []
    for k, (i, l) in enumerate(dedup):
        end = dedup[k + 1][0] if k + 1 < len(dedup) else len(lines)
        # 下一本书开始处截断：标题不属于本书的镜头不算进来
        body = []
        for j in range(i + 1, end):
            # 下一本书的标题行（任何《X》开头的标题，且不是本书）即截断
            if lines[j].startswith("《") and f"《{book}》" not in lines[j]:
                break
            # 跳过正文里重复出现的本节标题行
            if lines[j] == l:
                continue
            body.append(lines[j])
        sections.append((l, body))
    return sections


def first_beat(body):
    for l in body:
        if l.startswith("《") or l.startswith("楔子"):
            continue
        if len(l) >= 12 and not l.startswith("“"):
            return l[:60]
    for l in body:
        if not l.startswith("《"):
            return l[:60]
    return body[0][:60] if body else ""


def main():
    lines = load_lines(EPUB, HTML)
    sections = split_book(lines, BOOK)
    total_chars = 0
    total_shots = 0
    print(f"# 《{BOOK}》全书镜头清单（仅供本人观看，不上传）\n")
    print("| 镜头 | 字数 | 估算镜数 | 时长 | GPU 约需 | 剧情一句话 |")
    print("|---|---|---|---|---|---|")
    for title, body in sections:
        chars = len("".join(body))
        shots = max(1, round(chars / CHARS_PER_SHOT))
        total_chars += chars
        total_shots += shots
        print(f"| {title} | {chars} | {shots} | {shots * 5} 秒 | "
              f"{shots * MIN_PER_SHOT:.0f} 分钟 | {first_beat(body)} |")
    print(f"\n合计：{len(sections)} 节（楔子+{len(sections) - 1} 个镜头），"
          f"{total_chars} 字，约 {total_shots} 镜，"
          f"成片约 {total_shots * 5 // 60} 分 {total_shots * 5 % 60} 秒，"
          f"GPU 约 {total_shots * MIN_PER_SHOT / 60:.1f} 小时。")
    print(f"Kaggle 每周 30 小时额度：整本约占 "
          f"{total_shots * MIN_PER_SHOT / 60 / 30 * 100:.0f}%。")


if __name__ == "__main__":
    main()
