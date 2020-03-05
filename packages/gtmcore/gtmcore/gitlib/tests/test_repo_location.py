import pytest

from gtmcore.gitlib import RepoLocation


def test_url_translations():
    """This should be kept current as a list of expected outputs from normal inputs"""
    expected_formatting = [
        # Leave canonical paths alone
        ('https://repo.gigantum.io/owner/project.git/',
         'https://username@repo.gigantum.io/owner/project.git/'),
        # Add trailing slash
        ('https://repo.gigantum.io/owner/project.git',
         'https://username@repo.gigantum.io/owner/project.git/'),
        # Always https
        ('http://repo.gigantum.io/owner/project.git',
         'https://username@repo.gigantum.io/owner/project.git/'),
        # Add trailing .git/
        ('https://repo.gigantum.io/owner/project',
         'https://username@repo.gigantum.io/owner/project.git/'),
        # Existing username overwritten
        ('https://othername@repo.gigantum.io/owner/project',
         'https://username@repo.gigantum.io/owner/project.git/'),
        ('/a/unix/path', '/a/unix/path'),
        # \ -> /, trailing slash stripped
        (r'\a\windows\path\\', '/a/windows/path'),
        # Trailing slash is stripped, no initial slash preserved
        ('a/unix/path/', 'a/unix/path'),
    ]

    for in_url, output in expected_formatting:
        remote = RepoLocation(in_url, 'username')
        assert remote.remote_location == output

    # We can also get rid of the username
    in_url = 'https://othername@repo.gigantum.io/owner/project'
    remote = RepoLocation(in_url, None)
    assert remote.remote_location == 'https://repo.gigantum.io/owner/project.git/'


def test_field_parsing():
    """We test OTHER fields besides remote_location (already tested extensively above)"""
    expected_fields = [
        # Leave canonical paths alone
        ('https://otheruser@repo.gigantum.io/owner/project.git/',
         {'owner_repo': 'owner/project',
          'base_path': '/owner/project',
          'host': 'repo.gigantum.io',
          # Note - different than initial URL
          'netloc': 'username@repo.gigantum.io',
          'owner': 'owner',
          'repo_name': 'project',
          }),
        ('/a/unix/path',
         {'owner_repo': 'unix/path',
          'base_path': '/a/unix/path',
          # Probably the oddest part of the API
          'host': '/a/unix/path',
          'netloc': '',
          'owner': 'unix',
          'repo_name': 'path',
          })
    ]

    for in_url, fields in expected_fields:
        remote = RepoLocation(in_url, 'username')
        for key, value in fields.items():
            assert getattr(remote, key) == value
