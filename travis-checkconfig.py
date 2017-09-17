#! /usr/bin/env python
# This script, to be run by travis, reads lib/config.json and generates
# dummy passwords file so that checkconfig does not complain.

import os
import json

# Create secrets directory
SECRETS_DIR=environ['SECRETS_DIR']
if not os.path.exists(SECRETS_DIR):
    os.makedirs(SECRETS_DIR)

# Create passwords file
with open('lib/config.json') as conf:
    data = json.load(conf)

dummy_pass = 'TESTING_PASS'
passwords = dict()

for w in data['workers']:
    name = w['name']
    passwords[name] = dummy_pass

if not os.path.exists('lib/passwords.json'):
    with open('lib/passwords.json', 'w') as passfile:
        json.dump(passwords, passfile)
    print('Done.')
else:
    print('Nothing done. lib/passwords.json already exists')
