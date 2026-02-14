"""Tool schema definitions for Claude API."""

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
        Choose repo based on what you're investigating:
        - appian-frontend: React Native mobile app (TypeScript/TSX)
        - appian-server: Kotlin/Spring Boot backend
        - tts-business: B2B money transfer platform (Python/React)

        Returns up to 10 matching files with paths and URLs.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "enum": ["appian-frontend", "appian-server", "tts-business", "analytics"],
                    "description": "Repository to search",
                },
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
                "repo": {
                    "type": "string",
                    "enum": ["appian-frontend", "appian-server", "tts-business", "analytics"],
                },
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
                "repo": {
                    "type": "string",
                    "enum": ["appian-frontend", "appian-server", "tts-business", "analytics"],
                },
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
                    "description": "Search query (e.g., 'OAuth2 best practices', 'Kotlin coroutines tutorial')"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results (default: 5, max: 20)",
                    "default": 5
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_legal_compliance_rules",
        "description": """Get TapTap Send marketing compliance rules and regulations.

        Use when:
        - Investigating marketing content issues
        - Checking what disclaimers are required
        - Understanding regulatory requirements
        - Validating marketing materials

        Returns detailed compliance requirements for:
        - FX disclaimers
        - Exchange rate language
        - Transfer speed claims
        - Geographic regulatory disclosures (UAE, Australia, USA, etc.)
        - Content-type requirements (emails, influencer, competitions)""",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": [
                        "all",
                        "fx_disclaimers",
                        "geographic_disclosures",
                        "content_type_requirements",
                    ],
                    "description": "Category of rules to retrieve (default: all)",
                }
            },
        },
    },
    {
        "name": "review_github_pr",
        "description": """Review a GitHub Pull Request with comprehensive code analysis.

        Use when:
        - User shares a GitHub PR URL
        - User asks to review PR #number
        - User asks for code review feedback

        Returns: PR metadata (title, author, description) and full diff for review.

        Always use Opus model for PR reviews (deep analysis required).""",
        "input_schema": {
            "type": "object",
            "properties": {
                "pr_url": {
                    "type": "string",
                    "description": "GitHub PR URL (e.g., 'https://github.com/taptapsend/appian-frontend/pull/1234') or short form (e.g., 'appian-frontend#1234')",
                }
            },
            "required": ["pr_url"],
        },
    },
    {
        "name": "create_pr_from_patch",
        "description": """Create a PR by applying a unified diff patch in a temporary workspace.

        Use ONLY when the user explicitly asks to implement a fix or create a PR.
        Provide a unified diff patch with paths relative to repo root.
        Returns the PR URL if successful.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository name (e.g., 'appian-server')"},
                "patch": {"type": "string", "description": "Unified diff patch (git apply compatible)"},
                "title": {"type": "string", "description": "PR title"},
                "body": {"type": "string", "description": "PR description/body"},
                "base_branch": {"type": "string", "description": "Base branch (default: main)"},
            },
            "required": ["repo", "patch", "title", "body"],
        },
    },
    {
        "name": "create_pr_from_plan",
        "description": """Create a PR by applying line-based edits in a temporary workspace.

        Use ONLY when the user explicitly asks to implement a fix or create a PR.
        Provide a plan with line-based edits (replace/insert/delete) relative to repo root.
        Returns the PR URL if successful.""",
        "input_schema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repository name (e.g., 'appian-server')"},
                "title": {"type": "string", "description": "PR title"},
                "body": {"type": "string", "description": "PR description/body"},
                "base_branch": {"type": "string", "description": "Base branch (default: main)"},
                "edits": {
                    "type": "array",
                    "description": "Line-based edits",
                    "items": {
                        "type": "object",
                        "properties": {
                            "op": {"type": "string", "enum": ["replace", "insert", "delete"]},
                            "path": {"type": "string"},
                            "start_line": {"type": "integer"},
                            "end_line": {"type": "integer"},
                            "new_lines": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["op", "path", "start_line"],
                    },
                },
            },
            "required": ["repo", "title", "body", "edits"],
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
