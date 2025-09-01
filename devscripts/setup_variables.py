# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime as dt
import json

from devscripts.utils import calculate_version


def setup_variables(environment):
    """
    `environment` must contain these keys:
        REPOSITORY, INPUTS, PROCESSED,
        PUSH_VERSION_COMMIT, PYPI_PROJECT,
        SOURCE_PYPI_PROJECT, SOURCE_PYPI_SUFFIX,
        TARGET_PYPI_PROJECT, TARGET_PYPI_SUFFIX,
        SOURCE_ARCHIVE_REPO, TARGET_ARCHIVE_REPO,
        HAS_SOURCE_ARCHIVE_REPO_TOKEN,
        HAS_TARGET_ARCHIVE_REPO_TOKEN,
        HAS_ARCHIVE_REPO_TOKEN

    `INPUTS` must contain these keys:
        prerelease

    `PROCESSED` must contain these keys:
        source_repo, source_tag,
        target_repo, target_tag
    """
    REPOSITORY = environment['REPOSITORY']
    INPUTS = json.loads(environment['INPUTS'])
    PROCESSED = json.loads(environment['PROCESSED'])

    source_channel = None
    does_not_have_needed_token = False
    target_repo_token = None
    pypi_project = None
    pypi_suffix = None

    source_repo = PROCESSED['source_repo']
    source_tag = PROCESSED['source_tag']
    if source_repo == 'stable':
        source_repo = 'yt-dlp/yt-dlp'
    elif not source_repo:
        source_repo = REPOSITORY
    elif environment['SOURCE_ARCHIVE_REPO']:
        source_channel = environment['SOURCE_ARCHIVE_REPO']
    elif not source_tag and '/' not in source_repo:
        source_tag = source_repo
        source_repo = REPOSITORY

    resolved_source = source_repo
    if source_tag:
        resolved_source = f'{resolved_source}@{source_tag}'
    elif source_repo == 'yt-dlp/yt-dlp':
        resolved_source = 'stable'

    if INPUTS['prerelease'] or not environment['PUSH_VERSION_COMMIT']:
        revision = dt.datetime.now(tz=dt.timezone.utc).strftime('%H%M%S')
    else:
        revision = ''

    version = calculate_version(INPUTS.get('version') or revision)

    target_repo = PROCESSED['target_repo']
    target_tag = PROCESSED['target_tag']
    if target_repo:
        if not target_tag:
            if environment['TARGET_ARCHIVE_REPO']:
                target_tag = source_tag or version
            else:
                target_tag = target_repo
                target_repo = REPOSITORY
        if target_repo != REPOSITORY:
            target_repo = environment['TARGET_ARCHIVE_REPO']
            target_repo_token = f'{PROCESSED["target_repo"].upper()}_ARCHIVE_REPO_TOKEN'
            if not json.loads(environment['HAS_TARGET_ARCHIVE_REPO_TOKEN']):
                does_not_have_needed_token = True
            pypi_project = environment['TARGET_PYPI_PROJECT'] or None
            pypi_suffix = environment['TARGET_PYPI_SUFFIX'] or None
    else:
        target_tag = source_tag or version
        if source_channel:
            target_repo = source_channel
            target_repo_token = f'{PROCESSED["source_repo"].upper()}_ARCHIVE_REPO_TOKEN'
            if not json.loads(environment['HAS_SOURCE_ARCHIVE_REPO_TOKEN']):
                does_not_have_needed_token = True
            pypi_project = environment['SOURCE_PYPI_PROJECT'] or None
            pypi_suffix = environment['SOURCE_PYPI_SUFFIX'] or None
        else:
            target_repo = REPOSITORY

    if does_not_have_needed_token:
        if not json.loads(environment['HAS_ARCHIVE_REPO_TOKEN']):
            print(f'::error::Repository access secret {target_repo_token} not found')
            return None
        target_repo_token = 'ARCHIVE_REPO_TOKEN'

    if target_repo == REPOSITORY and not INPUTS['prerelease']:
        pypi_project = environment['PYPI_PROJECT'] or None

    return {
        'channel': resolved_source,
        'version': version,
        'target_repo': target_repo,
        'target_repo_token': target_repo_token,
        'target_tag': target_tag,
        'pypi_project': pypi_project,
        'pypi_suffix': pypi_suffix,
    }


def process_inputs(inputs):
    outputs = {}
    for key in ('source', 'target'):
        repo, _, tag = inputs.get(key, '').partition('@')
        outputs[f'{key}_repo'] = repo
        outputs[f'{key}_tag'] = tag
    return outputs


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

    exp = expected.copy()
    if ignore_revision:
        assert len(result['version']) == len(exp['version'])
        version_is_tag = result['version'] == result['target_tag']
        for dct in (result, exp):
            dct['version'] = '.'.join(dct['version'].split('.')[:3])
            if version_is_tag:
                dct['target_tag'] = dct['version']
    assert result == exp, f'{github_repository} {note}'


def _run_tests():
    DEFAULT_VERSION_WITH_REVISION = dt.datetime.now(tz=dt.timezone.utc).strftime('%Y.%m.%d.%H%M%S')
    DEFAULT_VERSION = DEFAULT_VERSION_WITH_REVISION[:10]
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

    _test(
        'yt-dlp/yt-dlp', 'official vars/secrets, stable',
        BASE_REPO_VARS, BASE_REPO_SECRETS, {}, {
            'channel': 'stable',
            'version': DEFAULT_VERSION,
            'target_repo': 'yt-dlp/yt-dlp',
            'target_repo_token': None,
            'target_tag': DEFAULT_VERSION,
            'pypi_project': 'yt-dlp',
            'pypi_suffix': None,
        })
    _test(
        'yt-dlp/yt-dlp', 'official vars/secrets, nightly (w/o target)',
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
        'yt-dlp/yt-dlp', 'official vars/secrets, nightly',
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
        'yt-dlp/yt-dlp', 'official vars/secrets, master (w/o target)',
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
        'yt-dlp/yt-dlp', 'official vars/secrets, master',
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
        'bashonly/yt-dlp', 'fork w/o vars/secrets, stable',
        {}, {}, {}, {
            'channel': 'bashonly/yt-dlp',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'bashonly/yt-dlp',
            'target_repo_token': None,
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        'bashonly/yt-dlp', 'fork w/o vars/secrets, prerelease',
        {}, {}, {'prerelease': True}, {
            'channel': 'bashonly/yt-dlp',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'bashonly/yt-dlp',
            'target_repo_token': None,
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        'bashonly/yt-dlp', 'fork w/o vars/secrets, nightly',
        {}, {}, {
            'prerelease': True,
            'source': 'nightly',
            'target': 'nightly',
        }, {
            'channel': 'bashonly/yt-dlp@nightly',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'bashonly/yt-dlp',
            'target_repo_token': None,
            'target_tag': 'nightly',
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        'bashonly/yt-dlp', 'fork w/o vars/secrets, master',
        {}, {}, {
            'prerelease': True,
            'source': 'master',
            'target': 'master',
        }, {
            'channel': 'bashonly/yt-dlp@master',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'bashonly/yt-dlp',
            'target_repo_token': None,
            'target_tag': 'master',
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        'bashonly/yt-dlp', 'fork w/o vars/secrets, revision',
        {}, {}, {'version': '123'}, {
            'channel': 'bashonly/yt-dlp',
            'version': f'{DEFAULT_VERSION}.123',
            'target_repo': 'bashonly/yt-dlp',
            'target_repo_token': None,
            'target_tag': f'{DEFAULT_VERSION}.123',
            'pypi_project': None,
            'pypi_suffix': None,
        })

    _test(
        'bashonly/yt-dlp', 'fork w/ PUSH_VERSION_COMMIT, stable',
        {'PUSH_VERSION_COMMIT': '1'}, {}, {}, {
            'channel': 'bashonly/yt-dlp',
            'version': DEFAULT_VERSION,
            'target_repo': 'bashonly/yt-dlp',
            'target_repo_token': None,
            'target_tag': DEFAULT_VERSION,
            'pypi_project': None,
            'pypi_suffix': None,
        })
    _test(
        'bashonly/yt-dlp', 'fork w/ PUSH_VERSION_COMMIT, prerelease',
        {'PUSH_VERSION_COMMIT': '1'}, {}, {'prerelease': True}, {
            'channel': 'bashonly/yt-dlp',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'bashonly/yt-dlp',
            'target_repo_token': None,
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)

    _test(
        'bashonly/yt-dlp', 'fork w/NIGHTLY_ARCHIVE_REPO_TOKEN, nightly', {
            'NIGHTLY_ARCHIVE_REPO': 'bashonly/yt-dlp-nightly-builds',
            'PYPI_PROJECT': 'yt-dlp-test',
        }, {
            'NIGHTLY_ARCHIVE_REPO_TOKEN': '1',
        }, {
            'source': 'bashonly/yt-dlp-nightly-builds',
            'target': 'nightly',
            'prerelease': True,
        }, {
            'channel': 'bashonly/yt-dlp-nightly-builds',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'bashonly/yt-dlp-nightly-builds',
            'target_repo_token': 'NIGHTLY_ARCHIVE_REPO_TOKEN',
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        'bashonly/yt-dlp', 'fork w/MASTER_ARCHIVE_REPO_TOKEN, master', {
            'MASTER_ARCHIVE_REPO': 'bashonly/yt-dlp-master-builds',
            'MASTER_PYPI_PROJECT': 'yt-dlp-test',
            'MASTER_PYPI_SUFFIX': 'dev',
        }, {
            'MASTER_ARCHIVE_REPO_TOKEN': '1',
        }, {
            'source': 'bashonly/yt-dlp-master-builds',
            'target': 'master',
            'prerelease': True,
        }, {
            'channel': 'bashonly/yt-dlp-master-builds',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'bashonly/yt-dlp-master-builds',
            'target_repo_token': 'MASTER_ARCHIVE_REPO_TOKEN',
            'target_tag': DEFAULT_VERSION_WITH_REVISION,
            'pypi_project': 'yt-dlp-test',
            'pypi_suffix': 'dev',
        }, ignore_revision=True)

    _test(
        'bashonly/yt-dlp', 'fork, non-numeric tag',
        {}, {}, {'source': 'experimental'}, {
            'channel': 'bashonly/yt-dlp@experimental',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'bashonly/yt-dlp',
            'target_repo_token': None,
            'target_tag': 'experimental',
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)
    _test(
        'bashonly/yt-dlp', 'fork, non-numeric tag, updates to stable',
        {}, {}, {
            'prerelease': True,
            'source': 'stable',
            'target': 'experimental',
        }, {
            'channel': 'stable',
            'version': DEFAULT_VERSION_WITH_REVISION,
            'target_repo': 'bashonly/yt-dlp',
            'target_repo_token': None,
            'target_tag': 'experimental',
            'pypi_project': None,
            'pypi_suffix': None,
        }, ignore_revision=True)

    print('all tests passed')


if __name__ == '__main__':
    if not os.getenv('GITHUB_OUTPUT'):
        print('This script is only intended for use with GitHub Actions', file=sys.stderr)
        sys.exit(1)

    if 'process_inputs' in sys.argv:
        inputs = json.loads(os.environ['INPUTS'])
        print('::group::Inputs')
        print(json.dumps(inputs, indent=2))
        print('::endgroup::')
        outputs = process_inputs(inputs)
        print('::group::Processed')
        print(json.dumps(outputs, indent=2))
        print('::endgroup::')
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write('\n'.join(f'{key}={value}' for key, value in outputs.items()))
        sys.exit(0)

    outputs = setup_variables(dict(os.environ))
    if not outputs:
        sys.exit(1)

    print('::group::Output variables')
    print(json.dumps(outputs, indent=2))
    print('::endgroup::')

    with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
        f.write('\n'.join(f'{key}={value or ""}' for key, value in outputs.items()))
