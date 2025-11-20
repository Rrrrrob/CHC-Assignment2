# app.py
# -*- coding: utf-8 -*-
import os
from pathlib import Path
import streamlit as st


# -------------------------------
# 配置路径
# -------------------------------
BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "outputs"

st.set_page_config(page_title="儒林外史 可视化展示", page_icon="📘", layout="wide")
st.title("《儒林外史》前20章 可视化展示")
st.caption("展示前六个主要图表：总体柱状图、章节热力图、人物-地名热力图、地名趋势折线图、堆叠面积图、累计曲线图。")

# -------------------------------
# 图片列表
# -------------------------------
images = [
    ("totals_bar.png", "地名总体频率柱状图"),
    ("chapter_heatmap.png", "章节-地名频率热力图"),
    ("character_place_heatmap.png", "人物-地名共现热力图"),
    ("place_trends_line.png", "各地名在前20章的章节频率变化（折线图）"),
    ("place_stacked_area.png", "前20章地名关注度构成（堆叠面积图）"),
    ("place_cumulative.png", "前20章地名累计出现次数（增长曲线）"),
]

# -------------------------------
# 展示图片
# -------------------------------
st.header("可视化图表")
for fname, caption in images:
    p = OUT_DIR / fname
    if p.exists():
        st.image(str(p), caption=caption, use_column_width=True)
    else:
        st.info(f"未找到 {fname}，请先运行 analysis.py 生成。")

# -------------------------------
# 帮助函数
# -------------------------------
def file_exists(p: Path) -> bool:
    return p.exists() and p.is_file()

def read_text_file(p: Path, encoding="utf-8"):
    with open(p, "r", encoding=encoding) as f:
        return f.read()

def read_bytes_file(p: Path):
    with open(p, "rb") as f:
        return f.read()

# -------------------------------
# GIS 地图嵌入
# -------------------------------
st.header("GIS 地图")
map_path = OUT_DIR / "map.html"
if file_exists(map_path):
    try:
        html = read_text_file(map_path, encoding="utf-8")
        st.components.v1.html(html, height=600, scrolling=False)
    except Exception as e:
        st.warning(f"嵌入地图时出错：{e}")
else:
    st.info("未找到 map.html，请先运行 analysis.py 生成地图。")

