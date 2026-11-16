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
for line in (ROOT / "README.md").read_text().splitlines():
    match = re.match(r"^- 🌟?\[[^\]]*?(20\d\d)\.(\d\d)(?:\.\d\d)?\]\(([^)]+)\), (.+)", line)
    if match:
        year, month, url, title = match.groups()
        if url not in seen:
            titles[int(year) * 12 + int(month) - 1].append(title.split(", [")[0])
            seen.add(url)

def month_name(month):
    return f"{month // 12}-{month % 12 + 1:02d}"

def label(x, y, value, size=16, color="#183649", anchor="start"):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}">{escape(str(value))}</text>'

def save(name, height, elements):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="{height}" viewBox="0 0 900 {height}" font-family="Arial,sans-serif"><rect width="100%" height="100%" fill="#fafbf7"/>'
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
