import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime as dt
import json

from devscripts.setup_variables import STABLE_REPOSITORY, process_inputs, setup_variables
from devscripts.utils import calculate_version


def _test(github_repository, note, repo_vars, repo_secrets, inputs, expected=None, ignore_revision=False):
    inp = inputs.copy()
    inp.setdefault('linux_armv7l', True)
    inp.setdefault('prerelease', False)
    processed = process_inputs(inp)
    source_repo = processed['source_repo'].upper()
    target_repo = processed['target_repo'].upper()
    variables = {k.upper(): v for k, v in repo_vars.items()}
    secrets = {k.upper(): v for k, v in repo_secrets.items()}

    env = {
        # Keep this in sync with prepare.setup_variables in release.yml
        'INPUTS': json.dumps(inp),
        'PROCESSED': json.dumps(processed),
        'REPOSITORY': github_repository,
        'PUSH_VERSION_COMMIT': variables.get('PUSH_VERSION_COMMIT') or '',
        'PYPI_PROJECT': variables.get('PYPI_PROJECT') or '',
        'SOURCE_PYPI_PROJECT': variables.get(f'{source_repo}_PYPI_PROJECT') or '',
        'SOURCE_PYPI_SUFFIX': variables.get(f'{source_repo}_PYPI_SUFFIX') or '',
        'TARGET_PYPI_PROJECT': variables.get(f'{target_repo}_PYPI_PROJECT') or '',
        'TARGET_PYPI_SUFFIX': variables.get(f'{target_repo}_PYPI_SUFFIX') or '',
        'SOURCE_ARCHIVE_REPO': variables.get(f'{source_repo}_ARCHIVE_REPO') or '',
        'TARGET_ARCHIVE_REPO': variables.get(f'{target_repo}_ARCHIVE_REPO') or '',
        'HAS_SOURCE_ARCHIVE_REPO_TOKEN': json.dumps(bool(secrets.get(f'{source_repo}_ARCHIVE_REPO_TOKEN'))),
        'HAS_TARGET_ARCHIVE_REPO_TOKEN': json.dumps(bool(secrets.get(f'{target_repo}_ARCHIVE_REPO_TOKEN'))),
        'HAS_ARCHIVE_REPO_TOKEN': json.dumps(bool(secrets.get('ARCHIVE_REPO_TOKEN'))),
    }

    result = setup_variables(env)
    if not expected:
        print('        {\n' + '\n'.join(f'            {k!r}: {v!r},' for k, v in result.items()) + '\n        }')
        return

    exp = expected.copy()
    if ignore_revision:
        assert len(result['version']) == len(exp['version']), f'revision missing: {github_repository} {note}'
        version_is_tag = result['version'] == result['target_tag']
        for dct in (result, exp):
            dct['version'] = '.'.join(dct['version'].split('.')[:3])
            if version_is_tag:
                dct['target_tag'] = dct['version']
    assert result == exp, f'unexpected result: {github_repository} {note}'


def test_setup_variables():
    DEFAULT_VERSION_WITH_REVISION = dt.datetime.now(tz=dt.timezone.utc).strftime('%Y.%m.%d.%H%M%S')
    DEFAULT_VERSION = calculate_version()
    BASE_REPO_VARS = {
        'MASTER_ARCHIVE_REPO': 'yt-dlp/yt-dlp-master-builds',
        'NIGHTLY_ARCHIVE_REPO': 'yt-dlp/yt-dlp-nightly-builds',
        'NIGHTLY_PYPI_PROJECT': 'yt-dlp',
        'NIGHTLY_PYPI_SUFFIX': 'dev',
        'PUSH_VERSION_COMMIT': '1',
        'PYPI_PROJECT': 'yt-dlp',
    }
    BASE_REPO_SECRETS = {
        'ARCHIVE_REPO_TOKEN': '1',
    }
    FORK_REPOSITORY = 'fork/yt-dlp'
    FORK_ORG = FORK_REPOSITORY.partition('/')[0]

    _test(
        STABLE_REPOSITORY, 'official vars/secrets, stable',
        BASE_REPO_VARS, BASE_REPO_SECRETS, {}, {
            'channel': 'stable',
            'version': DEFAULT_VERSION,
            'target_repo': STABLE_REPOSITORY,
            'target_repo_token': None,
            'target_tag': DEFAULT_VERSION,
            'pypi_project': 'yt-dlp',
            'pypi_suffix': None,
        })
    _test(
        STABLE_REPOSITORY, 'official vars/secrets, nightly (w/o target)',
        BASE_REPO_VARS, BASE_REPO_SECRETS, {
            'source': 'nightly',
            'prerelease': True,
        }, {
            'channel': 'nightly',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'yt-dlp/yt-dlp-nightly-builds',
            'target_repo_token': 'ARCHIVE_REPO_TOKEN',
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': 'yt-dlp',
            'pypi_suffix': 'dev',
        }, ignore_revision=True)
    _test(
        STABLE_REPOSITORY, 'official vars/secrets, nightly',
        BASE_REPO_VARS, BASE_REPO_SECRETS, {
            'source': 'nightly',
            'target': 'nightly',
            'prerelease': True,
        }, {
            'channel': 'nightly',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'yt-dlp/yt-dlp-nightly-builds',
            'target_repo_token': 'ARCHIVE_REPO_TOKEN',
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': 'yt-dlp',
            'pypi_suffix': 'dev',
        }, ignore_revision=True)
    _test(
        STABLE_REPOSITORY, 'official vars/secrets, master (w/o target)',
        BASE_REPO_VARS, BASE_REPO_SECRETS, {
            'source': 'master',
            'prerelease': True,
        }, {
            'channel': 'master',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'yt-dlp/yt-dlp-master-builds',
            'target_repo_token': 'ARCHIVE_REPO_TOKEN',
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        STABLE_REPOSITORY, 'official vars/secrets, master',
        BASE_REPO_VARS, BASE_REPO_SECRETS, {
            'source': 'master',
            'target': 'master',
            'prerelease': True,
        }, {
            'channel': 'master',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'yt-dlp/yt-dlp-master-builds',
            'target_repo_token': 'ARCHIVE_REPO_TOKEN',
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        STABLE_REPOSITORY, 'official vars/secrets, special tag, updates to stable',
        BASE_REPO_VARS, BASE_REPO_SECRETS, {
            'target': f'{STABLE_REPOSITORY}@experimental',
            'prerelease': True,
        }, {
            'channel': 'stable',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': STABLE_REPOSITORY,
            'target_repo_token': None,
            'target_tag': 'experimental',
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        STABLE_REPOSITORY, 'official vars/secrets, special tag, "stable" as target repo',
        BASE_REPO_VARS, BASE_REPO_SECRETS, {
            'target': 'stable@experimental',
            'prerelease': True,
        }, {
            'channel': 'stable',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': STABLE_REPOSITORY,
            'target_repo_token': None,
            'target_tag': 'experimental',
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)

    _test(
        FORK_REPOSITORY, 'fork w/o vars/secrets, stable',
        {}, {}, {}, {
            'channel': FORK_REPOSITORY,
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': FORK_REPOSITORY,
            'target_repo_token': None,
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        FORK_REPOSITORY, 'fork w/o vars/secrets, prerelease',
        {}, {}, {'prerelease': True}, {
            'channel': FORK_REPOSITORY,
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': FORK_REPOSITORY,
            'target_repo_token': None,
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        FORK_REPOSITORY, 'fork w/o vars/secrets, nightly',
        {}, {}, {
            'prerelease': True,
            'source': 'nightly',
            'target': 'nightly',
        }, {
            'channel': f'{FORK_REPOSITORY}@nightly',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': FORK_REPOSITORY,
            'target_repo_token': None,
            'target_tag': 'nightly',
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        FORK_REPOSITORY, 'fork w/o vars/secrets, master',
        {}, {}, {
            'prerelease': True,
            'source': 'master',
            'target': 'master',
        }, {
            'channel': f'{FORK_REPOSITORY}@master',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': FORK_REPOSITORY,
            'target_repo_token': None,
            'target_tag': 'master',
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        FORK_REPOSITORY, 'fork w/o vars/secrets, revision',
        {}, {}, {'version': '123'}, {
            'channel': FORK_REPOSITORY,
            'version': f'{DEFAULT_VERSION[:10]}.123',
            'target_repo': FORK_REPOSITORY,
            'target_repo_token': None,
            'target_tag': f'{DEFAULT_VERSION[:10]}.123',
            'pypi_project': None,
            'pypi_suffix': None,
        })

    _test(
        FORK_REPOSITORY, 'fork w/ PUSH_VERSION_COMMIT, stable',
        {'PUSH_VERSION_COMMIT': '1'}, {}, {}, {
            'channel': FORK_REPOSITORY,
            'version': DEFAULT_VERSION,
            'target_repo': FORK_REPOSITORY,
            'target_repo_token': None,
            'target_tag': DEFAULT_VERSION,
            'pypi_project': None,
            'pypi_suffix': None,
        })
    _test(
        FORK_REPOSITORY, 'fork w/ PUSH_VERSION_COMMIT, prerelease',
        {'PUSH_VERSION_COMMIT': '1'}, {}, {'prerelease': True}, {
            'channel': FORK_REPOSITORY,
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': FORK_REPOSITORY,
            'target_repo_token': None,
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)

    _test(
        FORK_REPOSITORY, 'fork w/NIGHTLY_ARCHIVE_REPO_TOKEN, nightly', {
            'NIGHTLY_ARCHIVE_REPO': f'{FORK_ORG}/yt-dlp-nightly-builds',
            'PYPI_PROJECT': 'yt-dlp-test',
        }, {
            'NIGHTLY_ARCHIVE_REPO_TOKEN': '1',
        }, {
            'source': f'{FORK_ORG}/yt-dlp-nightly-builds',
            'target': 'nightly',
            'prerelease': True,
        }, {
            'channel': f'{FORK_ORG}/yt-dlp-nightly-builds',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': f'{FORK_ORG}/yt-dlp-nightly-builds',
            'target_repo_token': 'NIGHTLY_ARCHIVE_REPO_TOKEN',
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        FORK_REPOSITORY, 'fork w/MASTER_ARCHIVE_REPO_TOKEN, master', {
            'MASTER_ARCHIVE_REPO': f'{FORK_ORG}/yt-dlp-master-builds',
            'MASTER_PYPI_PROJECT': 'yt-dlp-test',
            'MASTER_PYPI_SUFFIX': 'dev',
        }, {
            'MASTER_ARCHIVE_REPO_TOKEN': '1',
        }, {
            'source': f'{FORK_ORG}/yt-dlp-master-builds',
            'target': 'master',
            'prerelease': True,
        }, {
            'channel': f'{FORK_ORG}/yt-dlp-master-builds',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': f'{FORK_ORG}/yt-dlp-master-builds',
            'target_repo_token': 'MASTER_ARCHIVE_REPO_TOKEN',
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': 'yt-dlp-test',
            'pypi_suffix': 'dev',
        }, ignore_revision=True)

    _test(
        FORK_REPOSITORY, 'fork, non-numeric tag',
        {}, {}, {'source': 'experimental'}, {
            'channel': f'{FORK_REPOSITORY}@experimental',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': FORK_REPOSITORY,
            'target_repo_token': None,
            'target_tag': 'experimental',
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        FORK_REPOSITORY, 'fork, non-numeric tag, updates to stable',
        {}, {}, {
            'prerelease': True,
            'source': 'stable',
            'target': 'experimental',
        }, {
            'channel': 'stable',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': FORK_REPOSITORY,
            'target_repo_token': None,
            'target_tag': 'experimental',
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
