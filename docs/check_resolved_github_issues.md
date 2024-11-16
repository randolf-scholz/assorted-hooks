# check-resolved-github-issues

Checks code for references to GitHub issues. Queries the GitHub API to check if the issues are resolved.

**Note:** Currently this hook is rather slow because the queries are not running asynchronously.

## Additional Arguments

- `--ignore-comments`: Ignore urls that point to comments in issues rather than the issue itself. (default: `True`)
- `--prefix`: Regex pattern that must be present in the url for the hook to check the issue. (default: `FIXME:\s*`)
