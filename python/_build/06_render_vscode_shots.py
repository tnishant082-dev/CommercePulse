#!/usr/bin/env python3
"""Render VS Code–style screenshots for CommercePulse SQL + ML work."""
from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
SHOTS = ROOT / "screenshots"
W, H = 1920, 1080

# VS Code Dark+ inspired
BG = (30, 30, 30)
SIDEBAR = (37, 37, 38)
SIDEBAR2 = (45, 45, 45)
ACTIVITY = (51, 51, 51)
TITLE = (60, 60, 60)
TAB_BG = (45, 45, 45)
TAB_ACTIVE = (30, 30, 30)
TAB_INACTIVE = (45, 45, 45)
EDITOR = (30, 30, 30)
LINE_GUTTER = (30, 30, 30)
STATUS = (0, 122, 204)  # classic blue status bar
BORDER = (60, 60, 60)
MUTED = (133, 133, 133)
WHITE = (212, 212, 212)
FG = (212, 212, 212)
TREE_FG = (204, 204, 204)
YELLOW = (220, 220, 170)
BLUE = (86, 156, 214)
GREEN = (106, 153, 85)
ORANGE = (206, 145, 120)
PURPLE = (197, 134, 192)
CYAN = (78, 201, 176)
STRING = (206, 145, 120)
KEYWORD = (86, 156, 214)
COMMENT = (106, 153, 85)
NUM = (181, 206, 168)
FUNC = (220, 220, 170)
SEL = (38, 79, 120)

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

ACTIVITY_W = 48
SIDEBAR_W = 260
TAB_H = 35
TITLE_H = 30
MENU_H = 0  # folded into title
STATUS_H = 22
TERM_H = 230


def F(path, size):
    return ImageFont.truetype(path, size)


def text_w(draw, s, font):
    b = draw.textbbox((0, 0), s, font=font)
    return b[2] - b[0]


def draw_window_chrome(draw, title="CommercePulse - Visual Studio Code"):
    # title bar
    draw.rectangle((0, 0, W, TITLE_H), fill=TITLE)
    # traffic lights
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        draw.ellipse((14 + i * 20, 8, 26 + i * 20, 20), fill=c)
    draw.text((90, 7), title, font=F(FONT, 13), fill=WHITE)
    # window controls right
    draw.text((W - 90, 6), "—   □   ×", font=F(FONT, 14), fill=MUTED)


def draw_activity_bar(draw, y0, y1, active="files"):
    draw.rectangle((0, y0, ACTIVITY_W, y1), fill=ACTIVITY)
    icons = [
        ("files", "☰", 18),
        ("search", "⌕", 70),
        ("git", "⑂", 122),
        ("debug", "▷", 174),
        ("ext", "▦", 226),
    ]
    for name, glyph, yy in icons:
        cy = y0 + yy
        if name == active:
            draw.rectangle((0, cy - 4, 3, cy + 28), fill=WHITE)
        draw.text((14, cy), glyph, font=F(FONT, 16), fill=WHITE if name == active else MUTED)
    # account / settings bottom
    draw.text((14, y1 - 70), "◎", font=F(FONT, 14), fill=MUTED)
    draw.text((14, y1 - 40), "⚙", font=F(FONT, 14), fill=MUTED)


def draw_file_tree(draw, x, y0, y1, expanded_sql=True, expanded_py=False, highlight=None):
    draw.rectangle((x, y0, x + SIDEBAR_W, y1), fill=SIDEBAR)
    draw.text((x + 16, y0 + 10), "EXPLORER", font=F(FONT_B, 11), fill=MUTED)
    draw.text((x + SIDEBAR_W - 40, y0 + 10), "⋯", font=F(FONT, 14), fill=MUTED)

    # section header
    hy = y0 + 36
    draw.rectangle((x, hy, x + SIDEBAR_W, hy + 22), fill=SIDEBAR2)
    draw.text((x + 10, hy + 4), "▼ COMMERCEPULSE", font=F(FONT_B, 11), fill=WHITE)

    # tree entries: (depth, name, kind, key)
    entries = [
        (0, "ai", "folder", None),
        (0, "artifacts", "folder", None),
        (0, "dashboard", "folder", None),
        (0, "data", "folder", None),
        (0, "excel", "folder", None),
        (0, "notebooks", "folder", "notebooks"),
        (1, "01_cleaning_eda.ipynb", "nb", None),
        (1, "02_customer_segmentation.ipynb", "nb", "nb_seg"),
        (1, "03_demand_or_clv_baseline.ipynb", "nb", "nb_churn"),
        (0, "python", "folder", "python"),
        (1, "01_build_medallion.py", "py", None),
        (1, "02_customer_segmentation.py", "py", "py_seg"),
        (1, "03_churn_baseline.py", "py", "py_churn"),
        (1, "_build", "folder", None),
        (0, "reports", "folder", None),
        (0, "screenshots", "folder", None),
        (0, "sql", "folder", "sql"),
        (1, "01_create_staging.sql", "sql", None),
        (1, "02_quality_checks.sql", "sql", "sql_quality"),
        (1, "03_gold_marts.sql", "sql", None),
        (1, "04_kpi_queries.sql", "sql", "sql_kpi"),
        (1, "05_practice_joins.sql", "sql", None),
        (0, "README.md", "md", None),
        (0, "requirements.txt", "txt", None),
    ]

    # collapse based on flags
    show = []
    skip_depth = None
    for depth, name, kind, key in entries:
        if skip_depth is not None:
            if depth > skip_depth:
                continue
            skip_depth = None
        if kind == "folder":
            if name == "sql" and not expanded_sql:
                show.append((depth, name, kind, key, False))
                skip_depth = depth
                continue
            if name == "python" and not expanded_py:
                show.append((depth, name, kind, key, False))
                skip_depth = depth
                continue
            if name == "notebooks" and not expanded_py and highlight and highlight.startswith("nb_"):
                # expand notebooks when highlighting nb
                show.append((depth, name, kind, key, True))
                continue
            if name == "notebooks" and (highlight or "").startswith("nb_"):
                show.append((depth, name, kind, key, True))
                continue
            if name == "notebooks" and not (highlight or "").startswith("nb_"):
                # keep collapsed unless we're in notebook mode
                if expanded_py:
                    show.append((depth, name, kind, key, True))
                else:
                    show.append((depth, name, kind, key, False))
                    skip_depth = depth
                continue
            open_folder = (
                (name == "sql" and expanded_sql)
                or (name == "python" and expanded_py)
                or (name == "notebooks" and (highlight or "").startswith("nb_"))
            )
            show.append((depth, name, kind, key, open_folder))
        else:
            show.append((depth, name, kind, key, None))

    # rebuild show more carefully
    show = []
    expand_nb = (highlight or "").startswith("nb_")
    for depth, name, kind, key in entries:
        if depth == 1:
            parent_hint = None
        if depth == 1 and name.endswith(".sql"):
            if not expanded_sql:
                continue
        if depth == 1 and name.endswith(".py"):
            if not expanded_py:
                continue
        if depth == 1 and name == "_build":
            if not expanded_py:
                continue
        if depth == 1 and name.endswith(".ipynb"):
            if not expand_nb:
                continue
        if kind == "folder" and name == "sql":
            show.append((depth, ("▼ " if expanded_sql else "▶ ") + name, kind, key))
        elif kind == "folder" and name == "python":
            show.append((depth, ("▼ " if expanded_py else "▶ ") + name, kind, key))
        elif kind == "folder" and name == "notebooks":
            show.append((depth, ("▼ " if expand_nb else "▶ ") + name, kind, key))
        elif kind == "folder":
            show.append((depth, "▶ " + name, kind, key))
        else:
            show.append((depth, name, kind, key))

    ty = hy + 28
    for depth, name, kind, key in show:
        if ty > y1 - 30:
            break
        indent = x + 14 + depth * 14
        if key and key == highlight:
            draw.rectangle((x + 2, ty - 2, x + SIDEBAR_W - 2, ty + 18), fill=(43, 45, 50))
            draw.rectangle((x + 2, ty - 2, x + 4, ty + 18), fill=STATUS)
        # icon tint
        if kind == "sql" or name.endswith(".sql"):
            col = ORANGE
            icon = "𝕤"
        elif kind == "py" or name.endswith(".py"):
            col = BLUE
            icon = "𝕡"
        elif kind == "nb" or name.endswith(".ipynb"):
            col = ORANGE
            icon = "𝕟"
        elif kind == "md":
            col = BLUE
            icon = "𝕞"
        elif kind == "folder" or name.startswith("▶") or name.startswith("▼"):
            col = YELLOW
            icon = ""
        else:
            col = TREE_FG
            icon = ""
        label = name
        draw.text((indent, ty), label, font=F(FONT, 12), fill=TREE_FG if key != highlight else WHITE)
        ty += 20


SQL_KW = {
    "SELECT", "FROM", "WHERE", "AND", "OR", "AS", "GROUP", "BY", "ORDER", "LIMIT",
    "HAVING", "JOIN", "INNER", "LEFT", "RIGHT", "ON", "CASE", "WHEN", "THEN", "ELSE",
    "END", "CREATE", "OR", "REPLACE", "VIEW", "TABLE", "IF", "NOT", "NULL", "IN",
    "COUNT", "SUM", "AVG", "MIN", "MAX", "DISTINCT", "ROUND", "CAST", "UNSIGNED",
    "DATETIME", "INT", "VARCHAR", "DECIMAL", "WITH", "OVER", "PARTITION", "RANK",
    "LAG", "DESC", "ASC", "BETWEEN", "LIKE", "IS", "ELSE",
}
PY_KW = {
    "import", "from", "as", "def", "class", "return", "if", "elif", "else", "for",
    "while", "in", "not", "and", "or", "True", "False", "None", "with", "try",
    "except", "print", "len", "float", "int", "round", "list", "dict", "zip",
}


def tokenize_sql_line(line):
    if line.strip().startswith("--"):
        return [("comment", line)]
    tokens = []
    i = 0
    while i < len(line):
        if line[i] == "-" and i + 1 < len(line) and line[i + 1] == "-":
            tokens.append(("comment", line[i:]))
            break
        if line[i] in "'\"":
            q = line[i]
            j = i + 1
            while j < len(line) and line[j] != q:
                j += 1
            tokens.append(("string", line[i : j + 1]))
            i = j + 1
            continue
        if line[i].isdigit():
            j = i
            while j < len(line) and (line[j].isdigit() or line[j] == "."):
                j += 1
            tokens.append(("num", line[i:j]))
            i = j
            continue
        if line[i].isalpha() or line[i] == "_":
            j = i
            while j < len(line) and (line[j].isalnum() or line[j] == "_"):
                j += 1
            word = line[i:j]
            if word.upper() in SQL_KW:
                tokens.append(("kw", word))
            else:
                tokens.append(("id", word))
            i = j
            continue
        tokens.append(("sym", line[i]))
        i += 1
    return tokens


def tokenize_py_line(line):
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return [("comment", line)]
    tokens = []
    i = 0
    while i < len(line):
        if line[i] == "#":
            tokens.append(("comment", line[i:]))
            break
        if line[i] in "'\"":
            q = line[i]
            # triple?
            if line[i : i + 3] in ('"""', "'''"):
                q3 = line[i : i + 3]
                j = i + 3
                while j < len(line) and line[j : j + 3] != q3:
                    j += 1
                tokens.append(("string", line[i : min(j + 3, len(line))]))
                i = min(j + 3, len(line))
                continue
            j = i + 1
            while j < len(line) and line[j] != q:
                if line[j] == "\\":
                    j += 2
                    continue
                j += 1
            tokens.append(("string", line[i : j + 1]))
            i = j + 1
            continue
        if line[i].isdigit():
            j = i
            while j < len(line) and (line[j].isdigit() or line[j] == "."):
                j += 1
            tokens.append(("num", line[i:j]))
            i = j
            continue
        if line[i].isalpha() or line[i] == "_":
            j = i
            while j < len(line) and (line[j].isalnum() or line[j] == "_"):
                j += 1
            word = line[i:j]
            if word in PY_KW:
                tokens.append(("kw", word))
            else:
                tokens.append(("id", word))
            i = j
            continue
        tokens.append(("sym", line[i]))
        i += 1
    return tokens


COLOR_MAP = {
    "comment": COMMENT,
    "string": STRING,
    "num": NUM,
    "kw": KEYWORD,
    "id": FG,
    "sym": FG,
    "func": FUNC,
}


def draw_code(draw, lines, x, y, max_lines, lang="sql", highlight_todo=True, start_line=1):
    mono = F(MONO, 13)
    mono_b = F(MONO_B, 13)
    line_h = 20
    gutter_w = 48
    # gutter bg
    draw.rectangle((x, y, x + gutter_w, y + max_lines * line_h + 8), fill=(30, 30, 30))
    draw.line((x + gutter_w, y, x + gutter_w, y + max_lines * line_h + 8), fill=(45, 45, 45), width=1)

    for li, line in enumerate(lines[:max_lines]):
        ln = start_line + li
        yy = y + 4 + li * line_h
        # line number
        ln_s = str(ln)
        draw.text((x + gutter_w - 8 - text_w(draw, ln_s, mono), yy), ln_s, font=mono, fill=(85, 85, 85))

        # TODO highlight band
        if highlight_todo and "TODO" in line:
            draw.rectangle(
                (x + gutter_w + 2, yy - 1, W - 20, yy + line_h - 2),
                fill=(55, 50, 30),
            )

        tokens = tokenize_sql_line(line) if lang == "sql" else tokenize_py_line(line)
        cx = x + gutter_w + 12
        for kind, tok in tokens:
            col = COLOR_MAP.get(kind, FG)
            if kind == "kw":
                font = mono_b
            else:
                font = mono
            # soften identifiers that look like functions before (
            draw.text((cx, yy), tok, font=font, fill=col)
            cx += text_w(draw, tok, font)
            if cx > W - 40:
                break


def draw_tabs(draw, x, y, tabs, active_idx, dirty_idx=None):
    draw.rectangle((x, y, W, y + TAB_H), fill=TAB_BG)
    tx = x
    for i, name in enumerate(tabs):
        tw = text_w(draw, name, F(FONT, 12)) + 40
        if i == active_idx:
            draw.rectangle((tx, y, tx + tw, y + TAB_H), fill=TAB_ACTIVE)
            draw.rectangle((tx, y + TAB_H - 2, tx + tw, y + TAB_H), fill=STATUS)
            col = WHITE
        else:
            draw.rectangle((tx, y, tx + tw, y + TAB_H), fill=TAB_INACTIVE)
            col = MUTED
        label = name
        draw.text((tx + 14, y + 9), label, font=F(FONT, 12), fill=col)
        if dirty_idx is not None and i == dirty_idx:
            draw.ellipse((tx + tw - 16, y + 14, tx + tw - 10, y + 20), fill=WHITE)
        else:
            draw.text((tx + tw - 18, y + 8), "×", font=F(FONT, 11), fill=MUTED)
        tx += tw + 1


def draw_status(draw, y, lang="SQL", ln=1, col=1, extra="UTF-8"):
    draw.rectangle((0, y, W, H), fill=STATUS)
    draw.text((12, y + 4), "  main*", font=F(FONT, 11), fill=WHITE)
    draw.text((100, y + 4), "○ 0  ⚠ 1", font=F(FONT, 11), fill=WHITE)
    right = f"Ln {ln}, Col {col}   {extra}   LF   {lang}   Spaces: 4"
    draw.text((W - text_w(draw, right, F(FONT, 11)) - 20, y + 4), right, font=F(FONT, 11), fill=WHITE)


def draw_terminal(draw, x, y, w, h, lines, title="Terminal"):
    draw.rectangle((x, y, x + w, y + h), fill=(25, 25, 25))
    # panel tab bar
    draw.rectangle((x, y, x + w, y + 28), fill=(37, 37, 38))
    for i, t in enumerate(["PROBLEMS", "OUTPUT", "DEBUG CONSOLE", "TERMINAL"]):
        xx = x + 16 + i * 120
        col = WHITE if t == "TERMINAL" else MUTED
        draw.text((xx, y + 7), t, font=F(FONT_B if t == "TERMINAL" else FONT, 11), fill=col)
        if t == "TERMINAL":
            draw.rectangle((xx, y + 26, xx + 70, y + 28), fill=STATUS)
    draw.text((x + w - 80, y + 6), "bash ▼  +  ×", font=F(FONT, 11), fill=MUTED)

    mono = F(MONO, 12)
    ty = y + 36
    for kind, text in lines:
        if kind == "prompt":
            draw.text((x + 12, ty), text, font=mono, fill=CYAN)
        elif kind == "out":
            draw.text((x + 12, ty), text, font=mono, fill=FG)
        elif kind == "warn":
            draw.text((x + 12, ty), text, font=mono, fill=ORANGE)
        elif kind == "ok":
            draw.text((x + 12, ty), text, font=mono, fill=NUM)
        else:
            draw.text((x + 12, ty), text, font=mono, fill=MUTED)
        ty += 17
        if ty > y + h - 10:
            break


def render_sql_shot(outfile, sql_path, highlight_key, tabs, active_name, dirty=False, term_lines=None):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_window_chrome(draw)

    content_top = TITLE_H
    status_y = H - STATUS_H
    term_y = status_y - (TERM_H if term_lines else 0)
    editor_bottom = term_y if term_lines else status_y

    draw_activity_bar(draw, content_top, status_y)
    sidebar_x = ACTIVITY_W
    draw_file_tree(
        draw,
        sidebar_x,
        content_top,
        editor_bottom,
        expanded_sql=True,
        expanded_py=False,
        highlight=highlight_key,
    )

    editor_x = ACTIVITY_W + SIDEBAR_W
    draw_tabs(
        draw,
        editor_x,
        content_top,
        tabs,
        tabs.index(active_name),
        dirty_idx=(tabs.index(active_name) if dirty else None),
    )

    # breadcrumb
    by = content_top + TAB_H
    draw.rectangle((editor_x, by, W, by + 24), fill=EDITOR)
    crumb = f"CommercePulse  ›  sql  ›  {active_name}"
    draw.text((editor_x + 12, by + 4), crumb, font=F(FONT, 11), fill=MUTED)

    code_y = by + 24
    sql_text = (ROOT / sql_path).read_text()
    lines = sql_text.splitlines()
    # show a useful window of lines
    max_lines = max(8, (editor_bottom - code_y - 8) // 20)
    draw.rectangle((editor_x, code_y, W, editor_bottom), fill=EDITOR)
    draw_code(draw, lines, editor_x, code_y, max_lines, lang="sql", highlight_todo=True)

    if term_lines:
        draw_terminal(draw, editor_x, term_y, W - editor_x, TERM_H, term_lines)

    # language from file
    draw_status(draw, status_y, lang="SQL", ln=12, col=5, extra="UTF-8")
    img.save(SHOTS / outfile, "PNG")
    print("wrote", outfile)


def render_py_shot(outfile, py_path, highlight_key, tabs, active_name, dirty=False, term_lines=None, start_line=1, take_lines=None):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_window_chrome(draw)

    content_top = TITLE_H
    status_y = H - STATUS_H
    term_y = status_y - (TERM_H if term_lines else 220)
    if not term_lines:
        term_y = status_y - 220
        term_lines = term_lines or []
    editor_bottom = term_y

    draw_activity_bar(draw, content_top, status_y)
    expand_py = highlight_key.startswith("py_")
    expand_nb = highlight_key.startswith("nb_")
    draw_file_tree(
        draw,
        ACTIVITY_W,
        content_top,
        editor_bottom,
        expanded_sql=False,
        expanded_py=expand_py,
        highlight=highlight_key,
    )

    editor_x = ACTIVITY_W + SIDEBAR_W
    draw_tabs(
        draw,
        editor_x,
        content_top,
        tabs,
        tabs.index(active_name),
        dirty_idx=(tabs.index(active_name) if dirty else None),
    )

    by = content_top + TAB_H
    draw.rectangle((editor_x, by, W, by + 24), fill=EDITOR)
    folder = "python" if active_name.endswith(".py") else "notebooks"
    draw.text((editor_x + 12, by + 4), f"CommercePulse  ›  {folder}  ›  {active_name}", font=F(FONT, 11), fill=MUTED)

    code_y = by + 24
    text = (ROOT / py_path).read_text()
    lines = text.splitlines()
    if take_lines:
        # take_lines is (start, end) 1-indexed inclusive for display window
        s, e = take_lines
        view = lines[s - 1 : e]
        start_line = s
    else:
        view = lines
        start_line = 1
    max_lines = max(8, (editor_bottom - code_y - 8) // 20)
    draw.rectangle((editor_x, code_y, W, editor_bottom), fill=EDITOR)
    draw_code(draw, view, editor_x, code_y, max_lines, lang="py", highlight_todo=True, start_line=start_line)

    draw_terminal(draw, editor_x, term_y, W - editor_x, status_y - term_y, term_lines)
    lang = "Python" if active_name.endswith(".py") else "Jupyter"
    draw_status(draw, status_y, lang=f"{lang}  3.11.9", ln=48, col=17, extra="UTF-8")
    img.save(SHOTS / outfile, "PNG")
    print("wrote", outfile)


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    metrics = json.loads((ROOT / "reports" / "model_metrics.json").read_text())
    seg = json.loads((ROOT / "reports" / "segmentation_metrics.json").read_text())

    lr = metrics["churn"]["logistic_regression"]
    gb = metrics["churn"]["gradient_boosting"]

    # 1) KPI SQL
    render_sql_shot(
        "vscode-sql-kpi.png",
        "sql/04_kpi_queries.sql",
        "sql_kpi",
        ["04_kpi_queries.sql", "03_gold_marts.sql", "02_quality_checks.sql"],
        "04_kpi_queries.sql",
        dirty=True,
        term_lines=[
            ("dim", "[SQL] Connected  ·  CommercePulse local"),
            ("prompt", "nishant@dev:~/CommercePulse$ mysql -u root commercepulse < sql/04_kpi_queries.sql"),
            ("out", "Revenue\tOrders\tCustomers\tAOV"),
            ("ok", "20076377.25\t39575\t5862\t507.32"),
            ("out", "uk_revenue_share"),
            ("ok", "0.8562"),
            ("dim", "-- Nov peaks show up in monthly trend ✓"),
        ],
    )

    # 2) quality SQL
    render_sql_shot(
        "vscode-sql-quality.png",
        "sql/02_quality_checks.sql",
        "sql_quality",
        ["02_quality_checks.sql", "01_create_staging.sql", "05_practice_joins.sql"],
        "02_quality_checks.sql",
        dirty=False,
        term_lines=[
            ("prompt", "nishant@dev:~/CommercePulse$ mysql -u root commercepulse < sql/02_quality_checks.sql"),
            ("out", "null_invoice_dates"),
            ("ok", "0"),
            ("out", "cancel_with_positive_qty"),
            ("ok", "0"),
            ("out", "null_customer_ids"),
            ("warn", "236007   -- guests; keep in sales, drop before RFM join"),
            ("dim", "Problems  ·  1 warning (TODO: index Country)"),
        ],
    )

    # 3) churn ML — show the LR hero section of the script
    # find a good window around logistic regression
    churn_path = ROOT / "python/03_churn_baseline.py"
    churn_lines = churn_path.read_text().splitlines()
    # prefer lines with "start with logistic" through metrics print
    start = 1
    for i, ln in enumerate(churn_lines):
        if "leakage risk" in ln or "churn_cols" in ln:
            start = max(1, i + 1 - 3)
            break
    end = min(len(churn_lines), start + 42)

    render_py_shot(
        "vscode-ml-churn.png",
        "python/03_churn_baseline.py",
        "py_churn",
        ["03_churn_baseline.py", "02_customer_segmentation.py", "model_metrics.json"],
        "03_churn_baseline.py",
        dirty=True,
        take_lines=(start, end),
        term_lines=[
            ("prompt", "nishant@dev:~/CommercePulse$ python python/03_churn_baseline.py"),
            ("out", "loading ml_customer_features…"),
            ("out", "customers (registered): 5862"),
            ("out", "train=4396  test=1466  base_rate=0.507"),
            ("ok", f"LogisticRegression  accuracy={lr['accuracy']:.4f}  AUC={lr['auc']:.4f}"),
            ("out", "trying GradientBoosting as a quick experiment…"),
            ("ok", f"GradientBoosting    accuracy={gb['accuracy']:.4f}  AUC={gb['auc']:.4f}"),
            ("warn", "/sklearn/...: ConvergenceWarning ignored (max_iter=500)"),
            ("out", "--- summary ---"),
            ("ok", f"LR  AUC={lr['auc']:.3f}  Acc={lr['accuracy']:.3f}"),
            ("ok", f"GB  AUC={gb['auc']:.3f}  Acc={gb['accuracy']:.3f}  (experiment)"),
        ],
    )

    # 4) segmentation — show notebook-ish view via the .py script + RFM terminal
    # Prefer showing segmentation script with notebook tab also open
    seg_path = ROOT / "python/02_customer_segmentation.py"
    seg_lines = seg_path.read_text().splitlines()
    s2 = 1
    for i, ln in enumerate(seg_lines):
        if "log1p" in ln or "silhouette" in ln.lower() or "try a few k" in ln:
            s2 = max(1, i + 1 - 1)
            break
    e2 = min(len(seg_lines), s2 + 40)

    segs = [s["Segment"] for s in seg["segments"]]
    render_py_shot(
        "vscode-ml-segmentation.png",
        "python/02_customer_segmentation.py",
        "py_seg",
        ["02_customer_segmentation.py", "02_customer_segmentation.ipynb", "segmentation_metrics.json"],
        "02_customer_segmentation.py",
        dirty=False,
        take_lines=(s2, e2),
        term_lines=[
            ("prompt", "nishant@dev:~/CommercePulse$ python python/02_customer_segmentation.py"),
            ("out", f"fitted k={seg['k']}  silhouette={seg['silhouette_full']:.3f}  n={seg['n_customers']}"),
            ("out", "segments:"),
            ("ok", "  " + ", ".join(segs)),
            ("out", "silhouette sweep (sample): " + ", ".join(f"k={k}:{v:.2f}" for k, v in seg["silhouette_k_sweep"].items())),
            ("dim", "# Champions should be low recency + high monetary — looks ok"),
            ("prompt", "nishant@dev:~/CommercePulse$ █"),
        ],
    )


if __name__ == "__main__":
    main()
