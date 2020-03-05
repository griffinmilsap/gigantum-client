from typing import Optional
import time

from gtmcore.labbook import LabBook, SecretStore
from gtmcore.container import container_for_context
from gtmcore.gitlib.git import GitAuthor
from gtmcore.logging import LMLogger

logger = LMLogger.get_logger()


class ContainerWorkflows(object):

    @staticmethod
    def start_labbook(labbook: LabBook, username: str, author: Optional[GitAuthor] = None) -> Optional[str]:
        project_container = container_for_context(username, labbook=labbook)
        project_container.start_project_container(author=author)

        secret_store = SecretStore(labbook, username)

        secrets_dir_map = secret_store.as_mount_dict.items()
        if secrets_dir_map:
            # If you are inserting a secret wait 3 seconds to ensure the entrypoint file has completed it's work.
            # There is a race condition between the container reporting that it is running and the environment being
            # fully configured and ready for secrets to be inserted.
            logger.info("Waiting for container to insert secrets.")
            time.sleep(3)

        for sec_local_src, sec_container_dst in secrets_dir_map:
            project_container.copy_into_container(src_path=sec_local_src, dst_dir=sec_container_dst)

        # TODO #1064 - if putting a secret fails, then stop container and raise exception

        return project_container.image_tag
