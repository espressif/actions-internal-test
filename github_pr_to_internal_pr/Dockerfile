FROM node:current-buster-slim

LABEL "com.github.actions.name"="GitHub PR to Internal Codebase Sync"
LABEL "com.github.actions.description"="Sync approved Github PRs to the internal codebasevv"
LABEL "com.github.actions.icon"="fast-forward"
LABEL "com.github.actions.color"="green"

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8

ADD requirements.txt /tmp/requirements.txt

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git && \
    apt-get install -y python3-pip && \
    pip3 install -r /tmp/requirements.txt

RUN rm /tmp/requirements.txt

ADD github_pr_to_internal_pr.py /github_pr_to_internal_pr.py

ENTRYPOINT ["/usr/bin/python3", "/github_pr_to_internal_pr.py"]