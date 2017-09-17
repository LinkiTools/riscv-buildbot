import re
import os
from buildbot.plugins import *

@util.renderer
def fetch_dejagnu_results(props):
    testsuitedir = os.path.join(props.getProperty('builddir'), 'gcc', 'testsuite')

    SUMS = ['gcc', 'g++', 'objc', 'gfortran']
    sumfiles = map(lambda s: (s, os.path.join(testsuitedir, s, '.'.join([s, 'sum']))),
                   SUMS)

    properties = {}

    rexp = re.compile(r"""
    ^
    [#]\s+of\s+
    (((un)?expected) | unresolved)
    \s+
    (passes | failures | successes | testcases | tests)
    \s+
    ([0-9]+)
    \s*
    $
    """, re.VERBOSE)
    for (s, path) in sumfiles:
        if not os.path.exists(path):
            continue

        with open(path, 'r') as f:
            for line in f:
                m = rexp.match(line)
                if m:
                    n1, n2, ntests = m.group(1, 4, 5)
                    result = ' '.join([n1, n2])
                    properties['{} {}'.format(s, result)] = int(ntests)

    return properties
