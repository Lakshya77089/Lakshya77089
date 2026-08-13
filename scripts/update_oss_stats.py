
import os
import requests

USERNAME = os.environ["GITHUB_USERNAME"]
TOKEN = os.environ["GITHUB_TOKEN"]

API_URL = "https://api.github.com/search/issues"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
}

START_MARKER = "<!-- OSS-STATS:START -->"
END_MARKER = "<!-- OSS-STATS:END -->"


def github_search(query):
    """Fetch all matching GitHub issues/PRs."""
    results = []
    page = 1

    while True:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            params={
                "q": query,
                "per_page": 100,
                "page": page,
            },
            timeout=30,
        )

        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        results.extend(items)

        if len(items) < 100:
            break

        page += 1

        # GitHub Search API exposes at most 1000 results.
        if page > 10:
            break

    return results


def get_repo_name(item):
    """Extract owner/repository from a GitHub search result."""
    repository_url = item.get("repository_url", "")

    if not repository_url:
        return None

    return repository_url.rstrip("/").split("/repos/")[-1]


def get_repo_url(item):
    """Get repository HTML URL."""
    repository_url = item.get("repository_url", "")

    if not repository_url:
        return None

    return repository_url.replace(
        "https://api.github.com/repos/",
        "https://github.com/",
    )


def build_stats():
    stats = {}

    # ---------------------------------------------------------
    # 1. Issues created by the user
    # ---------------------------------------------------------
    issues = github_search(
        f"author:{USERNAME} type:issue"
    )

    for issue in issues:
        repo = get_repo_name(issue)

        if not repo:
            continue

        if repo not in stats:
            stats[repo] = {
                "issues": 0,
                "prs": 0,
                "merged": 0,
                "url": get_repo_url(issue),
            }

        stats[repo]["issues"] += 1

    # ---------------------------------------------------------
    # 2. Pull Requests created by the user
    # ---------------------------------------------------------
    prs = github_search(
        f"author:{USERNAME} type:pr"
    )

    for pr in prs:
        repo = get_repo_name(pr)

        if not repo:
            continue

        if repo not in stats:
            stats[repo] = {
                "issues": 0,
                "prs": 0,
                "merged": 0,
                "url": get_repo_url(pr),
            }

        stats[repo]["prs"] += 1

    # ---------------------------------------------------------
    # 3. Merged Pull Requests
    # ---------------------------------------------------------
    merged_prs = github_search(
        f"author:{USERNAME} type:pr is:merged"
    )

    for pr in merged_prs:
        repo = get_repo_name(pr)

        if not repo:
            continue

        if repo not in stats:
            stats[repo] = {
                "issues": 0,
                "prs": 0,
                "merged": 0,
                "url": get_repo_url(pr),
            }

        stats[repo]["merged"] += 1

    return stats


def generate_markdown(stats):
    if not stats:
        return (
            "No public open-source contributions found yet."
        )

    # Sort by total activity
    sorted_repos = sorted(
        stats.items(),
        key=lambda item: (
            item[1]["merged"],
            item[1]["prs"],
            item[1]["issues"],
        ),
        reverse=True,
    )

    lines = [
        "## 🌍 Open Source Contributions",
        "",
        "Contributions across repositories:",
        "",
        "| Repository | 🐛 Issues | 🔀 PRs | ✅ Merged PRs |",
        "|:---|---:|---:|---:|",
    ]

    for repo, data in sorted_repos:
        repository_url = data["url"]

        lines.append(
            f"| [{repo}]({repository_url}) "
            f"| {data['issues']} "
            f"| {data['prs']} "
            f"| {data['merged']} |"
        )

    return "\n".join(lines)


def update_readme(markdown):
    readme_path = "README.md"

    if not os.path.exists(readme_path):
        raise FileNotFoundError("README.md not found.")

    with open(readme_path, "r", encoding="utf-8") as file:
        content = file.read()

    if START_MARKER not in content or END_MARKER not in content:
        raise ValueError(
            "README.md must contain "
            f"{START_MARKER} and {END_MARKER}"
        )

    start = content.index(START_MARKER)
    end = content.index(END_MARKER)

    new_section = (
        START_MARKER
        + "\n\n"
        + markdown
        + "\n\n"
        + END_MARKER
    )

    updated_content = (
        content[:start]
        + new_section
        + content[end + len(END_MARKER):]
    )

    with open(readme_path, "w", encoding="utf-8") as file:
        file.write(updated_content)


def main():
    print(f"Fetching GitHub contributions for {USERNAME}...")

    stats = build_stats()

    print("\nRepositories found:")

    for repo, data in stats.items():
        print(
            f"{repo}: "
            f"Issues={data['issues']}, "
            f"PRs={data['prs']}, "
            f"Merged={data['merged']}"
        )

    markdown = generate_markdown(stats)

    update_readme(markdown)

    print("\nREADME.md updated successfully.")


if __name__ == "__main__":
    main()

