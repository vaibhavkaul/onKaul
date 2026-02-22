#!/usr/bin/env python3
"""Test PR review flow end-to-end."""

from tools.pr_review import extract_pr_url, post_pr_review_comment, review_github_pr

# Test URL
test_message = "@onkaul review https://github.com/taptapsend/appian-frontend/pull/3179"

print("=" * 80)
print("Testing PR Review Flow")
print("=" * 80)

# 1. Extract URL
pr_url = extract_pr_url(test_message)
print(f"1. Extracted URL: {pr_url}")

# 2. Fetch PR data
print("\n2. Fetching PR data...")
pr_data = review_github_pr(pr_url)
print(f"   Title: {pr_data.get('title')}")
print(f"   Author: {pr_data.get('author')}")
print(f"   Diff: {len(pr_data.get('diff', ''))} chars")

# 3. Build review request
review_request = f"""Please review this Pull Request:

**PR #{pr_data['pr_number']}**: {pr_data['title']}
**Author**: {pr_data['author']}
**Repository**: {pr_data['repository']}

**Description:**
{pr_data['description'][:500]}

**Changes:**
```diff
{pr_data['diff'][:2000]}
```

Provide a comprehensive code review with 4 priority levels."""

print(f"\n3. Review request built ({len(review_request)} chars)")

# 4. Agent review (would use Opus)
print("\n4. Would call agent.investigate() with Opus...")
print("   (Skipping actual API call for test)")

# Mock review for testing
mock_review = """## 🤖 onKaul PR Review

### ⚠️ High Priority
None found - changes look safe

### 📋 Medium Priority
1. Consider adding test coverage for the new logic

### ✨ Nice to Have
1. Extract magic number to constant

### 🔍 Nits
1. Minor: Spacing in imports"""

# 5. Post to GitHub
print("\n5. Posting review to GitHub...")
post_result = post_pr_review_comment(pr_url, mock_review)
print(f"   Success: {post_result.get('success')}")
print(f"   Comment URL: {post_result.get('comment_url')}")

# 6. Generate summary
print("\n6. Generating summary...")
summary = f"""✅ **PR Review Complete**

**PR #{pr_data['pr_number']}**: {pr_data['title']}

**Summary:**
- ⚠️ High Priority: 0 issues
- 📋 Medium Priority: 1 issue
- ✨ Nice to Have: 1 suggestion
- 🔍 Nits: 1 item

🔗 Full review: {post_result.get('comment_url')}"""

print(summary)
print("\n7. Would post this summary to Slack/Jira")

print("\n" + "=" * 80)
print("✅ PR Review Flow Complete!")
print("=" * 80)
