# GitHub to JIRA Issue Sync

This is a GitHub action that performs simple one way syncing of GitHub issues into JIRA.

* When a new GitHub issue is opened
  - A corresponding JIRA issue (in the configured JIRA project) is created.
  - Markdown in the GitHub issue body is converted into JIRA Wiki format (thanks to [markdown2confluence](http://chunpu.github.io/markdown2confluence/browser/))
  - A JIRA custom field "GitHub Reference" is set to the URL of the issue
  - The GitHub issue title has `(JIRA SLUG)` appended to it.
* When a GitHub issue is edited, the summary and description of the JIRA issue are updated.
* When someone comments on the GitHub issue, a comment is created on the JIRA issue.
* When GitHub comments are edited or deleted, or the issue is closed or deleted, a comment is created on the JIRA issue.

Note: Closing the GitHub issue does not cause any transition in the JIRA issue. This is deliberate as sometimes GitHub issues are closed for different reasons (ie reporter decides "Works for me!").

# Sync Linkage

The JIRA custom URL field named "GitHub Reference" must exist in the configured JIRA project. It is used to link the JIRA issue to the GitHub issue.

The sync action will continue to update JIRA issues which are moved to other JIRA projects, provided the "GitHub Reference" field is moved to the other JIRA project as well.

# Variables

The environment variables should be set in the GitHub Workflow:

* `JIRA_PROJECT` is the slug of the JIRA project to create new issues in.
* `JIRA_ISSUE_TYPE` (optional) the JIRA issue type for new issues to be created with. If not set, "Task" is used.

The following secrets should be set in the workflow:

* `JIRA_URL` is the main JIRA URL (doesn't have to be secret).
* `JIRA_USER` is the JIRA username to log in with (JIRA basic auth)
* `JIRA_PASS` is the JIRA password to log in with (JIRA basic auth)

# Tests

test_sync_issue.py is a Python unittest framework that uses unittest.mock to create a mock JIRA API, then calls unit_test.py with various combinations of payloads similar to real GitHub Actions payloads.

The best way to run the tests is in the docker container, as this is the same environment that GitHub will run real actions in.

## Build image and run tests in a temporary container:

```
docker build . --tag jira-sync && docker run --rm --name jira-sync --entrypoint=/test_sync_issue.py jira-sync
```

## Rebuild container and run tests multiple times

(This is a bit faster than rebuilding the image each time.)

Build the image and run the container once:

```
docker build . --tag jira-sync
docker run -td --entrypoint=/bin/sh --name jira-sync
```

For each test run, copy the Python files to the running container and run the test program:

```
docker cp . jira-sync:/ && docker exec jira-sync /test_sync_issue.py
```

Once finished, kill the container:

```
docker stop -t1 jira-sync
```


## Cleanup

To clean up container and container image:

```
docker rm jira-sync
docker rmi jira-sync
```
