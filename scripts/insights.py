"""Refresh README figures with Python 3.9+ (standard library only)."""
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import re
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
today = datetime.now(ZoneInfo("Asia/Shanghai"))
current = today.year * 12 + today.month - 1
titles = defaultdict(list)
seen = set()
methods = ("Agent Uses Robot", "Agent Controls Policies", "Agent Trains Robot", "Agent Learns to Be Robot")
tasks = ("Manipulation", "Locomotion & Navigation", "Loco-Manipulation", "Interaction & Collaboration")
method_sizes = Counter()
tagged_sizes = Counter()
task_counts = defaultdict(Counter)
section = None
lines = (ROOT / "README.md").read_text().splitlines()
for index, line in enumerate(lines):
    if line.startswith("## "):
        section = line[3:]
    match = re.match(r"^- 🌟?\[[^\]]*?(20\d\d)\.(\d\d)(?:\.\d\d)?\]\(([^)]+)\), (.+)", line)
    if match:
        year, month, url, title = match.groups()
        if url not in seen:
            titles[int(year) * 12 + int(month) - 1].append(title.split(", [")[0])
            seen.add(url)
            if section in methods:
                method_sizes[section] += 1
                tag_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
                if tag_line in ("**Evaluation**", "**Survey scope**"):
                    continue
                tag = re.fullmatch(r"\*\*Task · (.+)\*\*", tag_line)
                if not tag:
                    raise ValueError(f"Missing task or evaluation label for {url}")
                families = set(tag[1].split(" + "))
                if not families.issubset(tasks):
                    raise ValueError(f"Unknown task family for {url}: {families.difference(tasks)}")
                tagged_sizes[section] += 1
                task_counts[section].update(families)

def month_name(month):
    return f"{month // 12}-{month % 12 + 1:02d}"

def label(x, y, value, size=16, color="#183649", anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(value))}</text>'

def save(name, height, elements):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}" font-family="Arial,sans-serif"><rect width="900" height="{height}" fill="#fafbf7"/>'
    (ROOT / "assets" / name).write_text(svg + "\n".join(elements) + "</svg>\n")

months = range(current - 11, current + 1)
peak = max(1, max(len(titles[m]) for m in months))
chart = [label(24, 32, "Publications in this list by month", 23)]
for i, month in enumerate(months):
    x = 50 + i * 72
    count = len(titles[month])
    height = round(count / peak * 130)
    color = "#82b5aa" if month == current else "#167466"
    chart.append(f'<rect x="{x-21}" y="{207-height}" width="42" height="{height}" fill="{color}"/>')
    chart.extend([label(x, 199-height, count, anchor="middle"), label(x, 229, month_name(month), 13, anchor="middle")])
chart.append(label(24, 262, "Counts use the listed publication or release date. The current month is partial.", 15))
save("monthly.svg", 280, chart)

stop = set("for and the with from through towards toward based using via into under beyond its how can that are robot robots robotic robotics agent agents agentic embodied learning model models large language task tasks system systems framework approach new real world".split())
phrases = {"vision-language-action": "VLA", "vision-language": "vision-language", "world model": "world model", "multi-robot": "multi-robot", "long-horizon": "long-horizon"}
def terms(title):
    title = title.lower()
    for phrase, term in phrases.items():
        title = re.sub(r"\b" + phrase + r"s?\b", term.replace(" ", "_"), title)
    return {w for w in re.findall(r"[a-zA-Z][a-zA-Z_-]+", title) if len(w)>2 and w not in stop}

cloud = [label(24, 32, "Recurring terms in paper titles", 23)]
for i, end in enumerate((current-6, current-3, current)):
    x = 24 + 294*i
    batch = [t for m in range(end-3,end) for t in titles[m]]
    freq = Counter(w for t in batch for w in terms(t))
    cloud.extend([label(x, 69, f"{month_name(end-3)} to {month_name(end-1)}", 18), label(x, 93, f"{len(batch)} publications", 14)])
    for j,(word,n) in enumerate(sorted(freq.items(), key=lambda kv:(-kv[1],kv[0]))[:7]):
        share = n / len(batch)
        y = 139 + j*44
        cloud.extend([label(x,y,word.replace("_"," "), min(31,15+round(70*share)), "#166f65"),label(x+260,y,f"{share:.0%}",15,anchor="end")])
cloud.append(label(24, 455, "Share of titles containing each term. Three complete months per column. Common field words omitted.", 15))
save("title-terms.svg",475,cloud)

matrix = [label(24, 36, "Which tasks does each method address?", 24)]
for column, task in enumerate(tasks):
    x = 316 + 162 * column
    parts = task.split(" & ")
    for j, part in enumerate(parts):
        text = part + " &" if len(parts) == 2 and j == 0 else part
        matrix.append(label(x, 79 + 18 * j, text, 16, anchor="middle"))
palette = ("#eff3f0", "#d4e7df", "#a6d0c0", "#65ae98", "#267b69", "#15564c")
for row, method in enumerate(methods):
    y = 111 + row * 61
    tagged = tagged_sizes[method]
    matrix.append(label(24, y + 23, method, 17))
    matrix.append(label(24, y + 43, f"{tagged} of {method_sizes[method]} task-tagged", 14, "#526675"))
    for column, task in enumerate(tasks):
        x = 238 + column * 162
        count = task_counts[method][task]
        share = count / tagged if tagged else 0
        shade = min(int(share * 6), len(palette) - 1)
        matrix.append(f'<rect x="{x}" y="{y}" width="156" height="55" rx="4" fill="{palette[shade]}"/>')
        ink = "#ffffff" if shade >= 4 else "#173e35"
        matrix.append(label(x + 78, y + 23, count, 21, ink, "middle"))
        matrix.append(label(x + 78, y + 43, f"{share:.1%}" if tagged else "—", 14, ink, "middle"))
matrix.append(label(24, 385, "Percentages use task-tagged papers in each row. Papers with multiple task tags count in each column.", 16))
save("method-task.svg", 406, matrix)
