#!/usr/bin/env python3
import pprint
import json
import os

def main():
    with open(os.env['GITHUB_EVENT_PATH'], 'r') as f:
        event = json.load(f)
        pprint.pprint(event)

if __name__ == "__main__":
    main()
