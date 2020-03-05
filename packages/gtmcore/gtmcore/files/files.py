import shutil
import os
from typing import Any, Dict, List, Optional

from gtmcore.labbook import LabBook
from gtmcore.logging import LMLogger
from gtmcore.activity import (ActivityDetailRecord, ActivityRecord,
                               ActivityStore, ActivityAction)
from gtmcore.activity.utils import ImmutableList, DetailRecordList, TextData
from gtmcore.configuration.utils import call_subprocess

logger = LMLogger.get_logger()


def _make_path_relative(path_str: str) -> str:
    while len(path_str or '') >= 1 and path_str[0] == os.path.sep:
        path_str = path_str[1:]
    return path_str


class FileOperationsException(Exception):
    pass


class FileOperations(object):

    @classmethod
    def content_size(cls, labbook: LabBook) -> int:
        """ Return the size on disk (in bytes) of the given LabBook.

        Args:
            labbook: Subject labbook

        Returns:
            int size of LabBook on disk
        """
        # Note: os.walk does NOT follow symlinks, but does follow hidden files
        total_bytes = 0
        for dirpath, dirnames, filenames in os.walk(labbook.root_dir):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_bytes += os.path.getsize(fp)
        return total_bytes

    @classmethod
    def put_file(cls, labbook: LabBook, section: str, src_file: str,
                 dst_path: str, txid: Optional[str] = None) -> Dict[str, Any]:
        """Move the file at `src_file` to `dst_dir`. Filename removes
        upload ID if present. This operation does NOT commit or create an
        activity record.

        Args:
            labbook: Subject LabBook
            section: Section name (code, input, output)
            src_file: Full path of file to insert into
            dst_path: Path within section to insert `src_file`
            txid: Optional transaction id

        Returns:
           Full path to inserted file.
        """
        if not os.path.abspath(src_file):
            raise ValueError(f"Source file `{src_file}` not an absolute path")

        if not os.path.isfile(src_file):
            raise ValueError(f"Source file does not exist at `{src_file}`")

        labbook.validate_section(section)
        r = call_subprocess(['git', 'check-ignore', os.path.basename(dst_path)],
                            cwd=labbook.root_dir, check=False)
        if dst_path and r and os.path.basename(dst_path) in r:
            logger.warning(f"File {dst_path} matches gitignore; "
                           f"not put into {str(labbook)}")
            raise FileOperationsException(f"`{dst_path}` matches "
                                          f"ignored pattern")

        mdst_dir = _make_path_relative(dst_path)
        full_dst = os.path.join(labbook.root_dir, section, mdst_dir)
        full_dst = full_dst.replace('..', '')
        full_dst = full_dst.replace('~', '')

        # Force overwrite if file already exists
        if os.path.isfile(os.path.join(full_dst, os.path.basename(src_file))):
            os.remove(os.path.join(full_dst, os.path.basename(src_file)))

        if not os.path.isdir(os.path.dirname(full_dst)):
            os.makedirs(os.path.dirname(full_dst), exist_ok=True)

        fdst = shutil.move(src_file, full_dst)
        relpath = fdst.replace(os.path.join(labbook.root_dir, section), '')
        return cls.get_file_info(labbook, section, relpath)

    @classmethod
    def insert_file(cls, labbook: LabBook, section: str, src_file: str,
                    dst_path: str = '') -> Dict[str, Any]:
        """ Move the file at `src_file` into the `dst_dir`, overwriting
        if a file already exists there. This calls `copy_into_container()` under-
        the-hood, but will create an activity record.

        Args:
            labbook: Subject labbook
            section: Section name (code, input, output)
            src_file: Full path of file to insert into
            dst_path: Relative path within labbook where `src_file`
                      should be copied to

        Returns:
            dict: The inserted file's info
        """

        finfo = FileOperations.put_file(labbook=labbook, section=section,
                                        src_file=src_file, dst_path=dst_path)

        rel_path = os.path.join(section, finfo['key'])

        activity_type, activity_detail_type, section_str = \
            labbook.get_activity_type_from_section(section)

        commit_msg = f"Added new {section_str} file {rel_path}"
        try:
            labbook.git.add(rel_path)
            commit = labbook.git.commit(commit_msg)
        except Exception as x:
            logger.error(x)
            os.remove(dst_path)
            raise FileOperationsException(x)

        # Create Activity record and detail
        _, ext = os.path.splitext(rel_path) or 'file'
        adr = ActivityDetailRecord(activity_detail_type,
                                   show=False,
                                   importance=0,
                                   action=ActivityAction.CREATE,
                                   data=TextData('plain', commit_msg))

        ar = ActivityRecord(activity_type,
                            message=commit_msg,
                            show=True,
                            importance=255,
                            linked_commit=commit.hexsha,
                            detail_objects=DetailRecordList([adr]),
                            tags=ImmutableList([ext]))

        ars = ActivityStore(labbook)
        ars.create_activity_record(ar)

        return finfo

    @classmethod
    def complete_batch(cls, labbook: LabBook, txid: str,
                       cancel: bool = False, rollback: bool = False) -> None:
        """
        Indicate a batch upload is finished and sweep all new files.

        Args:
            labbook: Subject labbook
            txid: Transaction id (correlator)
            cancel: Indicate transaction finished but due to cancellation
            rollback: Undo all local changes if cancelled (default False)

        Returns:
            None
        """

        if cancel and rollback:
            logger.warning(f"Cancelled tx {txid}, doing git reset")
            call_subprocess(['git', 'reset', '--hard'],
                            cwd=labbook.root_dir)
        else:
            logger.info(f"Done batch upload {txid}, cancelled={cancel}")
            if cancel:
                logger.warning("Sweeping aborted batch upload.")
            m = "Cancelled upload `{txid}`. " if cancel else ''
            labbook.sweep_uncommitted_changes(upload=True,
                                              extra_msg=m,
                                              show=True)

    @classmethod
    def delete_files(cls, labbook: LabBook, section: str, relative_paths: List[str]) -> None:
        """Delete file (or directory) from inside lb section.

        The list of paths is deleted in series. Only provide "parent" nodes in the file tree. This is because deletes
        on directories will remove all child objects, so subsequent deletes of individual files will then fail.


        Args:
            labbook(LabBook): Subject LabBook
            section(str): Section name (code, input, output)
            relative_paths(list(str)): a list of relative paths from labbook root to target

        Returns:
            None
        """
        labbook.validate_section(section)

        if not isinstance(relative_paths, list):
            raise ValueError("Must provide list of paths to remove")

        for file_path in relative_paths:
            relative_path = LabBook.make_path_relative(file_path)
            target_path = os.path.join(labbook.root_dir, section, relative_path)
            if not os.path.exists(target_path):
                raise ValueError(f"Attempted to delete non-existent path at `{target_path}`")
            else:
                labbook.git.remove(target_path, force=True, keep_file=False)
                if os.path.exists(target_path):
                    raise IOError(f"Failed to delete path: {target_path}")
        labbook.sweep_uncommitted_changes(show=True)

    @classmethod
    def _make_move_activity_record(cls, labbook: LabBook, section: str, dst_abs_path: str,
                                   commit_msg: str) -> None:
        if os.path.isdir(dst_abs_path):
            labbook.git.add_all(dst_abs_path)
        else:
            labbook.git.add(dst_abs_path)

        commit = labbook.git.commit(commit_msg)
        activity_type, activity_detail_type, section_str = labbook.get_activity_type_from_section(section)
        adr = ActivityDetailRecord(activity_detail_type,
                                   show=False,
                                   importance=0,
                                   action=ActivityAction.EDIT,
                                   data=TextData('markdown', commit_msg))

        ar = ActivityRecord(activity_type,
                            message=commit_msg,
                            linked_commit=commit.hexsha,
                            show=True,
                            importance=255,
                            detail_objects=DetailRecordList([adr]),
                            tags=ImmutableList(['file-move']))

        ars = ActivityStore(labbook)
        ars.create_activity_record(ar)

    @classmethod
    def move_file(cls, labbook: LabBook, section: str, src_rel_path: str, dst_rel_path: str) \
            -> List[Dict[str, Any]]:

        """Move a file or directory within a labbook, but not outside of it. Wraps
        underlying "mv" call.

        Args:
            labbook: Subject LabBook
            section(str): Section name (code, input, output)
            src_rel_path(str): Source file or directory
            dst_rel_path(str): Target file name and/or directory
        """

        # Start with Validations
        labbook.validate_section(section)
        if not src_rel_path:
            raise ValueError("src_rel_path cannot be None or empty")

        if dst_rel_path is None:
            raise ValueError("dst_rel_path cannot be None or empty")

        src_rel_path = LabBook.make_path_relative(src_rel_path)
        dst_rel_path = LabBook.make_path_relative(dst_rel_path)

        src_abs_path = os.path.join(labbook.root_dir, section, src_rel_path.replace('..', ''))
        dst_abs_path = os.path.join(labbook.root_dir, section, dst_rel_path.replace('..', ''))

        if not os.path.exists(src_abs_path):
            raise ValueError(f"No src file exists at `{src_abs_path}`")

        try:
            src_type = 'directory' if os.path.isdir(src_abs_path) else 'file'
            logger.info(f"Moving {src_type} `{src_abs_path}` to `{dst_abs_path}`")
            labbook.git.remove(src_abs_path, keep_file=True)
            final_dest = shutil.move(src_abs_path, dst_abs_path)
            commit_msg = f"Moved {src_type} `{src_rel_path}` to `{dst_rel_path}`"
            cls._make_move_activity_record(labbook, section, dst_abs_path, commit_msg)

            if os.path.isfile(final_dest):
                t = final_dest.replace(os.path.join(labbook.root_dir, section), '')
                return [cls.get_file_info(labbook, section, t or "/")]
            else:
                moved_files = list()
                t = final_dest.replace(os.path.join(labbook.root_dir, section), '')
                moved_files.append(cls.get_file_info(labbook, section, t or "/"))
                for root, dirs, files in os.walk(final_dest):
                    rt = root.replace(os.path.join(labbook.root_dir, section), '')
                    rt = _make_path_relative(rt)
                    for d in sorted(dirs):
                        dinfo = cls.get_file_info(labbook, section, os.path.join(rt, d))
                        moved_files.append(dinfo)
                    for f in filter(lambda n: n != '.gitkeep', sorted(files)):
                        finfo = cls.get_file_info(labbook, section, os.path.join(rt, f))
                        moved_files.append(finfo)
                return moved_files

        except Exception as e:
            logger.critical("Failed moving file in labbook. Repository may be in corrupted state.")
            logger.exception(e)
            raise

    @classmethod
    def makedir(cls, labbook: LabBook, relative_path: str, create_activity_record: bool = False) -> None:
        """Make a new directory inside the labbook directory.

        Args:
            labbook: Subject LabBook
            relative_path(str): Path within the labbook to make directory
            create_activity_record(bool): If true, create commit and activity record

        Returns:
            str: Absolute path of new directory
        """
        if not relative_path:
            raise ValueError("relative_path argument cannot be None or empty")

        relative_path = LabBook.make_path_relative(relative_path)
        new_directory_path = os.path.join(labbook.root_dir, relative_path)
        if os.path.exists(new_directory_path):
            return
        else:
            logger.info(f"Making new directory in `{new_directory_path}`")
            os.makedirs(new_directory_path, exist_ok=True)
            new_dir = ''
            for d in relative_path.split(os.sep):
                new_dir = os.path.join(new_dir, d)
                if labbook.git.check_ignored(new_dir):
                    # This path is ignored - don't do any further git operations
                    logger.info(f'Skipping git operations for untracked path {new_dir}')
                    break

                full_new_dir = os.path.join(labbook.root_dir, new_dir)
                gitkeep_path = os.path.join(full_new_dir, '.gitkeep')
                if not os.path.exists(gitkeep_path):
                    with open(gitkeep_path, 'w') as gitkeep:
                        gitkeep.write("This file is necessary to keep this directory tracked by Git"
                                      " and archivable by compression tools. Do not delete or modify!")
                    labbook.git.add(gitkeep_path)

            if create_activity_record:
                # Create detail record
                activity_type, activity_detail_type, section_str = labbook.infer_section_from_relative_path(
                    relative_path)
                msg = f"Created new {section_str} directory `{relative_path}`"
                adr = ActivityDetailRecord(activity_detail_type,
                                           show=False,
                                           importance=0,
                                           action=ActivityAction.CREATE,
                                           data=TextData('markdown', msg))

                commit = labbook.git.commit(msg)

                # Create activity record
                ar = ActivityRecord(activity_type,
                                    message=msg,
                                    linked_commit=commit.hexsha,
                                    show=True,
                                    importance=255,
                                    detail_objects=DetailRecordList([adr]),
                                    tags=ImmutableList(['directory-create']))

                # Store
                ars = ActivityStore(labbook)
                ars.create_activity_record(ar)

    @classmethod
    def get_file_info(cls, labbook: LabBook, section: str, rel_file_path: str) -> Dict[str, Any]:
        """Method to get a file's detail information

        Args:
            labbook: Subject labbook
            rel_file_path(str): The relative file path to generate info from
            section(str): The section name (code, input, output)

        Returns:
            dict
        """
        # remove leading separators if one exists.
        rel_file_path = _make_path_relative(rel_file_path)
        full_path = os.path.join(labbook.root_dir, section, rel_file_path)

        file_info = os.stat(full_path)
        is_dir = os.path.isdir(full_path)

        # If it's a directory, add a trailing slash so UI renders properly
        if is_dir:
            if len(rel_file_path) == 0 or rel_file_path[-1] != os.path.sep:
                rel_file_path = f"{rel_file_path}{os.path.sep}"

        return {
                  'key': rel_file_path,
                  'is_dir': is_dir,
                  'size': file_info.st_size if not is_dir else 0,
                  'modified_at': file_info.st_mtime
               }

    @classmethod
    def walkdir(cls, labbook: LabBook, section: str, show_hidden: bool = False) -> List[Dict[str, Any]]:
        """Return a list of all files and directories in a section of the labbook. Never includes the .git or
         .gigantum directory.

        Args:
            labbook: Subject LabBook
            section(str): The labbook section (code, input, output) to walk
            show_hidden(bool): If True, include hidden directories (EXCLUDING .git and .gigantum)

        Returns:
            List[Dict[str, str]]: List of dictionaries containing file and directory metadata
        """
        labbook.validate_section(section)

        keys: List[str] = list()
        # base_dir is the root directory to search, to account for relative paths inside labbook.
        base_dir = os.path.join(labbook.root_dir, section)
        if not os.path.isdir(base_dir):
            raise ValueError(f"Labbook walkdir base_dir {base_dir} not an existing directory")

        for root, dirs, files in os.walk(base_dir):
            # Remove directories we ignore so os.walk does not traverse into them during future iterations
            if '.git' in dirs:
                del dirs[dirs.index('.git')]
            if '.gigantum' in dirs:
                del dirs[dirs.index('.gigantum')]

            # For more deterministic responses, sort resulting paths alphabetically.
            # Store directories then files, so pagination loads things in an intuitive order
            dirs.sort()
            keys.extend(sorted([os.path.join(root.replace(base_dir, ''), d) for d in dirs]))
            keys.extend(sorted([os.path.join(root.replace(base_dir, ''), f) for f in files]))

        # Create stats
        stats: List[Dict[str, Any]] = list()
        for f_p in keys:
            if not show_hidden and any([len(p) and p[0] == '.' for p in f_p.split(os.path.sep)]):
                continue
            stats.append(cls.get_file_info(labbook, section, f_p))

        return stats

    @classmethod
    def listdir(cls, labbook: LabBook, section: str, base_path: Optional[str] = None,
                show_hidden: bool = False) -> List[Dict[str, Any]]:
        """Return a list of all files and directories in a directory. Never includes the .git or
         .gigantum directory.

        Args:
            labbook: Subject labbook
            section(str): the labbook section to start from
            base_path(str): Relative base path, if not listing from labbook's root.
            show_hidden(bool): If True, include hidden directories (EXCLUDING .git and .gigantum)

        Returns:
            List[Dict[str, str]]: List of dictionaries containing file and directory metadata
        """
        labbook.validate_section(section)
        # base_dir is the root directory to search, to account for relative paths inside labbook.
        base_dir = os.path.join(labbook.root_dir, section, base_path or '')
        if not os.path.isdir(base_dir):
            raise ValueError(f"Labbook listdir base_dir {base_dir} not an existing directory")

        stats: List[Dict[str, Any]] = list()
        for item in os.listdir(base_dir):
            if item in ['.git', '.gigantum']:
                # Never include .git or .gigantum
                continue

            if not show_hidden and any([len(p) and p[0] == '.' for p in item.split('/')]):
                continue

            # Create tuple (isDir, key)
            stats.append(cls.get_file_info(labbook, section, os.path.join(base_path or "", item)))

        # For more deterministic responses, sort resulting paths alphabetically.
        return sorted(stats, key=lambda a: a['key'])
