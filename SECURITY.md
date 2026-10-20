# Security and public portfolio disclosure

This repository is an educational **demonstration**, not production trading infrastructure. The Flask server is restricted to localhost by default, has no live-exchange order execution, and does not include real brokerage authentication.

## Important: pre-cleanup Git history

During October 2026 portfolio preparation, historic tracked files included:
- An environment-like configuration file named `Key.env`.
- Pine Script source with credential-looking `api_key` / `api_secret` string literals.

The current `Main` files remove the tracked environment sample and replace the relevant credential-looking literals with *demo placeholders*. A standard `.gitignore` now excludes `.env`, `Key.env`, and other typical local secrets.

**This is a working-tree cleanup only.** Previous Git commits may still contain the original strings and remain accessible even if this repository is renamed. It has *not* been verified whether the historic strings were ever real, active credentials.

### If any historic value was ever valid

1. **Immediately revoke/rotate it** at the relevant provider (and update any consumers of that token).
2. Check provider activity logs for unauthorized use, where supported.
3. Consider a **new public repository created from a clean snapshot** or a carefully coordinated Git history rewrite using `git filter-repo`. A rewrite changes commit hashes, may break existing clones, and requires verifying all branches/tags/PR references and caches. Coordinate before force-pushing.
4. Search all Git branches and histories, not just the current worktree, for secrets. Any removed key must be considered compromised once publicly published.

### Before sharing with recruiters

- Confirm there are no real secrets in any **publicly accessible history**, or use a new clean-history repository.
- Never publish actual account, trade, wallet, or personal records.
- Keep demo mode enabled and the Flask development server bound to `127.0.0.1`.
- Never present this project as verified live trading or audited exchange integration.

## Responsible disclosure

If you discover a security issue, please avoid publishing credentials, exploit payloads, or private account data in public GitHub issues. Use the repository owner's private contact channel instead.
