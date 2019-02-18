workflow "Sync issues to JIRA" {
  on = "issues"
  resolves = ["./action-jira-sync"]
}

action "./action-jira-sync" {
  uses = "./action-jira-sync"
  secrets = ["GITHUB_TOKEN", "JIRA_USER", "JIRA_PASS"]
}
