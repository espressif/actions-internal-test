workflow "Sync issues to JIRA" {
  on = "issues"
  resolves = ["./action-jira-sync"]
}

workflow "Sync issue comments to JIRA" {
  on = "issue_comment"
  resolves = ["./action-jira-sync"]
}

action "./action-jira-sync" {
  uses = "./action-jira-sync"
  secrets = ["GITHUB_TOKEN", "JIRA_URL", "JIRA_USER", "JIRA_PASS"]
  env = {
    JIRA_PROJECT = "IDFSYNTEST"
  }
}
