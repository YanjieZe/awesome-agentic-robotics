"""Refresh GitHub star rankings from the repository links in README.md (requires authenticated gh)."""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from statistics import median
import subprocess

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("Agent Uses Robot", "Agent Controls Policies", "Agent Trains Robot", "Agent Learns to Be Robot")
TASKS = ("Manipulation", "Locomotion & Navigation", "Loco-Manipulation", "Interaction & Collaboration")
ENTRY = re.compile(r"^- 🌟?\[[^\]]*20\d\d\.\d\d(?:\.\d\d)?\]\(([^)]+)\), (.+)")
REPO = re.compile(r"\[(?:GitHub|code|companion repository)\]\(https://github\.com/([\w.-]+/[\w.-]+)/?\)", re.I)


def read_papers():
    papers = []
    lines = (ROOT / "README.md").read_text().splitlines()
    section = None
    for index, line in enumerate(lines):
        if line.startswith("## "):
            section = line[3:]
        entry = ENTRY.match(line)
        if entry:
            url, rest = entry.groups()
            title = rest.split(", [", 1)[0]
            tag = re.fullmatch(r"  \*\*Task · (.+)\*\*", lines[index + 1])
            groups = tag[1].split(" + ") if tag else []
            if section in METHODS:
                groups.append(section)
            papers.append((url, title, groups, set(r.lower() for r in REPO.findall(line))))
    return papers


def fetch_stars(slugs):
    result = {}
    for offset in range(0, len(slugs), 40):
        batch = slugs[offset:offset + 40]
        queries = []
        for i, slug in enumerate(batch):
            owner, name = slug.split("/")
            queries.append(f'r{i}:repository(owner:{json.dumps(owner)}, name:{json.dumps(name)})'
                           '{nameWithOwner stargazerCount isPrivate}')
        response = subprocess.run(["gh", "api", "graphql", "-f", "query={" + " ".join(queries) + "}"],
                                  capture_output=True, text=True)
        if not response.stdout:
            raise RuntimeError(response.stderr)
        payload = json.loads(response.stdout)
        errors = payload.get("errors", [])
        if any(e.get("type") != "NOT_FOUND" for e in errors) or not payload.get("data"):
            raise RuntimeError(errors or response.stderr)
        for i, slug in enumerate(batch):
            repo = payload["data"][f"r{i}"]
            if repo and not repo["isPrivate"]:
                result[slug] = (repo["nameWithOwner"], repo["stargazerCount"])
    return result


def main():
    papers = read_papers()
    stars = fetch_stars(sorted({slug for _, _, _, repos in papers for slug in repos}))
    by_group = defaultdict(lambda: defaultdict(list))
    totals = defaultdict(int)
    covered = defaultdict(int)
    counts = {}
    for url, title, groups, repos in papers:
        for group in ["All", *groups]:
            totals[group] += 1
            public = {stars[slug] for slug in repos if slug in stars}
            if public:
                covered[group] += 1
            for name, count in public:
                counts[name] = count
                by_group[group][name].append((url, title))

    day = datetime.now(timezone.utc).date()
    lines = ["# GitHub star rankings", "",
             f"GitHub snapshot · {day} UTC · {covered['All']} of {totals['All']} papers matched to "
             f"{len(counts)} public project repositories.", "",
             "Each repository counts once per group. Stars belong to the whole repository, including shared "
             "codebases. Coverage counts papers with a matched public repository. Unmatched papers contribute "
             "only to the coverage denominator. A multi-task paper appears under each of its task families.", "",
             "Project repositories may contain code, data, or the authors’ project page. The 🌟 marker in the "
             "reading list identifies verified code releases.", "",
             "[Method totals](#four-methods-by-total-stars) · [Task totals](#four-tasks-by-total-stars)"]
    for heading, label, groups in (("Four methods by total stars", "Method", METHODS),
                                   ("Four tasks by total stars", "Task", TASKS)):
        lines.extend(["", f"## {heading}", "",
                      f"| Rank | {label} | Total stars | Repositories | Median stars | Paper coverage |",
                      "| ---: | --- | ---: | ---: | ---: | ---: |"])
        sums = {g: sum(counts[n] for n in by_group[g]) for g in groups}
        previous = None
        for i, group in enumerate(sorted(groups, key=sums.get, reverse=True), 1):
            if sums[group] != previous:
                rank = i
            previous = sums[group]
            values = [counts[n] for n in by_group[group]]
            middle = f"{median(values):,g}" if values else "—"
            anchor = group.lower().replace("&", "").replace(" ", "-")
            lines.append(f"| {rank} | [{group}](#{anchor}) | {sums[group]:,} | {len(values)} | {middle} | "
                         f"{covered[group]}/{totals[group]} |")

    for heading, groups in (("Projects by method", METHODS), ("Projects by task", TASKS)):
        lines.extend(["", f"## {heading}"])
        for group in groups:
            lines.extend(["", f"### {group}", "",
                          f"{covered[group]} of {totals[group]} papers matched · {len(by_group[group])} repositories.",
                          "", "| Rank | Repository | Stars | Paper |", "| ---: | --- | ---: | --- |"])
            previous = None
            for i, name in enumerate(sorted(by_group[group], key=lambda n: (-counts[n], n.lower())), 1):
                if counts[name] != previous:
                    rank = i
                previous = counts[name]
                references = []
                for url, title in by_group[group][name]:
                    safe = title.replace("|", "&#124;").replace("[", "&#91;").replace("]", "&#93;")
                    references.append(f"[{safe}]({url})")
                lines.append(f"| {rank} | [{name}](https://github.com/{name}) | {counts[name]:,} | "
                             + "<br>".join(references) + " |")
    (ROOT / "STAR-RANKINGS.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
