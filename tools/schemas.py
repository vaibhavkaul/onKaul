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
                    "enum": ["appian-frontend", "appian-server", "tts-business"],
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
                    "enum": ["appian-frontend", "appian-server", "tts-business"],
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
                    "enum": ["appian-frontend", "appian-server", "tts-business"],
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
        "description": """Search the web for documentation, Stack Overflow answers, or library info.

        Use for external libraries, APIs, or general programming questions.
        Don't use for TapTap Send internal code - use search_code instead.""",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
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
]
