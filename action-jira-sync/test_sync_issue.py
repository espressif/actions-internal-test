#!/usr/bin/env python3
import jira
import json
import sync_issue
import os
import unittest
import unittest.mock
from unittest.mock import create_autospec
import tempfile

# mock custom field ID for the 'GitHub Reference' field
MOCK_GITHUB_REFERENCE_ID = "custom_field_111111"

def run_sync_issue(event_name, event, jira_issue=None):
    """
    Run the 'sync_issue' main() function with supplied event (as Python dict), event name, and mocked JIRA PAI.

    If jira_issue is not None, this JIRA issue object will be
    returned as the only result of a call to JIRA.search_issues().
    """
    try:
        # dump the event data to a JSON file
        event_file = tempfile.NamedTemporaryFile('w+', delete=False)
        json.dump(event, event_file)
        event_file.close()

        os.environ['GITHUB_EVENT_NAME'] = event_name
        os.environ['GITHUB_EVENT_PATH'] = event_file.name

        os.environ['JIRA_PROJECT'] = 'TEST'
        os.environ['JIRA_URL'] = 'https://test.test:88/'
        os.environ['JIRA_USER'] = 'test_user'
        os.environ['JIRA_PASS'] = 'test_pass'

        jira_class = create_autospec(jira.JIRA)

        # fake a fields() response with all fields in instance
        jira_class.return_value.fields.return_value = [
            { "id": MOCK_GITHUB_REFERENCE_ID,
              "name": "GitHub Reference" }
            ]

        if jira_issue is not None:
            jira_class.return_value.search_issues.return_value = [jira_issue]
        else:
            jira_class.return_value.search_issues.return_value = []

        sync_issue.JIRA = jira_class
        sync_issue.main()

        return jira_class.return_value  # mock JIRA object

    finally:
        os.unlink(event_file.name)


class TestIssuesEvents(unittest.TestCase):

    def test_issue_opened(self):
        issue = {"html_url": "https://github.com/fake/fake/issues/3",
                 "number": 3,
                 "title": "Test issue",
                 "body": "I am a new test issue\nabc\n\n",
                 "user": {"login": "testuser"},
                 }
        event = {"action": "opened",
                 "issue": issue
                 }

        m_jira = run_sync_issue('issues', event)

        # Check that create_issue() was called with fields param resembling the GH issue
        fields = m_jira.create_issue.call_args[0][0]
        self.assertIn(issue["title"], fields["summary"])
        self.assertIn(issue["body"], fields["description"])
        self.assertIn(issue["html_url"], fields["description"])
        self.assertEqual(issue["html_url"], fields[MOCK_GITHUB_REFERENCE_ID])

    def test_issue_closed(self):
        self._test_issue_simple_comment("closed")

    def test_issue_deleted(self):
        self._test_issue_simple_comment("deleted")

    def test_issue_reopened(self):
        self._test_issue_simple_comment("deleted")

    def test_issue_edited(self):
        issue = {"html_url": "https://github.com/fake/fake/issues/11",
                 "number": 11,
                 "title": "Edited issue",
                 "body": "Edited issue content goes here",
                 "user": {"login": "edituser"},
                 }

        m_jira = self._test_issue_simple_comment("edited", issue)

        # check the update resembles the edited issue
        m_issue = m_jira.search_issues.return_value[0]

        update_args = m_issue.update.call_args[1]
        self.assertIn("description", update_args["fields"])
        self.assertIn("summary", update_args["fields"])
        self.assertIn(issue["title"], update_args["fields"]["summary"])

    def _test_issue_simple_comment(self, action, gh_issue=None):
        """
        Wrapper for the simple case of updating an issue (with 'action'). GitHub issue fields can be supplied, or generic ones will be used.
        """
        if gh_issue is None:
            gh_number = hash(action) % 43
            gh_issue = {"html_url": "https://github.com/fake/fake/issues/%d" % gh_number,
                        "number": gh_number,
                        "title": "Test issue",
                        "body": "I am a test issue\nabc\n\n",
                        "user": {"login": "otheruser"},
                        }
        event = {"action": action,
                 "issue": gh_issue
                 }

        m_issue = create_autospec(jira.Issue)(None, None)
        jira_id = hash(action) % 1001
        m_issue.id = jira_id

        m_jira = run_sync_issue('issues', event, m_issue)

        # expect JIRA API added a comment about the action
        comment_jira_id, comment = m_jira.add_comment.call_args[0]
        self.assertEqual(jira_id, comment_jira_id)
        self.assertIn(gh_issue["user"]["login"], comment)
        self.assertIn(action, comment)

        return m_jira


class TestIssueCommentEvents(unittest.TestCase):

    def test_issue_comment_created(self):
        self._test_issue_comment("created")

    def test_issue_comment_deleted(self):
        self._test_issue_comment("deleted")

    def test_issue_comment_edited(self):
        self._test_issue_comment("edited")

    def _test_issue_comment(self, action, gh_issue=None, gh_comment=None):
        """
        Wrapper for the simple case of an issue comment event (with 'action'). GitHub issue and comment fields can be supplied, or generic ones will be used.
        """
        if gh_issue is None:
            gh_number = hash(action) % 50
            gh_issue = {"html_url": "https://github.com/fake/fake/issues/%d" % gh_number,
                        "number": gh_number,
                        "title": "Test issue",
                        "body": "I am a test issue\nabc\n\n",
                        "user": {"login": "otheruser"},
                        }
        if gh_comment is None:
            gh_comment_id = hash(action) % 404
            gh_comment = {"html_url": gh_issue["html_url"] + "#" + str(gh_comment_id),
                          "id": gh_comment_id,
                          "user": {"login": "commentuser"},
                          "body": "ZOMG a comment!"
                          }
        event = {"action": action,
                 "issue": gh_issue,
                 "comment": gh_comment
                 }

        m_issue = create_autospec(jira.Issue)(None, None)
        jira_id = hash(action) % 1003
        m_issue.id = jira_id

        m_jira = run_sync_issue('issue_comment', event, m_issue)

        # expect JIRA API added a comment about the action
        comment_jira_id, comment = m_jira.add_comment.call_args[0]
        self.assertEqual(jira_id, comment_jira_id)
        self.assertIn(gh_comment["user"]["login"], comment)
        self.assertIn(gh_comment["html_url"], comment)
        if action != "created":
            self.assertIn(action, comment)

        return m_jira


if __name__ == '__main__':
    unittest.main()
