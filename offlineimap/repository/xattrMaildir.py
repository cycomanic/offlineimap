# xattrMaildir repository support

from offlineimap import folder
from offlineimap.repository.Maildir import MaildirRepository
import os

class xattrMaildirRepository(MaildirRepository):
    def _getfolders_scandir(self, root, extension = None):
        """Recursively scan folder 'root'; return a list of MailDirFolder

        :param root: (absolute) path to Maildir root
        :param extension: (relative) subfolder to examine within root"""
        self.debug("_GETFOLDERS_SCANDIR STARTING. root = %s, extension = %s" \
                   % (root, extension))
        retval = []

        # Configure the full path to this repository -- "toppath"
        if extension:
            toppath = os.path.join(root, extension)
        else:
            toppath = root
        self.debug("  toppath = %s" % toppath)

        # Iterate over directories in top & top itself.
        for dirname in os.listdir(toppath) + ['']:
            self.debug("  dirname = %s" % dirname)
            if dirname == '' and extension is not None:
                self.debug('  skip this entry (already scanned)')
                continue
            if dirname in ['cur', 'new', 'tmp']:
                self.debug("  skip this entry (Maildir special)")
                # Bypass special files.
                continue
            fullname = os.path.join(toppath, dirname)
            if not os.path.isdir(fullname):
                self.debug("  skip this entry (not a directory)")
                # Not a directory -- not a folder.
                continue
            if extension:
                # extension can be None which fails.
                foldername = os.path.join(extension, dirname)
            else:
                foldername = dirname

            if (os.path.isdir(os.path.join(fullname, 'cur')) and
                os.path.isdir(os.path.join(fullname, 'new')) and
                os.path.isdir(os.path.join(fullname, 'tmp'))):
                # This directory has maildir stuff -- process
                self.debug("  This is maildir folder '%s'." % foldername)
                if self.getconfboolean('restoreatime', False):
                    self._append_folder_atimes(foldername)
                retval.append(folder.xattrMaildir.xattrMaildirFolder(self.root,
                                                                     foldername,
                                                                     self.getsep(),
                                                                     self))

            if self.getsep() == '/' and dirname != '':
                # Recursively check sub-directories for folders too.
                retval.extend(self._getfolders_scandir(root, foldername))
        self.debug("_GETFOLDERS_SCANDIR RETURNING %s" % \
                   repr([x.getname() for x in retval]))
        return retval
