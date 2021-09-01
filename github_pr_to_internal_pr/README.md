# GitHub PR to Internal Codebase Sync

This script automates the process of creating branches and PRs on the internal codebase of Espressif based on approved PRs on Github.

## Flow

1. Get the PR information and perform the necessary checks (forbidden files, approver access level, etc) 
2. Download patch from Github PR (e.g. #yyyy)
3. Checkout a new branch from master after pulling the latest changes
4. Apply the patch and amending the commit message (for internal tracking)
5. Push the branch to the internal remote
6. Open a new MR with appropriate description (General Description, Related, Release Notes)