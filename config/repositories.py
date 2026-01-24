"""Repository configuration for TapTap Send codebases.

This config is derived from:
- /Users/vkaul/code/com.github.taptapsend/CLAUDE.md
- /Users/vkaul/code/com.github.taptapsend/ai-context/*.md
"""

REPOSITORIES = {
    "appian-frontend": {
        "name": "appian-frontend",
        "org": "taptapsend",
        "description": "React Native mobile application",
        "tech_stack": [
            "React Native",
            "TypeScript/TSX",
            "Redux (state management)",
            "GraphQL (with code generation)",
            "XState (state machines)",
            "Jest (unit tests)",
            "Detox (E2E tests)",
        ],
        "key_systems": [
            "Feather Component Library (js/src/feather/)",
            "Backend Integration (TanStack Query + Redux)",
            "i18n System (strings codegen)",
            "Deep Link Handling",
            "Event Bus",
        ],
        "handles": [
            "UI bugs and crashes",
            "Mobile app issues",
            "Frontend logic errors",
            "React Native crashes",
            "Component rendering issues",
            "Navigation problems",
            "Deep link issues",
        ],
        "context_files": [
            "../ai-context/frontend-dev.md",
            "../ai-context/feather-components.md",
            "../ai-context/i18n-system.md",
            "../ai-context/deep-links.md",
            "../ai-context/event-bus.md",
        ],
    },
    "appian-server": {
        "name": "appian-server",
        "org": "taptapsend",
        "description": "Kotlin/Spring Boot backend server",
        "tech_stack": [
            "Kotlin",
            "Spring Boot",
            "PostgreSQL",
            "JOOQ (type-safe DB access)",
            "Flyway (migrations)",
            "Gradle (Kotlin DSL)",
            "Docker",
        ],
        "key_systems": [
            "REST API (EmptyResponse pattern)",
            "Feature Flag System (Consul-based)",
            "Database Migrations (Flyway)",
            "JOOQ Generated Code",
        ],
        "handles": [
            "API errors and failures",
            "Backend logic bugs",
            "Database issues",
            "Migration failures",
            "Business logic errors",
            "Performance issues",
            "Feature flag problems",
        ],
        "context_files": [
            "../ai-context/backend-dev.md",
            "../ai-context/feature-flags.md",
        ],
    },
}

# Investigation strategy mapping
INVESTIGATION_STRATEGY = {
    "Frontend/UI bugs": "appian-frontend",
    "Mobile crashes": "appian-frontend",
    "React Native errors": "appian-frontend",
    "Component issues": "appian-frontend",
    "Navigation problems": "appian-frontend",
    "Deep link issues": "appian-frontend",
    "API errors": "appian-server",
    "Backend failures": "appian-server",
    "Database issues": "appian-server",
    "Business logic bugs": "appian-server",
    "Migration errors": "appian-server",
    "Performance issues": "appian-server",
}

# Additional context sources
ADDITIONAL_CONTEXT = {
    "Sentry Integration": "../ai-context/sentry.md",
    "Jira Workflows": "../ai-context/jira_commands.md",
    "Confluence Wiki": "../ai-context/confluence-wiki.md",
}


def get_repository_info(repo_name: str) -> dict:
    """Get information about a specific repository."""
    return REPOSITORIES.get(repo_name, {})


def get_all_repositories() -> dict:
    """Get all repository configurations."""
    return REPOSITORIES


def get_investigation_strategy() -> dict:
    """Get mapping of issue types to repositories."""
    return INVESTIGATION_STRATEGY
