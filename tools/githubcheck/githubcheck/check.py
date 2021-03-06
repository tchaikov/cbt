#!/usr/bin/env python3

import datetime
import logging
import sys

import github3
import github3.exceptions

log = logging.getLogger("cephacheck.check")


class UTC(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)


utc = UTC()


class Check:
    def __init__(self, owner, project, context, pem, app_id, install_id):
        self.owner = owner
        self.project = project
        self.context = context
        self.github = github3.GitHub()
        self.github.login_as_app_installation(pem, app_id, install_id)

    def start(self, sha, status, output=None, details_url=None):
        repo = self.github.repository(self.owner, self.project)
        started_at = datetime.datetime.now(utc).isoformat()
        if output is None:
            output = {'title': 'Summary',
                      'summary': 'started',
                      'text': 'details'}
        try:
            check_run = repo.create_check_run(
                name=self.context,
                head_sha=sha,
                status=status,
                started_at=started_at,
                output=output,
                details_url=details_url,
            )
        except github3.exceptions.GitHubException as e:
            log.error(f"failed to create check run {self.context} for #{sha}:"
                      f" {e}")

    # conclusion: string: one of
    #   success, failure, neutral, cancelled, skipped, timed_out, or
    #   action_required
    #   see https://developer.github.com/v3/checks/runs/#create-a-check-run
    # output: dict
    #   see https://developer.github.com/v3/checks/runs/#output-object
    def complete(self, sha, conclusion, output, details_url=None):
        repo = self.github.repository(self.owner, self.project)
        status = 'completed'
        completed_at = datetime.datetime.now(utc).isoformat()
        try:
            check_run = next(c for c in repo.commit(sha).check_runs()
                             if c.name == self.context)
        except github3.exceptions.GitHubException as e:
            log.error(f"could not retrieve existing check runs for #{sha}:"
                      f" {e}")
        except StopIteration:
            # create a new one
            log.debug(f"could not find existing check runs {self.context} for "
                      f"#{sha}, creating a new one")
            try:
                check_run = repo.create_check_run(
                    name=self.context,
                    head_sha=sha,
                    status=status,
                    conclusion=conclusion,
                    completed_at=completed_at,
                    output=output,
                    details_url=details_url,
                )
            except github3.exceptions.GitHubException as e:
                log.error(f"failed to create check run {self.context} for "
                          f"#{sha}: {e}")
        else:
            # update an existing one
            log.debug(f"updating existing check run {self.context} for #{sha} "
                      f"with status {status}")
            try:
                check_run.update(
                    status=status,
                    conclusion=conclusion,
                    completed_at=completed_at,
                    output=output,
                    details_url=details_url,
                )
            except github3.exceptions.GitHubException as e:
                log.error(f"failed to update check run {self.context} for "
                          f"#{sha}: {e}")

