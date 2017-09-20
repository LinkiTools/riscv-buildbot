import os
import re

def extract_properties_jv(rc, stdout, stderr):
    """Extracts properties from jamais-vu output in stdout
    iff jv succeeds."""
    if rc != 0:
        return

    properties = dict()
    current_group = None
    group_regexp = re.compile('^(/.+)\.sum$')
    result_regexp = re.compile('^ (FAIL|PASS|XFAIL|KFAIL|XPASS|KPASS|UNTESTED|UNRESOLVED|UNSUPPORTED): ([0-9]+)$')
    for line in stdout.splitlines():
        if current_group is not None:
            m = result_regexp.match(line)
            if m:
                status, value = m.group(1,2)
                properties['{}-{}'.format(current_group, status)] = int(value)
        # are we starting another group?
        m = group_regexp.match(line)
        if m:
            path = m.group(1)
            _, current_group = os.path.split(path)

    return properties
