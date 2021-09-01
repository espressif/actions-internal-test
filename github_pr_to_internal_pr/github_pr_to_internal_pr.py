#!/usr/bin/env python3
#
# Copyright 2021 Espressif Systems (Shanghai) PTE LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import json
import os
import shutil
import time

import gitlab
import requests
from git import Git, Repo

def pr_download_patch(pr_patch_url):
    print('Downloading patch for PR...')
    data = requests.get(pr_patch_url)
    
    f = open('esp-idf/diff.patch', 'wb')
    f.write(data.content)
    f.close()


def pr_check_forbidden_files(pr_files_url):
    r = requests.get(pr_files_url)
    r_data = r.json()
    
    pr_files = [file_info['filename'] for file_info in r_data
                if (file_info['filename']).find('.gitlab') != -1 or (file_info['filename']).find('.github') != -1]
    if pr_files:
        raise SystemError('PR modifying forbidden files!!!')


def pr_check_approver_access(project_name, pr_approver):
    # TODO: Requires Github Access Token, with Push Access
    GITHUB_TOKEN = os.environ['GITHUB_TOKEN']

    r = requests.get('https://api.github.com/repos/' + project_name + '/collaborators', headers={'Authorization': 'token ' + GITHUB_TOKEN})
    r_data = r.json()

    pr_appr_perm = [usr for usr in r_data if usr['login'] == pr_approver][0]['permissions']
    if not pr_appr_perm['triage']:
        raise SystemError('PR Approver Access is below TRIAGE level!')


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
        print(json.dumps(event, indent=4))

    event_name = os.environ['GITHUB_EVENT_NAME']  # The name of the webhook event that triggered the workflow.
    action = event["action"]
    state = event["review"]["state"]

    if event_name != 'pull_request_review' or state != 'commented':
        raise SystemError("False Trigger!")

    pr_base = event["pull_request"]["base"]["ref"]
    if pr_base != 'master':
        raise SystemError("PR base illegal! Should be the master branch!")
    
    project_name = event["repository"]["full_name"]
    pr_num = event["pull_request"]["number"]
    pr_branch = 'contrib/github_pr_' + str(pr_num)
    
    pr_files_url = event["pull_request"]["url"] + '/files'
    # Check whether the PR has modified forbidden files
    pr_check_forbidden_files(pr_files_url)

    # pr_approver = event["review"]["user"]["login"]
    # # Checks whether the approver access level is above required; needs Github access token
    # pr_check_approver_access(project_name, pr_approver)

    # # Getting the PR title
    # pr_title = event["pull_request"]["title"]
    # idx = pr_title.find(os.environ['JIRA_PROJECT']) # Finding the JIRA issue tag
    # pr_title_desc = pr_title[0 : idx - 2] # For space character
    # pr_jira_issue = pr_title[idx : -1]

    # # Getting the PR body and URL
    # pr_body = event["pull_request"]["body"]
    # pr_url = event["pull_request"]["html_url"]

    # pr_patch_url = event["pull_request"]["patch_url"]
    # # Download the patch for the given PR
    # pr_download_patch(pr_patch_url)

    # # TODO: Add Gitlab private token and URL as an encrypted secret
    # print('Connecting to gitlab...')
    # gl_url = os.environ['GITLAB_URL']
    # GITLAB_TOKEN = os.environ['GITLAB_TOKEN']

    # gl = gitlab.Gitlab(url=gl_url, private_token=GITLAB_TOKEN)
    # gl.auth()

    # HDR_LEN = 8
    # gl_project_url = gl_url[: HDR_LEN] + GITLAB_TOKEN + ':' + GITLAB_TOKEN + '@' + gl_url[HDR_LEN :] + '/' + project_name + '.git'
    # print(Git(".").clone(gl_project_url))

    # idf = 'esp-idf'
    # git = Git(idf)
    # repo = Repo(idf)

    # # TODO: Set the config parameters: Better be a espressif bot
    # repo.config_writer().set_value('user', 'name', os.environ['GIT_CONFIG_NAME']).release()
    # repo.config_writer().set_value('user', 'email', os.environ['GIT_CONFIG_EMAIL']).release()

    # # Following is the rebase approach for old PRs
    # # TODO: Enable merging PR without rebase for new commits

    # print('Checking out to master branch...')
    # print(git.checkout('master'))

    # print('Pulling the latest changes...')
    # print(git.pull('origin','master'))

    # print('Updating submodules...')
    # print(git.submodule('update', '--init', '--recursive'))

    # print('Checking out to new branch for contribution...')
    # print(git.checkout('HEAD', b=pr_branch))

    # print('Applying patch...')
    # print(git.execute(['git','am', '--signoff', 'diff.patch']))

    # commit = repo.head.commit
    # new_cmt_msg = commit.message + '\nCloses ' + pr_url

    # print('Amending commit message (Adding additional info about commit)...')
    # print(git.execute(['git','commit', '--amend', '-m', new_cmt_msg]))

    # print('Pushing to remote...')
    # print(git.push('--set-upstream', 'origin', pr_branch))

    # # Deleting local repo
    # shutil.rmtree(idf)

    # # NOTE: Remote takes some time to register a branch
    # time.sleep(30)

    # print('Creating a merge request...')
    # project_gl = gl.projects.get(project_name)
    # mr = project_gl.mergerequests.create({'source_branch': pr_branch, 'target_branch': 'master', 'title': pr_title_desc})

    # print('Updating merge request description...')
    # mr_desc = pr_body + '\n(Add more info here)' + '\n## Related'
    # mr_desc +=  '\n* Closes ' + pr_jira_issue
    # mr_desc += '\n## Release notes (Mandatory)\n ### To-be-added'

    # mr.description = mr_desc
    # mr.save()

    # print('Done with the merge request!')


if __name__ == '__main__':
    main()