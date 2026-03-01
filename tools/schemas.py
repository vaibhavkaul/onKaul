"""Tool schema definitions for Claude API."""

from repository_config.repositories import REPOSITORIES

_repo_names: list[str] = list(REPOSITORIES.keys())


# Repo field used in search_code, read_file, list_directory.
# Uses an enum when repos are configured so the agent picks valid names;
# falls back to a plain string when no config is loaded yet.
def _repo_field(description: str = "Repository name") -> dict:
    field: dict = {"type": "string", "description": description}
    if _repo_names:
        field["enum"] = _repo_names
    return field


TOOL_SCHEMAS = [
    {
        "name": "get_sentry_issue",
        "description": """Fetch details about a Sentry error/exception.

        Use when:
        - A ticket or thread mentions a Sentry issue/link
        - Someone asks about an error, exception, or crash
        - You see a Sentry URL or issue ID

        Returns: title, stacktrace, frequency, first/last seen, affected users, permalink""",
        "input_schema": {
            "type": "object",
            "properties": {
                "issue_id": {
                    "type": "string",
                    "description": "Sentry issue ID (numeric or short ID like PROJ-1ABC)",
                }
            },
            "required": ["issue_id"],
        },
    },
    {
        "name": "search_code",
        "description": """Search for code in a repository.

        Use to find relevant files, functions, patterns, or usages.
        Choose the repo that matches what you're investigating based on the repository descriptions in the system prompt.

        Returns up to 10 matching files with paths and URLs.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": _repo_field("Repository to search"),
                "query": {
                    "type": "string",
                    "description": "Search query - function names, class names, error messages, keywords",
                },
            },
            "required": ["repo", "query"],
        },
    },
    {
        "name": "read_file",
        "description": """Read the contents of a specific file from a repository.

        Use after finding relevant files with search_code.
        Returns the full file contents.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": _repo_field(),
                "path": {
                    "type": "string",
                    "description": "Path to file from repo root (e.g., src/api/routes/users.py)",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to read from. Defaults to main.",
                },
            },
            "required": ["repo", "path"],
        },
    },
    {
        "name": "list_directory",
        "description": """List files and folders in a directory.

        Use to explore repository structure.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": _repo_field(),
                "path": {
                    "type": "string",
                    "description": "Directory path (empty string for repo root)",
                },
            },
            "required": ["repo", "path"],
        },
    },
    {
        "name": "query_datadog_logs",
        "description": """Search Datadog logs.

        Use when investigating runtime issues, errors in production, or tracing requests.
        Returns recent log entries matching the query.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Datadog log query (e.g., 'service:api status:error')",
                },
                "timeframe": {
                    "type": "string",
                    "description": "Time range (e.g., '1h', '24h', '7d')",
                    "default": "1h",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default: 50)",
                    "default": 50,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_datadog_monitors",
        "description": """List Datadog monitors.

        Use to check what's alerting or find monitors by tags.
        Returns list of monitors with status.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "string",
                    "description": "Comma-separated tags (e.g., 'env:prod,team:backend')",
                },
            },
        },
    },
    {
        "name": "get_datadog_monitor",
        "description": """Get details about a specific monitor.

        Returns monitor query, message, status.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "monitor_id": {
                    "type": "integer",
                    "description": "Monitor ID",
                }
            },
            "required": ["monitor_id"],
        },
    },
    {
        "name": "query_datadog_metrics",
        "description": """Query Datadog metrics.

        Use for performance analysis, error rates.
        Returns time series data.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Metric query (e.g., 'avg:api.latency{service:payments}')",
                },
                "timeframe": {
                    "type": "string",
                    "description": "Time range (default: '1h')",
                    "default": "1h",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "list_datadog_incidents",
        "description": """List Datadog incidents.

        Returns active/recent incidents.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Filter (e.g., 'state:active')",
                    "default": "state:active",
                }
            },
        },
    },
    {
        "name": "search_datadog_events",
        "description": """Search Datadog events.

        Find deployments, config changes.
        Returns events list.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Event query (e.g., 'tags:deployment')",
                },
                "timeframe": {
                    "type": "string",
                    "description": "Time range (default: '1h')",
                    "default": "1h",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "query_jira",
        "description": """Search Jira issues using acli.

        Use to find related issues, check if bug is known, or find similar problems.
        Returns list of matching issues.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "jql": {
                    "type": "string",
                    "description": "JQL query (e.g., 'project=B2B AND status=Open')",
                },
            },
            "required": ["jql"],
        },
    },
    {
        "name": "get_jira_issue",
        "description": """Get full details of a specific Jira issue.

        Use when you have an issue key and need full context.
        Returns summary, description, status, comments, etc.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "issue_key": {
                    "type": "string",
                    "description": "Jira issue key (e.g., 'B2B-456')",
                }
            },
            "required": ["issue_key"],
        },
    },
    {
        "name": "web_search",
        "description": """Search the web using Brave Search API for external information.

        Use when:
        - Researching external libraries, frameworks, or technologies (e.g., "React hooks best practices")
        - Looking up API documentation for 3rd party services
        - Finding Stack Overflow solutions for general programming problems
        - Researching industry standards or competitive landscape
        - Technology comparisons (e.g., "Redis vs Memcached")

        Do NOT use for:
        - TapTap Send internal code (use search_code instead)
        - Production errors (use Sentry/Datadog)
        - Team processes (use Confluence)

        Returns: Top 5 web results with title, URL, and description.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'OAuth2 best practices', 'Kotlin coroutines tutorial')",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results (default: 5, max: 20)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "create_pr_from_plan",
        "description": """Create a PR using headless Codex to generate a plan and apply it (onKaul handles commit/push/PR).

        Use ONLY when the user explicitly asks to implement a fix or create a PR.
        Provide a concise context summary; Codex will plan and implement the changes.
        Returns the PR URL if successful.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Repository name (must match a repo in your repository config)",
                },
                "title": {"type": "string", "description": "PR title"},
                "body": {"type": "string", "description": "PR description/body"},
                "base_branch": {"type": "string", "description": "Base branch (default: main)"},
                "context": {
                    "type": "string",
                    "description": "Issue context and expectations for the fix",
                },
            },
            "required": ["repo", "title", "body", "context"],
        },
    },
    {
        "name": "update_pr_from_plan",
        "description": """Update an existing PR by applying a plan to its head branch.

        Use when a user asks for changes to an existing PR (they provide a PR URL).
        Provide a concise context summary; the executor will plan/apply and push to the PR branch.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "pr_url": {"type": "string", "description": "GitHub PR URL"},
                "title": {"type": "string", "description": "Commit title for the update"},
                "body": {"type": "string", "description": "PR context/body to guide planning"},
                "context": {"type": "string", "description": "Issue context and requested changes"},
            },
            "required": ["pr_url", "title", "body", "context"],
        },
    },
    {
        "name": "close_pr",
        "description": """Close a GitHub pull request.

        Use when the user explicitly asks to close a PR.
        Requires a full PR URL (e.g., https://github.com/org/repo/pull/123).""",
        "input_schema": {
            "type": "object",
            "properties": {
                "pr_url": {"type": "string", "description": "GitHub PR URL"},
            },
            "required": ["pr_url"],
        },
    },
    {
        "name": "read_confluence_page",
        "description": """Read a Confluence wiki page (playbooks, documentation, RFCs).

        Use when:
        - Investigating an issue that references a playbook URL
        - User asks about documented procedures
        - Need to follow runbook/playbook steps
        - Datadog/Sentry alerts mention playbook links

        Returns: Page title and content (converted from HTML to readable text).

        Common use cases:
        - Dead letter queue playbooks
        - Incident response procedures
        - Team runbooks
        - Architecture RFCs""",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {
                    "type": "string",
                    "description": "Confluence page ID (extract from URL like 'pages/2030403650' → '2030403650') or full URL",
                }
            },
            "required": ["page_id"],
        },
    },
]
