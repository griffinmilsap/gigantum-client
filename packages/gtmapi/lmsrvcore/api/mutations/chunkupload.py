import graphene
import unicodedata
from pathlib import PosixPath

import os
import subprocess
import flask

from gtmcore.logging import LMLogger
from gtmcore.files.lock import FileWriteLock

logger = LMLogger.get_logger()


class ChunkUploadInput(graphene.InputObjectType):
    """Input Object for params needed for a chunked upload

    To use, add a field `chunk_upload_params` to your mutation input

    """
    file_size = graphene.String(required=True,
                                description='Total file size in bytes represented as a string due to '
                                            'limitations in JSON int encoding')

    chunk_size = graphene.Int(required=True,
                              description='Number of bytes in a single chunk (note, last chunk will be <= chunk_size)')

    total_chunks = graphene.Int(required=True,
                                description="Total number of chunks in the file")

    chunk_index = graphene.Int(required=True,
                               description="An index value for which chunk is currently being uploaded, starting at 0")

    filename = graphene.String(required=True,
                               description="The name of the file being uploaded")

    upload_id = graphene.String(required=True,
                                description="A UUID for an entire upload job")


class ChunkUploadMutation(object):
    """Abstract class for performing chunked uploads

    To use, inherit from this class when writing your mutation and add the required ChunkUploadInput field:

        from lmsrvcore.api.mutations import ChunkUploadMutation, ChunkUploadInput

        class MyMutation(graphene.relay.ClientIDMutation, ChunkUploadMutation):
            class Input:
                chunk_upload_params = ChunkUploadInput(required=True)

            @classmethod
            def mutate_and_process_upload(cls, input, context, info):
                ...
                return MyMutation()

    """
    # TODO: REFACTOR check if this comment is still true
    # NOTE: CURRENTLY INPUT DOES NOT GET INHERITED PROPERLY IN GRAPHENE, SO YOU MUST ADD THE PARAM TO YOUR CHILD CLASS
    class Arguments:
        chunk_upload_params = ChunkUploadInput(required=True)

    # The uploaded temporary absolute file path
    upload_file_path = None

    # The desired filename
    filename = None

    @staticmethod
    def validate_args(args):
        """Method to validate the input chunking arguments"""
        if args['chunk_index'] >= args['total_chunks']:
            raise ValueError("Invalid args. chunk_index >= total_chunks")

        if args['chunk_size'] * args['total_chunks'] < int(args['file_size']):
            raise ValueError("Invalid args. Not enough chunks expected")

    @staticmethod
    def py_secure_filename(filename: str) -> str:
        """Method to clean up provided filenames to be safe, relative paths

        This function removes leading slashes, control characters, '..' and '.' in directories, and replaces \\/:*"<>|?
        with underscores.


        Args:
            filename: Filename to sanitize

        Returns:
            str
        """
        # Completely remove control characters
        safe_filename = "".join(c for c in filename if unicodedata.category(c)[0] != "C")

        # Remove leading slash if attempting an absolute path
        if safe_filename[0] == "/":
            safe_filename = safe_filename[1:]

        # Remove ../ or ./ paths (should only be relative names from the repo root)
        filename_parts = PosixPath(safe_filename).parts
        relative_filename_parts = [p for p in filename_parts if p not in ['..', '.']]

        # Replace invalid characters with underscores
        invalid_char_map = {ord(ch): '_' for ch in '\\/:*"<>|?'}
        safe_parts = [part.translate(invalid_char_map).strip() for part in relative_filename_parts]

        safe_filename = "/".join(safe_parts)
        if safe_filename != filename:
            logger.info(f"Renaming unsafe filename `{filename}` to `{safe_filename}`")

        return safe_filename

    @staticmethod
    def get_temp_filename(upload_id, filename):
        """Method to generate the temporary filename"""
        return os.path.join(flask.current_app.config['LABMGR_CONFIG'].upload_dir,
                            "{}-{}".format(ChunkUploadMutation.py_secure_filename(upload_id),
                            ChunkUploadMutation.py_secure_filename(filename)))

    @staticmethod
    def get_filename(filename):
        """Method to generate the desired target filename"""
        return os.path.basename(ChunkUploadMutation.py_secure_filename(filename))

    @staticmethod
    def _prepare_file(filename: str, total_file_size: int) -> None:
        """Method to check if a file has started to be written, and if not, create a file of the correct size that
        is sparsely padded. This will be fast but also let seek operations properly occur when chunks arrive out of
        order.

        Args:
            filename: name of the file to prepare
            total_file_size: total size in bytes to pad

        Returns:
            None
        """
        if not os.path.exists(filename):
            if total_file_size > 0:
                args = ['dd', 'if=/dev/null', f'of={filename}', 'bs=1', 'count=1', f'seek={total_file_size - 1}']
                subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            else:
                # Touch the file so it exists for future seek/write ops
                open(filename, 'a').close()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **kwargs):
        try:
            chunk_params = kwargs.get("chunk_upload_params")
            logger.debug(f"Processing chunk {chunk_params['chunk_index']} for {chunk_params['filename']}")

            # Make sure the file is there
            if 'uploadChunk' not in info.context.files:
                msg = 'No file "uploadChunk" associated with request'
                logger.error(msg)
                raise ValueError(msg)

            # Validate input arguments
            cls.validate_args(chunk_params)

            upload_file_path = cls.get_temp_filename(chunk_params['upload_id'], chunk_params['filename'])

            with FileWriteLock(upload_file_path, flask.current_app.config['LABMGR_CONFIG']).lock():
                # Create a file with the proper total size, but punched out
                cls._prepare_file(upload_file_path, int(chunk_params['file_size']))

                # Write chunk to file
                with open(upload_file_path, 'r+b') as f:
                    f.seek(chunk_params['chunk_index'] * chunk_params['chunk_size'])
                    f.write(info.context.files.get('uploadChunk').stream.read())

            # If last chunk, move on to mutation
            logger.debug(f"Write for chunk {chunk_params['chunk_index']} complete")
            if chunk_params['chunk_index'] == chunk_params['total_chunks'] - 1:
                # Assume last chunk. Let mutation process
                filename = cls.get_filename(chunk_params['filename'])
                return cls.mutate_and_process_upload(info,
                                                     upload_file_path=upload_file_path,
                                                     upload_filename=filename,
                                                     **kwargs)
            else:
                # Assume more chunks to go. Short circuit request
                return cls.mutate_and_wait_for_chunks(info, **kwargs)

        except Exception as e:
            logger.exception(e)
            # Something bad happened, so make best effort to dump all the files in the body on the floor.
            # This is important because you must read all bytes out of a POST body when deployed with uwsgi/nginx
            if info.context.files:
                logger.error(f"Error occurred while processing a file chunk. Dumping all files in the body.")
                for fs in info.context.files.keys():
                    if info.context.files.get(fs):
                        try:
                            _ = info.context.files.get(fs).stream.read()
                            logger.error(f"Dumped file key {fs}")
                        except Exception:
                            pass
            raise

    @classmethod
    def mutate_and_process_upload(cls, info, upload_file_path, upload_filename, **kwargs):
        """Method to implement to process the upload. Must return a Mutation type"""
        raise NotImplemented

    @classmethod
    def mutate_and_wait_for_chunks(cls, info, **kwargs):
        """Method to implement to process set any non-null fields, but essentially just return.
         Must return a Mutation type"""
        raise NotImplemented
