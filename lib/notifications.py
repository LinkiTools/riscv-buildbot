# This file has all the services related to email notification.

import smtplib
import socket
from email.mime.text import MIMEText
from buildbot.interfaces import IEmailLookup
from zope.interface import implementer

def SendRootMessageGCCTesters (branch, change, rev,
                               istrysched = False,
                               try_to = None):
    global GCC_MAIL_TO, GCC_MAIL_FROM

    if istrysched:
        f = "/tmp/gcc-buildbot-%s-try.lock" % rev
    else:
        f = "/tmp/gcc-buildbot-%s.lock" % rev

    if os.path.exists (f):
        # The message has already been sent
        return

    # WE HAVE TO REMEMBER TO CLEAN THESE FILES REGULARLY
    open (f, 'w').close ()

    if not istrysched:
        text = ""
        text += "*** TEST RESULTS FOR COMMIT %s ***\n\n" % rev

        text += "Author: %s\n" % change.who
        text += "Branch: %s\n" % branch
        text += "Commit: %s\n\n" % rev

        text += change.comments.split ('\n')[0] + "\n\n"
        text += '\n'.join (change.comments.split ('\n')[1:])

        chg_title = change.comments.split ('\n')[0]
        text = text.encode ('ascii', 'ignore').decode ('ascii')
    else:
        text = ""
        text += "*** TEST RESULTS FOR TRY BUILD ***\n\n"

        text += "Branch: %s\n" % branch
        text += "Commit tested against: %s\n\n" % rev

        text += "Patch tested:\n\n"
        text += change

        chg_title = "Try Build against commit %s" % rev
        text = text.encode ('ascii', 'ignore').decode ('ascii')

    mail = MIMEText (text)
    if branch == 'trunk':
        sbj = "[gcc] %s" % chg_title
    else:
        sbj = "[gcc/%s] %s" % (branch, chg_title)

    mail['Subject'] = sbj
    mail['From'] = GCC_MAIL_FROM
    if not istrysched:
        mail['To'] = GCC_MAIL_TO
        mailto = GCC_MAIL_TO
        mail['Message-Id'] = "<%s@gcc-build>" % rev
    else:
        mail['To'] = try_to
        mailto = try_to
        mail['Message-Id'] = "<%s-try@gcc-build>" % rev

    s = smtplib.SMTP ('localhost')
    s.sendmail (GCC_MAIL_FROM, [ mailto ], mail.as_string ())
    s.quit ()

def make_breakage_lockfile_prefix ():
    return "/tmp/gcc-buildbot-breakage-report-"

def SendAuthorMessage (name, change, text_prepend):
    """Send a message to the author of the commit if it broke GCC.

We use a lock file to avoid reporting the breakage to different
people.  This may happen, for example, if a commit X breaks GCC, but
subsequent commits are made after X, by different people."""
    global GCC_MAIL_FROM

    lockfile = "%s%s" % (make_breakage_lockfile_prefix (), name)

    if os.path.exists (lockfile):
        # This means we have already reported this failure for this
        # builder to the author.
        return

    # This file will be cleaned the next time we run
    # MessageGCCTesters, iff the build breakage has been fixed.
    open (lockfile, 'w').close ()

    rev = change.revision
    to = change.who.encode ('ascii', 'ignore').decode ('ascii')
    title = change.comments.split ('\n')[0]

    sbj = 'Your commit \'%s\' broke GCC' % title

    text = "Hello there,\n\n"
    text += "Your commit:\n\n"
    text += "\t%s\n" % title
    text += "\t%s\n\n" % rev
    text += "broke GCC.  Please fix it, or the GCC gods will get you.\n\n"
    text += "You can find details of the breakage below.\n\n"
    text += "Cheers,\n\n"
    text += "Your GCC BuildBot.\n\n"
    text += "+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+\n\n"
    text += "\n" + text_prepend

    mail = MIMEText (text)
    mail['Subject'] = sbj
    mail['From'] = GCC_MAIL_FROM
    mail['To'] = to

    s = smtplib.SMTP ('localhost')
    s.sendmail (GCC_MAIL_FROM, [ to ], mail.as_string ())
    s.quit ()

def MessageGCCTesters (mode, name, build, results, master_status):
    """This function is responsible for composing the message that will be
send to the gcc-testers mailing list."""
    git_url = "http://gcc-build.sergiodj.net/cgit"
    branch = build.getSourceStamps ()[0].branch
    cur_change = build.getSourceStamps ()[0].changes[0]
    properties = build.getProperties ()
    isrebuild = properties.getProperty ('isRebuild')

    # Sending the root message to gcc-testers.
    SendRootMessageGCCTesters (branch, cur_change, cur_change.revision)

    # Subject
    subj = "Failures on %s, branch %s" % (name, branch)

    # Body
    text = ""

    # Build worker name, useful for knowing the exact configuration.
    text += "Buildworker:\n"
    text += "\t%s\n" % build.getWorkername ()

    # Including the link for the full build
    text += "\nFull Build URL:\n"
    text += "\t<%s>\n" % master_status.getURLForThing (build)

    # Commits that were tested.  Usually we should be dealing with
    # only one commit
    text += "\nCommit(s) tested:\n"
    ss_list = build.getSourceStamps ()
    for ss in ss_list:
        for chg in ss.changes:
            text += "\t%s\n" % chg.revision

    # Who's to blame?
    text += "\nAuthor(s) (in the same order as the commits):\n"
    for ss in ss_list:
        for chg in ss.changes:
            text += "\t%s\n" % chg.who

    # Subject of the changes
    text += "\nSubject:\n"
    text += "\t%s\n" % cur_change.comments.split ('\n')[0]

    # URL to find more info about what went wrong.
    text += "\nTestsuite log (gcc.sum and gcc.log) URL(s):\n"
    for ss in ss_list:
        commit_id = get_builder_commit_id (name, ss.revision, ss.branch)
        if commit_id:
            text += "\t<%s/%s/.git/tree/?h=%s&id=%s>\n" % (git_url, name, quote (ss.branch),
                                                           commit_id)
        else:
            text += "\t<Error fetching commit ID for %s>\n" % ss.revision

    # Including the 'regressions' log.  This is the 'diff' of what
    # went wrong.
    text += "\n"
    if isrebuild and isrebuild == 'yes':
        text += "\n*** WARNING: This was a REBUILD request! ***\n"
        text += "*** The previous build (build #%s) MAY NOT BE the ancestor of the current build! ***\n\n" % properties.getProperty ('buildnumber')

    # report_build_breakage will be True if we see a build breakage,
    # i.e., if the 'configure' or the 'compile' steps fail.  In this
    # case, we use this variable to know if we must report the
    # breakage directly to the author.
    report_build_breakage = False

    # found_regressions will be True if the 'regressions' log is not
    # empty.
    found_regressions = False

    for log in build.getLogs ():
        st = log.getStep ()
        if st.getResults ()[0] == FAILURE:
            n = st.getName ()
            if 'No space left on device' in log.getText ():
                text += "*** Internal error on buildworker (no space left on device). ***\n"
                text += "*** Please report this to the buildworker owner (see <%s/buildworker/%s>) ***\n\n" % (master_status.getBuildbotURL (), build.getWorkername ())
                continue
            elif n == 'update gcc master repo':
                text += "*** Failed to update master GCC git repository.  The build can continue. ***\n\n"
                continue
            elif n == 'update gcc repo':
                text += "*** Failed to update GCC git repository.  This is probably a timeout problem. ***\n\n"
                break
            elif n == 'configure gcc':
                text += "*** Failed to configure GCC. ***\n"
                text += "============================\n"
                text += log.getText ()
                text += "============================\n"
                subj = "*** COMPILATION FAILED *** " + subj
                report_build_breakage = True
                break
            elif n == 'compile gcc':
                text += "*** Failed to compiled GCC.  ***\n"
                text += "============================\n"
                ct = log.getText ().decode ('ascii', 'ignore')
                if len (ct) > 100000:
                    text += "\n+++ The full log is too big to be posted here."
                    text += "\n+++ These are the last 100 lines of it.\n\n"
                    ctt = ct.split ('\n')[-100:]
                    ct = '\n'.join (ctt)
                    text += ct
                else:
                    text += ct
                text += "============================\n"
                subj = "*** COMPILATION FAILED *** " + subj
                report_build_breakage = True
                break
            elif n == 'regressions' and log.getName () == 'regressions':
                text += "*** Diff to previous build ***\n"
                text += "============================\n"
                text += log.getText ()
                text += "============================\n"
                found_regressions = True
                break

    # Including the 'xfail' log.  It is important to say which tests
    # we are ignoring.
    if found_regressions:
        if os.path.exists (os.path.join (gcc_web_base, name)):
            xfail_commit = os.path.join (gcc_web_base, name, 'xfails', branch, '.last-commit')
            text += "\n\n*** Complete list of XFAILs for this builder ***\n\n"
            if os.path.exists (xfail_commit):
                with open (xfail_commit, 'r') as f:
                    com = f.read ().strip ('\n')
                    text += "To obtain the list of XFAIL tests for this builder, go to:\n\n"
                    text += "\t<http://git.sergiodj.net/?p=gcc-xfails.git;a=blob;f=xfails/%s/xfails/%s/xfail;hb=%s>\n\n" % (name, branch, com)
                    text += "You can also see a pretty-printed version of the list, with more information\n"
                    text += "about each XFAIL, by going to:\n\n"
                    text += "\t<http://git.sergiodj.net/?p=gcc-xfails.git;a=blob;f=xfails/%s/xfails/%s/xfail.table;hb=%s>\n" % (name, branch, com)
            else:
                text += "FAILURE TO OBTAIN THE COMMIT FOR THE XFAIL LIST.  PLEASE CONTACT THE BUILDBOT ADMIN.\n"
    text += "\n"

    if report_build_breakage:
        subj += " *** BREAKAGE ***"
        SendAuthorMessage (name, cur_change, text)
    else:
        # There is no build breakage anymore!  Yay!  Now, let's see if
        # we need to clean up any lock file from previous breaks.
        lockfile = "%s%s" % (make_breakage_lockfile_prefix (), name)
        if os.path.exists (lockfile):
            # We need to clean the lockfile.  Garbage-collect it here.
            os.remove (lockfile)

    return { 'body' : text,
             'type' : 'plain',
             'subject' : subj }

def MessageGCCTestersTryBuild (mode, name, build, results, master_status):
    """This function is responsible for composing the message that will be
send to the gcc-testers mailing list."""
    git_url = "http://gcc-build.sergiodj.net/cgit"
    branch = build.getSourceStamps ()[0].branch
    sourcestamp = build.getSourceStamps ()[0]
    cur_change = sourcestamp.patch[1]
    properties = build.getProperties ()
    isrebuild = properties.getProperty ('isRebuild')

    try_to = build.getReason ().strip ("'try' job by user ")
    # Sending the root message to gcc-testers.
    SendRootMessageGCCTesters (branch, cur_change, properties.getProperty ('revision'),
                               istrysched = True, try_to = try_to)

    # Subject
    subj = "Try Build on %s, branch %s" % (name, branch)

    # Body
    text = ""

    # Buildslave name, useful for knowing the exact configuration.
    text += "Buildslave:\n"
    text += "\t%s\n" % build.getSlavename ()

    # Including the link for the full build
    text += "\nFull Build URL:\n"
    text += "\t<%s>\n" % master_status.getURLForThing (build)

    # Commits that were tested.  Usually we should be dealing with
    # only one commit
    text += "\nLast commit(s) before Try Build:\n"
    text += "\t%s\n" % sourcestamp.revision

    # URL to find more info about what went wrong.
    text += "\nTestsuite log (gcc.sum and gcc.log) URL(s):\n"
    commit_id = get_builder_commit_id (name, sourcestamp.revision,
                                       sourcestamp.branch)
    if commit_id:
        text += "\t<%s/%s/.git/tree/?h=%s&id=%s>\n" % (git_url, name,
                                                       quote (sourcestamp.branch),
                                                       commit_id)
    else:
        text += "\t<Error fetching commit ID for %s>\n" % sourcestamp.revision

    # found_regressions will be True if the 'regressions' log is not
    # empty.
    found_regressions = False

    for log in build.getLogs ():
        st = log.getStep ()
        n = st.getName ()
        if st.getResults ()[0] == SUCCESS or st.getResults ()[0] == WARNINGS:
            if n == 'regressions':
                text += "\nCongratulations!  No regressions were found in this build!\n\n"
                break
        if st.getResults ()[0] == FAILURE:
            if 'No space left on device' in log.getText ():
                text += "*** Internal error on buildslave (no space left on device). ***\n"
                text += "*** Please report this to the buildslave owner (see <%s/buildslaves/%s>) ***\n\n" % (master_status.getBuildbotURL (), build.getSlavename ())
                continue
            elif n == 'update gcc master repo':
                text += "*** Failed to update master GCC git repository.  The build can continue. ***\n\n"
                continue
            elif n == 'update gcc repo':
                text += "*** Failed to update GCC git repository.  This is probably a timeout problem. ***\n\n"
                break
            elif n == 'configure gcc':
                text += "*** Failed to configure GCC. ***\n"
                text += "============================\n"
                text += log.getText ()
                text += "============================\n"
                subj = "*** COMPILATION FAILED *** " + subj
                break
            elif n == 'compile gcc':
                text += "*** Failed to compiled GCC.  ***\n"
                text += "============================\n"
                ct = log.getText ().decode ('ascii', 'ignore')
                if len (ct) > 100000:
                    text += "\n+++ The full log is too big to be posted here."
                    text += "\n+++ These are the last 100 lines of it.\n\n"
                    ctt = ct.split ('\n')[-100:]
                    ct = '\n'.join (ctt)
                    text += ct
                else:
                    text += ct
                text += "============================\n"
                subj = "*** COMPILATION FAILED *** " + subj
                break
            elif n == 'regressions' and log.getName () == 'regressions':
                text += "*** Diff to previous build ***\n"
                text += "============================\n"
                text += log.getText ()
                text += "============================\n"
                found_regressions = True
                break

    # Including the 'xfail' log.  It is important to say which tests
    # we are ignoring.
    if found_regressions:
        if os.path.exists (os.path.join (gcc_web_base, name)):
            xfail_commit = os.path.join (gcc_web_base, name, 'xfails', branch, '.last-commit')
            text += "\n\n*** Complete list of XFAILs for this builder ***\n\n"
            if os.path.exists (xfail_commit):
                with open (xfail_commit, 'r') as f:
                    com = f.read ().strip ('\n')
                    text += "To obtain the list of XFAIL tests for this builder, go to:\n\n"
                    text += "\t<http://git.sergiodj.net/?p=gcc-xfails.git;a=blob;f=xfails/%s/xfails/%s/xfail;hb=%s>\n\n" % (name, branch, com)
                    text += "You can also see a pretty-printed version of the list, with more information\n"
                    text += "about each XFAIL, by going to:\n\n"
                    text += "\t<http://git.sergiodj.net/?p=gcc-xfails.git;a=blob;f=xfails/%s/xfails/%s/xfail.table;hb=%s>\n" % (name, branch, com)
            else:
                text += "FAILURE TO OBTAIN THE COMMIT FOR THE XFAIL LIST.  PLEASE CONTACT THE BUILDBOT ADMIN.\n"
    text += "\n"

    return { 'body' : text,
             'type' : 'plain',
             'subject' : subj }

from buildbot.reporters import mail

class MyMailNotifier (mail.MailNotifier):
    """Extend the regular MailNotifier class in order to filter e-mails by scheduler."""
    def isMailNeeded (self, build, results):
        prop = build.properties.getProperty ('scheduler')
        if prop.startswith ('racy'):
            return False
        elif prop.startswith ('try'):
            if "TRY" not in self.tags:
                # This means we're dealing with mn.  We only send
                # e-mail on mn_try.
                return False
        else:
            if "TRY" in self.tags:
                # We're dealing with mn_try.
                return False
        return mail.MailNotifier.isMailNeeded (self, build, results)


@implementer(IEmailLookup)
class LookupEmailTryBuild (object):

    def getAddress (self, name):
        # List of [ dir, sorted_reverse ]
        tryjobdir = [ [ os.path.expanduser ("~/try_ssh_jobdir/new/"), False ],
                      [ os.path.expanduser ("~/try_ssh_jobdir/cur/"), True ] ]
        name_re = re.compile (".*(%s <.*@.*>),.*" % name, flags = re.UNICODE)
        for directory, sort_order in tryjobdir:
            for _, _, filenames in os.walk (directory):
                for f in sorted (filenames, reverse = sort_order):
                    with open (os.path.join (directory, f), 'r') as myf:
                        for line in reversed (myf.readlines ()):
                            m = re.match (name_re, line)
                            if m:
                                return m.group (1)
