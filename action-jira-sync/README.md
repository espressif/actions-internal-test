# GitHub to JIRA Issue Sync

This is a GitHub action that performs simple one way syncing of GitHub issues into JIRA.

* New issues in GitHub are created in JIRA
* Updates to GitHub issues, new comments, etc also update JIRA.

(Note: Apart from creating and editing the GitHub issue itself, all other GitHub events only result in a new comment in the JIRA issue.)

A JIRA project is configured where new issues will be created. A JIRA custom URL field named "GitHub Reference" must be exist in this project, and is used to link the JIRA issue to the GitHub issue.

The sync action will continue to update JIRA issues which are moved to other JIRA projects, provided the "GitHub Reference" field is present in the other JIRA project as well.

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
