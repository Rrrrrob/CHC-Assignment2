# analysis.py
# -*- coding: utf-8 -*-
import re
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import folium

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False    # 用来正常显示负号

# -------------------------------
# I/O config
# -------------------------------
INPUT_TXT = "rulinwaishi.txt"   # Traditional Chinese text from ctext.org
OUT_DIR = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)

# -------------------------------
# Place name variants (traditional + simplified -> normalized simplified)
# -------------------------------
place_variants = {
    "南京": "南京",
    "蘇州": "苏州", "苏州": "苏州",
    "杭州": "杭州",
    "北京": "北京",
    "揚州": "扬州", "扬州": "扬州",
    "濟南": "济南", "济南": "济南",
    "湖州": "湖州",
}

# Coordinates (WGS84) for normalized names
place_coords = {
    "南京": (32.0603, 118.7969),
    "苏州": (31.2989, 120.5853),
    "杭州": (30.2741, 120.1551),
    "北京": (39.9042, 116.4074),
    "扬州": (32.3936, 119.4127),
    "济南": (36.6512, 117.1201),
    "湖州": (30.8943, 120.0868),
}

# -------------------------------
# Characters (traditional forms, extend as needed)
# -------------------------------
characters = [
    "范進", "嚴監生", "匡超人", "杜少卿", "王冕", "莊紹光", "魯編修"
]

# -------------------------------
# Utility functions
# -------------------------------
def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def split_chapters_by_star(raw: str):
    """
    Split text by lines that start with '*' followed by a chapter title.
    Example: '*王孝廉村學識同科　周蒙師暮年登上第'
    Returns list of (chapter_title, chapter_text).
    """
    text = raw.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    # indices of headers
    header_idx = [i for i, ln in enumerate(lines) if ln.strip().startswith("*")]
    chapters = []
    if not header_idx:
        # Fallback: try "第…回"
        pattern = r"(第[一二三四五六七八九十百千零〇兩两\d]+回.*)"
        matches = list(re.finditer(pattern, text))
        if not matches:
            return [("整体文本", text)]
        for mi in range(len(matches)):
            start_title_span = matches[mi].span()
            title = matches[mi].group(1).strip()
            start = start_title_span[1]
            end = matches[mi+1].span()[0] if mi+1 < len(matches) else len(text)
            content = text[start:end].strip()
            chapters.append((title, content))
        return chapters

    for idx, start_line in enumerate(header_idx):
        # strip leading '*' and surrounding whitespace
        raw_title = lines[start_line].strip()
        title = raw_title.lstrip("*").strip()
        content_start = start_line + 1
        content_end = header_idx[idx+1] if idx+1 < len(header_idx) else len(lines)
        content = "\n".join(lines[content_start:content_end]).strip()
        chapters.append((title if title else f"第{idx+1}章", content))
    return chapters

def count_places_in_text(text: str) -> dict:
    """
    Count occurrences of all place variants, normalized to simplified names.
    Literal matching to handle traditional forms (e.g., '濟南').
    """
    counts = {}
    for variant, norm in place_variants.items():
        pattern = re.compile(re.escape(variant))
        match_count = len(pattern.findall(text))
        counts[norm] = counts.get(norm, 0) + match_count
    return counts

def count_characters_in_text(text: str) -> dict:
    counts = {}
    for char in characters:
        pattern = re.compile(re.escape(char))
        counts[char] = len(pattern.findall(text))
    return counts

# -------------------------------
# Main processing
# -------------------------------
def main():
    raw = read_text(INPUT_TXT)
    chapters = split_chapters_by_star(raw)

    if len(chapters) == 1 and chapters[0][0] == "整体文本":
        print("⚠️ 未识别到以 * 开头的章节标题；已回退到“第…回”或整体文本。")

    # Take first 20 chapters
    selected = chapters[:20]
    if not selected:
        print("⚠️ 没有章节可处理。请检查章节标记（以 * 开头）或文本内容。")
        return

    # Per-chapter counting
    rows = []
    for idx, (title, content) in enumerate(selected, start=1):
        place_counts = count_places_in_text(content)
        char_counts = count_characters_in_text(content)
        total_place_mentions = sum(place_counts.values())
        rows.append({
            "chapter_index": idx,
            "chapter_title": title,
            **place_counts,
            "total_place_mentions": total_place_mentions,
            "char_count": len(content),
            "text": content
        })

    df = pd.DataFrame(rows)

    # Save chapter-place frequency (remove text to keep CSV clean)
    freq_cols = [c for c in df.columns if c != "text"]
    df[freq_cols].to_csv(os.path.join(OUT_DIR, "chapter_place_frequency.csv"), index=False, encoding="utf-8-sig")
    print("✅ chapter_place_frequency.csv")

    # Totals per place
    place_names_norm = list(place_coords.keys())
    totals = df[place_names_norm].sum(numeric_only=True)
    totals_df = totals.reset_index()
    totals_df.columns = ["place", "total_mentions"]
    totals_df.to_csv(os.path.join(OUT_DIR, "place_totals.csv"), index=False, encoding="utf-8-sig")
    print("✅ place_totals.csv")

    # Character-place co-occurrence (chapter-level proxy for activities)
    activity_rows = []
    for _, row in df.iterrows():
        text_content = row["text"]
        per_char_counts = count_characters_in_text(text_content)  # compute once per chapter
        for place in place_names_norm:
            pcount = int(row.get(place, 0))
            if pcount <= 0:
                continue
            for char, ccount in per_char_counts.items():
                if ccount <= 0:
                    continue
                activity_rows.append({
                    "chapter_index": int(row["chapter_index"]),
                    "chapter_title": row["chapter_title"],
                    "place": place,
                    "character": char,
                    "place_mentions": pcount,
                    "character_mentions": ccount
                })

    activity_df = pd.DataFrame(activity_rows)
    activity_df.to_csv(os.path.join(OUT_DIR, "character_place_cooccurrence.csv"), index=False, encoding="utf-8-sig")
    print("✅ character_place_cooccurrence.csv")

    # Pivot: character x place (number of chapters with co-occurrence)
    pivot = pd.pivot_table(
        activity_df,
        index="character",
        columns="place",
        values="chapter_index",
        aggfunc="count",
        fill_value=0
    )
    pivot.to_csv(os.path.join(OUT_DIR, "character_place_matrix.csv"), encoding="utf-8-sig")
    print("✅ character_place_matrix.csv")

    # -------------------------------
    # Visualizations (PNG + HTML map)
    # -------------------------------
    sns.set(style="whitegrid", font="SimHei", rc={"axes.unicode_minus": False})

    # 1. 总体柱状图
    plt.figure(figsize=(9, 6))
    sns.barplot(data=totals_df.sort_values("total_mentions", ascending=False), x="place", y="total_mentions",
                color="#c03a2b")
    plt.title("前20章地名总体频率")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "totals_bar.png"), dpi=150)

    # 2. 章节热力图
    heat_df = df[["chapter_title"] + place_names_norm].set_index("chapter_title")
    plt.figure(figsize=(12, 7))
    sns.heatmap(heat_df, cmap="Reds", annot=True, fmt="d")
    plt.title("前20章 章节-地名频率热力图")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "chapter_heatmap.png"), dpi=150)

    # 3. 人物-地名热力图
    plt.figure(figsize=(10, 7))
    sns.heatmap(pivot, cmap="Blues", annot=True, fmt="d")
    plt.title("人物-地名共现热力图")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "character_place_heatmap.png"), dpi=150)

    # 4. 折线图：地名趋势
    line_df = df[["chapter_index"] + place_names_norm].set_index("chapter_index").sort_index()
    plt.figure(figsize=(12, 6))
    for p in place_names_norm:
        plt.plot(line_df.index, line_df[p], label=p, linewidth=2)
    plt.title("各地名在前20章的章节频率变化")
    plt.legend(ncol=4, fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "place_trends_line.png"), dpi=150)

    # 5. 堆叠面积图
    plt.figure(figsize=(12, 6))
    plt.stackplot(line_df.index, [line_df[p] for p in place_names_norm], labels=place_names_norm, alpha=0.85)
    plt.title("前20章地名关注度构成（堆叠面积图）")
    plt.legend(loc="upper left", fontsize=9, ncol=2)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "place_stacked_area.png"), dpi=150)

    # 6. 累计曲线
    cum_df = line_df.cumsum()
    plt.figure(figsize=(12, 6))
    for p in place_names_norm:
        plt.plot(cum_df.index, cum_df[p], label=p, linewidth=2)
    plt.title("前20章地名累计出现次数")
    plt.legend(ncol=4, fontsize=9)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "place_cumulative.png"), dpi=150)



if __name__ == "__main__":
    main()

