#!/usr/bin/env python3
"""Render an explicitly scoped public-repository snapshot using the GitHub REST API."""
import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

OWNER = "Sh-Nasib"
ROOT = Path(__file__).resolve().parents[1]


def get_page(owner, page):
    url = (
        "https://api.github.com/users/"
        + urllib.parse.quote(owner, safe="")
        + "/repos?type=owner&per_page=100&page="
        + str(page)
    )
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Sh-Nasib-public-profile",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    if not isinstance(data, list):
        raise ValueError("Expected a repository list; snapshot was not updated.")
    return data


def load_repositories(owner):
    result = []
    page = 1
    while True:
        batch = get_page(owner, page)
        result.extend(batch)
        if len(batch) < 100:
            return result
        page += 1


def summarize(repositories, owner):
    public = [
        repo for repo in repositories
        if repo.get("owner", {}).get("login", "").casefold() == owner.casefold()
        and repo.get("private") is False
        and repo.get("fork") is False
        and repo.get("archived") is False
    ]
    by_name = {repo["full_name"]: repo for repo in public}
    public = sorted(by_name.values(), key=lambda repo: repo["full_name"].casefold())
    return {
        "owner": owner,
        "updated_date_utc": datetime.now(timezone.utc).date().isoformat(),
        "scope": "Owned public repositories, excluding forks and archived repositories",
        "public_repositories": len(public),
        "repository_stars": sum(int(repo["stargazers_count"]) for repo in public),
        "repositories": [
            {"name": repo["full_name"], "stars": int(repo["stargazers_count"])}
            for repo in public
        ],
    }


def render_svg(data):
    owner = html.escape(data["owner"])
    date = html.escape(data["updated_date_utc"])
    count = int(data["public_repositories"])
    stars = int(data["repository_stars"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="210" viewBox="0 0 1000 210" role="img" aria-labelledby="title desc">
  <title id="title">{owner}: публичные репозитории и звёзды</title>
  <desc id="desc">{count} публичных репозиториев, {stars} звёзд. Форки, архивы и закрытые репозитории исключены. Обновлено {date} UTC.</desc>
  <style>
    .surface {{ fill: #f6f8fa; stroke: #d8dee4; }}
    .title {{ fill: #57606a; }}
    .number {{ fill: #162b38; }}
    .accent {{ fill: #087f5b; }}
    @media (prefers-color-scheme: dark) {{
      .surface {{ fill: #0d1725; stroke: #2b3a4c; }}
      .title {{ fill: #a6b8cb; }}
      .number {{ fill: #f0f6fc; }}
      .accent {{ fill: #6ee7b7; }}
    }}
  </style>
  <rect class="surface" x=".5" y=".5" width="999" height="209" rx="18"/>
  <g font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif">
    <text class="accent" x="30" y="34" font-size="12" letter-spacing="2">PUBLIC GITHUB SNAPSHOT</text>
    <text class="title" x="970" y="34" text-anchor="end" font-size="12">{date} UTC</text>
    <text class="number" x="30" y="112" font-size="52" font-weight="700">{count}</text>
    <text class="title" x="30" y="142" font-size="17">Публичных репозиториев</text>
    <path d="M480 64v88" stroke="#8b949e" stroke-opacity=".3"/>
    <text class="number" x="520" y="112" font-size="52" font-weight="700">{stars}</text>
    <text class="title" x="520" y="142" font-size="17">Звёзд на этих репозиториях</text>
    <text class="title" x="30" y="184" font-size="12">Источник: GitHub REST API · Только {owner} · Без форков и архивов</text>
  </g>
</svg>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default=OWNER)
    args = parser.parse_args()
    data = summarize(load_repositories(args.owner), args.owner)
    svg = render_svg(data)
    output = ROOT / "assets"
    output.mkdir(exist_ok=True)
    (output / "public-stats.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "public-stats.svg").write_text(svg, encoding="utf-8")
    print(f"Public repositories: {data['public_repositories']}; stars: {data['repository_stars']}")


if __name__ == "__main__":
    main()
