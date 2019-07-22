import time
import os
from multiprocessing import Process

from gtmcore.configuration import Configuration
from gtmcore.files.lock import FileWriteLock
from gtmcore.fixtures import mock_config_file


def write_function(filename: str, delay: int, value: str, lock: FileWriteLock) -> None:
    """
    A test function that appends to a file after a delay
    """
    time.sleep(delay)
    with lock.lock():
        with open(filename, 'at') as f:
            f.write(value)


class TestFileWriteLock(object):

    def test_multiple_acquires(self, mock_config_file):
        """Test trying to lock around multiple writes"""
        conf_file, working_dir = mock_config_file

        config = Configuration(config_file=conf_file)
        filename = os.path.join(working_dir, "testfile1.dat")
        lock = FileWriteLock(filename, config)

        proc1 = Process(target=write_function, args=(filename, 1, "1", lock))
        proc1.start()
        proc2 = Process(target=write_function, args=(filename, 0, "2", lock))
        proc2.start()
        proc3 = Process(target=write_function, args=(filename, .5, "3", lock))
        proc3.start()

        time.sleep(7)
        proc1.join()
        proc1.terminate()
        proc2.join()
        proc2.terminate()
        proc3.join()
        proc3.terminate()

        with open(filename, 'rt') as f:
            data = f.read()

        assert data == "231"

    def test_lock_independence(self, mock_config_file):
        """Test to verify different files have different locks automatically"""
        conf_file, working_dir = mock_config_file

        config = Configuration(config_file=conf_file)
        filename1 = os.path.join(working_dir, "testfile1.dat")
        lock1 = FileWriteLock(filename1, config)
        filename2 = os.path.join(working_dir, "testfile2.dat")
        lock2 = FileWriteLock(filename2, config)

        proc1 = Process(target=write_function, args=(filename1, 1, "1", lock1))
        proc1.start()
        proc2 = Process(target=write_function, args=(filename1, 6, "2", lock1))
        proc2.start()
        proc3 = Process(target=write_function, args=(filename2, 0, "1", lock2))
        proc3.start()
        proc4 = Process(target=write_function, args=(filename2, 1, "2", lock2))
        proc4.start()

        time.sleep(3)

        with open(filename1, 'rt') as f:
            assert f.read() == '1'

        with open(filename2, 'rt') as f:
            assert f.read() == '12'

        proc1.join()
        proc1.terminate()
        proc2.join()
        proc2.terminate()
        proc3.join()
        proc3.terminate()
        proc4.join()
        proc4.terminate()
