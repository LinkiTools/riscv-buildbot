# GCC .sum-fetching command.

from buildbot.status.builder import SUCCESS, WARNINGS, FAILURE, EXCEPTION
from buildbot.steps.shell import ShellCommand
from sumfiles import DejaResults, get_web_base
from gccgitdb import switch_to_branch
from shutil import copyfile

class CopyOldGCCSumFile (ShellCommand):
    """Copy the current gcc.sum file into the old_gcc.sum file."""
    name = "copy gcc.sum file"
    description = "copying previous gcc.sum file"
    descriptionDone = "copied previous gcc.sum file"
    command = [ 'true' ]

    def __init__ (self, **kwargs):
        ShellCommand.__init__ (self, **kwargs)

    def evaluateCommand (self, cmd):
        rev = self.getProperty('got_revision')
        builder = self.getProperty('buildername')
        isrebuild = self.getProperty ('isRebuild')
        branch = self.getProperty('branch')
        wb = get_web_base ()
        if branch is None:
            branch = 'master'

        if isrebuild and isrebuild == 'yes':
            return SUCCESS

        # Switch to the right branch inside the BUILDER repo
        switch_to_branch (builder, branch, force_switch = True)

        try:
            copyfile ("%s/%s/gcc.sum" % (wb, builder),
                      "%s/%s/previous_gcc.sum" % (wb, builder))
        except IOError:
            # If the dest file does not exist, ignore
            pass

        return SUCCESS

class GccCatSumfileCommand(ShellCommand):
    name = 'regressions'
    command = ['cat', 'gcc.sum']

    def __init__(self, **kwargs):
        ShellCommand.__init__(self, **kwargs)

    def evaluateCommand(self, cmd):
        rev = self.getProperty('got_revision')
        builder = self.getProperty('buildername')
        istrysched = self.getProperty('isTrySched')
        branch = self.getProperty('branch')
        if branch is None:
            branch = 'master'

        # Switch to the right branch inside the BUILDER repo
        switch_to_branch (builder, branch, force_switch = False)

        parser = DejaResults()
        cur_results = parser.read_sum_text(self.getLog('stdio').getText())
        baseline = parser.read_baseline (builder, branch)
        old_sum = parser.read_sum_file (builder, branch)
        result = SUCCESS

        if baseline is not None:
            report = parser.compute_regressions (builder, branch,
                                                 cur_results, baseline)
            if report is not '':
                self.addCompleteLog ('baseline_diff', report)
                result = WARNINGS

        if old_sum is not None:
            report = parser.compute_regressions (builder, branch,
                                                 cur_results, old_sum)
            if report is not '':
                self.addCompleteLog ('regressions', report)
                result = FAILURE

        if not istrysched or istrysched == 'no':
            parser.write_sum_file (cur_results, builder, branch)
            # If there was no previous baseline, then this run
            # gets the honor.
            if baseline is None:
                baseline = cur_results
            parser.write_baseline (baseline, builder, branch, rev)
        else:
            parser.write_try_build_sum_file (cur_results, builder, branch)

        return result
