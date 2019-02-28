#!/usr/bin/env python3
from jira import JIRA
from github import Github
import pprint
import json
import os
import re
import subprocess
import tempfile


def main():
    with open(os.environ['GITHUB_EVENT_PATH'], 'r') as f:
        event = json.load(f)
        pprint.pprint(event)

        print('Connecting to JIRA...')
        jira = JIRA(os.environ['JIRA_URL'],
                    basic_auth=(os.environ['JIRA_USER'],
                                os.environ['JIRA_PASS']))

        action = event["action"]

        if os.environ['GITHUB_EVENT_NAME'] == 'issues':
            action_handlers = {
                'opened': handle_issue_opened,
                'edited': handle_issue_edited,
                'closed': handle_issue_closed,
                'deleted': handle_issue_deleted,
                'reopened': handle_issue_reopened,
            }
        elif os.environ['GITHUB_EVENT_NAME'] == 'issue_comment':
            action_handlers = {
                'created': handle_comment_created,
                'edited': handle_comment_edited,
                'deleted': handle_comment_deleted,
            }
        if action in action_handlers:
            action_handlers[action](jira, event)
        else:
            print("No handler for issues action '%s'. Skipping." % action)


def handle_issue_opened(jira, event):
    _create_jira_issue(jira, event["issue"])


def handle_issue_edited(jira, event):
    gh_issue = event["issue"]
    issue = _find_jira_issue(jira, gh_issue, True)

    issue.update(fields={
        "description": _get_description(gh_issue),
        "summary": _get_summary(gh_issue)
    })

    _leave_jira_issue_comment(jira, event, "edited", True, jira_issue=issue)


def handle_issue_closed(jira, event):
    # note: Not auto-closing the synced JIRA issue because GitHub
    # issues often get closed for the wrong reasons - ie the user
    # found a workaround but the root cause still exists.
    _leave_jira_issue_comment(jira, event, "closed", False)


def handle_issue_deleted(jira, event):
    _leave_jira_issue_comment(jira, event, "deleted", False)


def handle_issue_reopened(jira, event):
    _leave_jira_issue_comment(jira, event, "reopened", True)


def _leave_jira_issue_comment(jira, event, verb, should_create,
                              jira_issue=None):
    """
    Leave a simple comment that the GitHub issue corresponding to this event was 'verb' by the GitHub user in question.

    If should_create is set then a JIRA issue will be opened if it doesn't exist.

    If jira_issue is set then this JIRA issue will be updated, otherwise the function will find the corresponding synced issue.
    """
    gh_issue = event["issue"]
    if jira_issue is None:
        jira_issue = _find_jira_issue(jira, event["issue"], should_create)
        if jira_issue is None:
            return
    jira.add_comment(jira_issue.id, "The [GitHub issue|%s] has been %s by @%s" % (gh_issue["html_url"], verb, gh_issue["user"]["login"]))


def _get_jira_comment_body(gh_comment, body=None):
    if body is None:
        body = _markdown2wiki(gh_comment["body"])
    return "[GitHub issue comment|%s] by @%s:\n\n%s" % (gh_comment["html_url"], gh_comment["user"]["login"], body)

def handle_comment_created(jira, event):
    gh_comment = event["comment"]

    jira_issue = _find_jira_issue(jira, event["issue"], True)
    jira.add_comment(jira_issue.id, _get_jira_comment_body(gh_comment))


def handle_comment_edited(jira, event):
    gh_comment = event["comment"]
    old_gh_body = _markdown2wiki(event["changes"]["body"]["from"])

    jira_issue = _find_jira_issue(jira, event["issue"], True)

    # Look for the old comment and update it if we find it
    old_jira_body = _get_jira_comment_body(gh_comment, old_gh_body)
    found = False
    for comment in jira.comments(jira_issue.key):
        if comment.body == old_jira_body:
            comment.update(body=_get_jira_comment_body(gh_comment))
            found = True
            break

    if not found:  # if we didn't find the old comment, make a new comment about the edit
        jira.add_comment(jira_issue.id, _get_jira_comment_body(gh_comment))


def handle_comment_deleted(jira, event):
    gh_comment = event["comment"]
    jira_issue = _find_jira_issue(jira, event["issue"], True)
    jira.add_comment(jira_issue.id, "@%s deleted their [GitHub issue comment|%s]" % (gh_comment["user"]["login"], gh_comment["html_url"]))


def _markdown2wiki(markdown):
    """
    Convert markdown to JIRA wiki format. Uses https://github.com/chunpu/markdown2confluence
    """
    with tempfile.NamedTemporaryFile('w+') as mdf:  # note: this won't work on Windows
        mdf.write(markdown)
        if not markdown.endswith('\n'):
            mdf.write('\n')
        mdf.flush()
        try:
            wiki = subprocess.check_output(['markdown2confluence', mdf.name])
            return wiki.decode('utf-8', errors='ignore')
        except subprocess.CalledProcessError as e:
            print("Failed to run markdown2confluence: %s. JIRA issue will have raw Markdown contents." % e)
            return markdown


def _get_description(gh_issue):
    return """%(github_url)s

    Opened by GitHub user @%(github_user)s:

    %(github_description)s

    ---

    Notes:

    * Do not edit this description text, it may be updated automatically.
    * Please interact on GitHub where possible, changes will sync to here.
    * If closing this issue from a commit, please add
      {code}
      Closes %(github_url)s
      {code}
      in the commit message so the commit is closed on GitHub automatically.
    """ % {
        "github_url": gh_issue["html_url"],
        "github_user": gh_issue["user"]["login"],
        "github_description": _markdown2wiki(gh_issue["body"]),
    }


def _get_summary(gh_issue):
    result = "GH #%d: %s" % (gh_issue["number"], gh_issue["title"])

    # don't mirror any existing JIRA slug-like pattern from GH title to JIRA summary
    # (note we don't look for a particular pattern as the JIRA issue may have moved)
    result = re.sub(r" \([\w]+-[\d]+\)", "", result)

    return result


def _create_jira_issue(jira, gh_issue):
    # get the custom field ID for 'GitHub Reference' on this instance
    try:
        github_reference_id = [f['id'] for f in jira.fields() if f["name"] == "GitHub Reference" ][0]
    except IndexError:
        raise RuntimeError("Custom field 'GitHub Reference' is not configured on this JIRA instance")

    fields = {
        "summary": _get_summary(gh_issue),
        "project": os.environ['JIRA_PROJECT'],
        "description": _get_description(gh_issue),
        "issuetype": os.environ.get('JIRA_ISSUE_TYPE', 'Task'),
        github_reference_id: gh_issue["html_url"]
    }
    issue = jira.create_issue(fields)

    # append the new JIRA slug to the GitHub issue
    # (updates made by github actions don't trigger new actions)
    github = Github(os.environ["GITHUB_TOKEN"])

    # note: github also gives us 'repository' JSON which has a 'full_name', but this is simpler
    # for the API structure.
    repo_name = re.search(r'[^/]+/[^/]+$', gh_issue["repository_url"]).group(0)
    repo = github.get_repo(repo_name)

    api_gh_issue = repo.get_issue(gh_issue["number"])
    api_gh_issue.edit(title="%s (%s)" % (api_gh_issue.title, issue.key))

    return issue


def _find_jira_issue(jira, gh_issue, make_new=False):
    url = gh_issue["html_url"]
    r = jira.search_issues('"GitHub Reference" = "%s"' % (url))
    if len(r) == 0:
        print("WARNING: GitHub issue '%s' not found in JIRA." % url)
        if not make_new:
            return None
        else:
            return _create_jira_issue(jira, gh_issue)
    if len(r) > 1:
        print("WARNING: GitHub reference '%s' returns multiple JIRA issues. Returning the first one only." % url)
    return r[0]


if __name__ == "__main__":
    main()
