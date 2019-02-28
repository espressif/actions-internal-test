#!/usr/bin/env python3
from jira import JIRA
import pprint
import json
import os
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
    }, notify=False)

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
    jira.add_comment(jira_issue.id, "The [GitHub issue|%s] has been %s by @%s" % (gh_issue["url"], verb, gh_issue["user"]["login"]))


def handle_comment_created(jira, event):
    gh_comment = event["comment"]
    jira_issue = _find_jira_issue(jira, event["issue"], True)
    jira.add_comment(jira_issue.id, "New [GitHub issue comment|%s] by @%s" % (gh_comment["html_url"], gh_comment["user"]["login"]))


def handle_comment_edited(jira, event):
    gh_comment = event["comment"]
    jira_issue = _find_jira_issue(jira, event["issue"], True)
    jira.add_comment(jira_issue.id, "@%s edited their [GitHub issue comment|%s]" % (gh_comment["user"]["login"], gh_comment["html_url"]))


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
      in the commit message so the commit is linked on GitHub automatically.
    """ % {
        "github_url": gh_issue["url"],
        "github_user": gh_issue["user"]["login"],
        "github_description": _markdown2wiki(gh_issue["body"]),
    }


def _get_summary(gh_issue):
    return "GitHub #%d: %s" % (gh_issue["number"], gh_issue["title"])


def _create_jira_issue(jira, gh_issue):
    fields = {
        "summary": _get_summary(gh_issue),
        "project": os.environ['JIRA_PROJECT'],
        "description": _get_description(gh_issue),
        "issuetype": os.environ.get('JIRA_ISSUE_TYPE', 'Task'),
    }
    issue = jira.create_issue(fields)
    issue.update(fields={"GitHub Reference": gh_issue["url"]})


def _find_jira_issue(jira, gh_issue, make_new=False):
    url = gh_issue["url"]
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
