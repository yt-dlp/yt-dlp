# Allow direct execution
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import datetime as dt
import json
import subprocess


def setup_variables(environment):
    """
    environment must contain these keys:
        REPOSITORY, INPUTS, PROCESSED,
        PUSH_VERSION_COMMIT, PYPI_PROJECT,
        SOURCE_PYPI_PROJECT, SOURCE_PYPI_SUFFIX,
        TARGET_PYPI_PROJECT, TARGET_PYPI_SUFFIX,
        SOURCE_ARCHIVE_REPO, TARGET_ARCHIVE_REPO,
        HAS_SOURCE_ARCHIVE_REPO_TOKEN,
        HAS_TARGET_ARCHIVE_REPO_TOKEN,
        HAS_ARCHIVE_REPO_TOKEN

    INPUTS must contain these keys:
        prerelease

    PROCESSED must contain these keys:
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

    version = json.loads(subprocess.run((
        sys.executable, 'devscripts/update-version.py',
        '--json',
        '-c', resolved_source,
        '-r', REPOSITORY,
        INPUTS.get('version') or revision,
    ), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout)['version']

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
            pypi_project = environment['TARGET_PYPI_PROJECT']
            pypi_suffix = environment['TARGET_PYPI_SUFFIX']
    else:
        target_tag = source_tag or version
        if source_channel:
            target_repo = source_channel
            target_repo_token = f'{PROCESSED["source_repo"].upper()}_ARCHIVE_REPO_TOKEN'
            if not json.loads(environment['HAS_SOURCE_ARCHIVE_REPO_TOKEN']):
                does_not_have_needed_token = True
            pypi_project = environment['SOURCE_PYPI_PROJECT']
            pypi_suffix = environment['SOURCE_PYPI_SUFFIX']
        else:
            target_repo = REPOSITORY

    if does_not_have_needed_token:
        if not json.loads(environment['HAS_ARCHIVE_REPO_TOKEN']):
            print('::error::Repository access secret {target_repo_token} not found')
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


def _test(github_repository, repo_vars, repo_secrets, inputs, expected=None):
    from devscripts.utils import read_version
    orig_version = read_version()

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

    version = json.loads(subprocess.run((
        sys.executable, 'devscripts/update-version.py', '--json', orig_version,
    ), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL).stdout)['version']
    assert version == orig_version

    print('    {\n' + '\n'.join(f'        {k!r}: {v!r},' for k, v in result.items()) + '\n    }')
    if expected:
        assert result == expected


def _run_tests():
    _test('yt-dlp/yt-dlp', {'PUSH_VERSION_COMMIT': '1'}, {}, {}, {
        'channel': 'stable',
        'version': dt.datetime.now(tz=dt.timezone.utc).strftime('%Y.%m.%d'),
        'target_repo': 'yt-dlp/yt-dlp',
        'target_repo_token': None,
        'target_tag': dt.datetime.now(tz=dt.timezone.utc).strftime('%Y.%m.%d'),
        'pypi_project': None,
        'pypi_suffix': None,
    })
    _test('bashonly/yt-dlp', {}, {}, {'version': '2025.09.01.000000'}, {
        'channel': 'bashonly/yt-dlp',
        'version': '2025.09.01.000000',
        'target_repo': 'bashonly/yt-dlp',
        'target_repo_token': None,
        'target_tag': '2025.09.01.000000',
        'pypi_project': None,
        'pypi_suffix': None,
    })
    _test('bashonly/yt-dlp', {
        'NIGHTLY_ARCHIVE_REPO': 'bashonly/yt-dlp-nightly-builds',
        'NIGHTLY_PYPI_PROJECT': 'yt-dlp-test',
        'NIGHTLY_PYPI_SUFFIX': 'pre',
    }, {
        'ARCHIVE_REPO_TOKEN': '1',
    }, {
        'version': '2025.09.01.000000',
        'source': 'nightly',
        'prerelease': True,
    }, {
        'channel': 'nightly',
        'version': '2025.09.01.000000',
        'target_repo': 'bashonly/yt-dlp-nightly-builds',
        'target_repo_token': 'ARCHIVE_REPO_TOKEN',
        'target_tag': '2025.09.01.000000',
        'pypi_project': 'yt-dlp-test',
        'pypi_suffix': 'pre',
    })


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
