#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2021 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0

import json
import os
import shutil
import time

import gitlab
import requests
from git import Git, Repo


def pr_check_approver(pr_creator, pr_comments_url, pr_approve_labeller):
    print('Checking PR comment and affixed label...')
    # Requires Github Access Token, with Push Access
    GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

    r = requests.get(pr_comments_url, headers={'Authorization': 'token ' + GITHUB_TOKEN})
    r_data = r.json()

    for comment in reversed(r_data):
        comment_body = comment['body']
        if comment_body.startswith('sha=') and comment['user']['login'] == pr_approve_labeller != pr_creator:
                return comment_body[4:]

    raise RuntimeError('PR Comment Error: Ensure that Command comment exists and PR commenter and labeller match!')


def pr_check_forbidden_files(pr_files_url):
    print('Checking if PR modified forbidden files...')
    # Requires Github Access Token, with Push Access
    GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

    r = requests.get(pr_files_url, headers={'Authorization': 'token ' + GITHUB_TOKEN})
    r_data = r.json()

    pr_files = [file_info['filename'] for file_info in r_data
                if (file_info['filename']).find('.gitlab') != -1 or (file_info['filename']).find('.github') != -1]
    if pr_files:
        raise RuntimeError('PR modifying forbidden files!!!')


def setup_project(project_html_url, repo_fullname, project_name):
    print('Connecting to GitLab...')
    GITLAB_URL = os.environ['GITLAB_URL']
    GITLAB_TOKEN = os.environ['GITLAB_TOKEN']
    GITHUB_URL = project_html_url
    GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

    gl = gitlab.Gitlab(url=GITLAB_URL, private_token=GITLAB_TOKEN)
    gl.auth()

    HDR_LEN = 8
    gh_project_url = GITHUB_URL[:HDR_LEN] + GITHUB_TOKEN + ':' + GITHUB_TOKEN + '@' + GITHUB_URL[HDR_LEN:]
    gl_project_url = GITLAB_URL[:HDR_LEN] + GITLAB_TOKEN + ':' + GITLAB_TOKEN + '@' + GITLAB_URL[HDR_LEN:] + '/' + repo_fullname + '.git'

    print('Cloning repository...')
    Git('.').clone(gh_project_url, branch='test_master', single_branch=True, recursive=True)

    git = Git(project_name)
    GITLAB_REMOTE = 'gitlab'

    print('Adding and fetching the internal remote...')
    git.remote('add', GITLAB_REMOTE, gl_project_url)
    git.pull(GITLAB_REMOTE, 'test_master')

    return gl


def check_remote_branch(project, pr_branch):
    ret = None
    for x in range(0, 15):
        try:
            ret = project.branches.get(pr_branch)
        except Exception:
            time.sleep(1)
            pass

        if ret is not None:
            return

    raise RuntimeError('PR branch creation failed!')


def check_update_label(pr_labels_list):
    LABEL_MERGE = 'PR-Sync-Merge'
    LABEL_REBASE = 'PR-Sync-Rebase'

    label_validity = [label['name'] for label in pr_labels_list if label['name'] == LABEL_MERGE or label['name'] == LABEL_REBASE]

    if not label_validity:
        raise RuntimeError('PR-Sync-Update Label: Illegal use!')


# Update existing MR
def update_mr(project_name, pr_num, pr_branch, pr_commit_id, project_gl):
    try:
        project_gl.branches.get(pr_branch)
    except:
        raise RuntimeError('PR Update: No branch found on internal remote to update!')

    GITHUB_REMOTE = 'origin'
    GITLAB_REMOTE = 'gitlab'
    git = Git(project_name)

    print('Updating the PR branch...')
    git.fetch(GITHUB_REMOTE, 'pull/' + str(pr_num) + '/head')
    git.checkout('FETCH_HEAD', b=pr_branch)

    print('Checking whether specified commit ID matches with user branch HEAD...')
    expected_commit_id = git.rev_parse('--short', 'HEAD')

    if not pr_commit_id.startswith(expected_commit_id):
        raise RuntimeError('PR Commit SHA1 in workflow comment and user branch do not match!')

    print('Pushing to remote...')
    git.push('--force', GITLAB_REMOTE, pr_branch)


# Merge PRs with/without Rebase
def sync_pr(project_name, pr_num, pr_branch, pr_commit_id, project_gl, pr_html_url, rebase_flag):
    try:
        project_gl.branches.get(pr_branch)
    except:
        pass
    else:
        raise RuntimeError('PR Merge/Rebase: Branch/MR already exists for PR!')

    GITHUB_REMOTE = 'origin'
    GITLAB_REMOTE = 'gitlab'
    git = Git(project_name)

    print('Fetching the PR branch...')
    git.fetch(GITHUB_REMOTE, 'pull/' + str(pr_num) + '/head')

    print('Checking out the PR branch...')
    git.checkout('FETCH_HEAD', b=pr_branch)

    print('Checking whether specified commit ID matches with user branch HEAD...')
    expected_commit_id = git.rev_parse('--short', 'HEAD')

    if not pr_commit_id.startswith(expected_commit_id):
        raise RuntimeError('PR Commit SHA1 in workflow comment and user branch do not match!')

    if rebase_flag:
        repo = Repo(project_name)
        repo.config_writer().set_value('user', 'name', os.environ['GIT_CONFIG_NAME']).release()
        repo.config_writer().set_value('user', 'email', os.environ['GIT_CONFIG_EMAIL']).release()

        print('Rebasing with the latest test_master...')
        git.rebase('test_master')

        commit = repo.head.commit
        new_cmt_msg = commit.message + '\nMerges ' + pr_html_url

        print('Amending commit message (Adding additional info about commit)...')
        git.execute(['git','commit', '--amend', '-m', new_cmt_msg])

    print('Pushing to remote...')
    git.push('--set-upstream', GITLAB_REMOTE, pr_branch)


def main():
    if 'GITHUB_REPOSITORY' not in os.environ:
        print('Not running in GitHub action context, nothing to do')
        return

    if not os.environ['GITHUB_REPOSITORY'].startswith('espressif/'):
        print('Not an Espressif repo!')
        return

    # The path of the file with the complete webhook event payload. For example, /github/workflow/event.json.
    with open(os.environ['GITHUB_EVENT_PATH'], 'r') as f:
        event = json.load(f)

    LABEL_MERGE = 'PR-Sync-Merge'
    LABEL_REBASE = 'PR-Sync-Rebase'
    LABEL_UPDATE = 'PR-Sync-Update'

    pr_label = event['label']['name']
    pr_labels_list = event['pull_request']['labels']

    pr_approve_labeller = event['sender']['login']
    pr_creator = event['pull_request']['user']['login']
    pr_comments_url = event['pull_request']['comments_url']
    # Checks whether the approve labeller and workflow initiator are the same
    pr_commit_id = pr_check_approver(pr_creator, pr_comments_url, pr_approve_labeller)

    repo_fullname = event['repository']['full_name']
    project_name = repo_fullname.split('/')[1]
    project_html_url = event['repository']['clone_url']

    pr_num = event['pull_request']['number']
    pr_branch = 'contrib/github_pr_' + str(pr_num)
    pr_rest_url = event['pull_request']['url']
    pr_html_url = event['pull_request']['html_url']

    pr_files_url = pr_rest_url + '/files'
    # Check whether the PR has modified forbidden files
    pr_check_forbidden_files(pr_files_url)

    # Getting the PR title and body
    pr_title = event['pull_request']['title']
    idx = pr_title.find(os.environ['JIRA_PROJECT'])  # Finding the JIRA issue tag
    pr_title_desc = pr_title[0:idx - 2] + ' (GitHub PR)'
    pr_jira_issue = pr_title[idx:-1]
    pr_body = event['pull_request']['body']

    # NOTE: Modified for testing purpose
    repo_fullname = 'app-frameworks/actions-internal-test'

    # Gitlab setup and cloning internal codebase
    gl = setup_project(project_html_url, repo_fullname, project_name)
    project_gl = gl.projects.get(repo_fullname)

    if pr_label == LABEL_REBASE:
        sync_pr(project_name, pr_num, pr_branch, pr_commit_id, project_gl, pr_html_url, rebase_flag=True)
    elif pr_label == LABEL_MERGE:
        sync_pr(project_name, pr_num, pr_branch, pr_commit_id, project_gl, pr_html_url, rebase_flag=False)
    elif pr_label == LABEL_UPDATE:
        check_update_label(pr_labels_list)
        update_mr(project_name, pr_num, pr_branch, pr_commit_id, project_gl)
        print('Done with the workflow!')
        return
    else:
        raise RuntimeError('Illegal program flow!')

    # Deleting local repo
    shutil.rmtree(project_name)

    # NOTE: Remote takes some time to register a branch
    time.sleep(15)

    print('Creating a merge request...')
    mr = project_gl.mergerequests.create({'source_branch': pr_branch, 'target_branch': 'test_master', 'title': pr_title_desc})

    print('Updating merge request description...')
    mr_desc = '## Description \n' + pr_body + '\n ##### (Add more info here)' + '\n## Related'
    mr_desc += '\n* Closes ' + pr_jira_issue
    mr_desc += '\n* Merges ' + pr_html_url
    mr_desc += '\n## Release notes (Mandatory)\n ### To-be-added'

    mr.description = mr_desc
    mr.save()

    print('Done with the workflow!')


if __name__ == '__main__':
    main()
