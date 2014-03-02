# xattrMaildir folder support

from offlineimap.folder.Maildir import re_uidmatch, MaildirFolder

import os
import xattr
from offlineimap import imaputil

try: # python 2.6 has set() built in
    set
except NameError:
    from sets import Set as set

from offlineimap import OfflineImapError

class xattrMaildirFolder(MaildirFolder):
    def _scanfolder(self):
        """Cache the message list from a Maildir.

        Maildir flags are: R (replied) S (seen) T (trashed) D (draft) F
        (flagged).
        :returns: dict that can be used as self.messagelist"""
        maxage = self.config.getdefaultint("Account " + self.accountname,
                                           "maxage", None)
        maxsize = self.config.getdefaultint("Account " + self.accountname,
                                            "maxsize", None)
        retval = {}
        files = []
        nouidcounter = -1          # Messages without UIDs get negative UIDs.
        for dirannex in ['new', 'cur']:
            fulldirname = os.path.join(self.getfullname(), dirannex)
            files.extend((dirannex, filename) for
                         filename in os.listdir(fulldirname))

        for dirannex, filename in files:
            # We store just dirannex and filename, ie 'cur/123...'
            filepath = os.path.join(dirannex, filename)
            # check maxage/maxsize if this message should be considered
            if maxage and not self._iswithinmaxage(filename, maxage):
                continue
            if maxsize and (os.path.getsize(os.path.join(
                        self.getfullname(), filepath)) > maxsize):
                continue

            (prefix, uid, fmd5, maildirflags) = self._parse_filename(filename)
            if uid is None: # assign negative uid to upload it.
                uid = nouidcounter
                nouidcounter -= 1
            else:                       # It comes from our folder.
                uidmatch = re_uidmatch.search(filename)
                uid = None
                if not uidmatch:
                    uid = nouidcounter
                    nouidcounter -= 1
                else:
                    uid = long(uidmatch.group(1))
            # 'filename' is 'dirannex/filename', e.g. cur/123,U=1,FMD5=1:2,S
            retval[uid] = {'flags': set((xattr.get(os.path.join(self.getfullname(), filepath),
                                                   'org.offlineimap.flags',
                                                   namespace=xattr.NS_USER)).split()),
                           'filename': filepath}
        return retval

    def quickchanged(self, statusfolder):
        """Returns True if the Maildir has changed"""
        self.cachemessagelist()
        # Folder has different uids than statusfolder => TRUE
        if sorted(self.getmessageuidlist()) != \
                sorted(statusfolder.getmessageuidlist()):
            return True
        # Also check for flag changes, it's quick on a Maildir
        for (uid, message) in self.getmessagelist().iteritems():
            if message['flags'] != statusfolder.getmessageflags(uid):
                return True
        return False  #Nope, nothing changed

    def savemessageflags(self, uid, flags):
        """Sets the specified message's flags to the given set.

        This function moves the message to the cur or new subdir,
        depending on the 'S'een flag.

        Note that this function does not check against dryrun settings,
        so you need to ensure that it is never called in a
        dryrun mode."""
        oldfilename = self.messagelist[uid]['filename']
        dir_prefix, filename = os.path.split(oldfilename)
        # If a message has been seen, it goes into 'cur'
        dir_prefix = 'cur' if '\\Seen' in flags else 'new'

        if flags != self.messagelist[uid]['flags']:
            # Flags have actually changed, construct new filename Strip
            # off existing infostring (possibly discarding small letter
            # flags that dovecot uses TODO)
            infomatch = self.re_flagmatch.search(filename)
            if infomatch:
                filename = filename[:-len(infomatch.group())] #strip off
            infostr = '%s2,%s' % (self.infosep,
                                  ''.join(sorted(imaputil.flagsimap2maildir(flags))))
            filename += infostr

        newfilename = os.path.join(dir_prefix, filename)
        if (newfilename != oldfilename):
            try:
                os.rename(os.path.join(self.getfullname(), oldfilename),
                          os.path.join(self.getfullname(), newfilename))
            except OSError as e:
                raise OfflineImapError("Can't rename file '%s' to '%s': %s" % (
                                       oldfilename, newfilename, e[1]),
                                       OfflineImapError.ERROR.FOLDER)

            self.messagelist[uid]['flags'] = flags
            self.messagelist[uid]['filename'] = newfilename

        xattr.set(os.path.join(self.getfullname(), newfilename),
                  'org.offlineimap.flags', ' '.join(flags),
                  namespace=xattr.NS_USER)
