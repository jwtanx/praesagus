"""Actual Git hook operations in isolated repos; synthetic interpreter, no providers."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def git(repo, *args, env=None):
    return subprocess.run(['git', '-C', str(repo), *args], env=env, capture_output=True, text=True)


@pytest.fixture
def checkout(tmp_path):
    repo = tmp_path / 'checkout'
    repo.mkdir()
    assert git(repo, 'init', '-q').returncode == 0
    git(repo, 'config', 'user.name', 'Synthetic hook test')
    git(repo, 'config', 'user.email', 'fixture@example.invalid')
    (repo / '.githooks').mkdir()
    for name in ['commit-msg', 'pre-commit', 'pre-push', 'run-tests']:
        shutil.copy2(ROOT / '.githooks' / name, repo / '.githooks' / name)
    (repo / 'scripts').mkdir()
    shutil.copy2(ROOT / 'scripts/install_git_hooks.sh', repo / 'scripts/install_git_hooks.sh')
    (repo / 'scripts/planning').mkdir()
    shutil.copy2(ROOT / 'scripts/planning/check_staged_harness.py', repo / 'scripts/planning/check_staged_harness.py')
    fake = tmp_path / 'interpreter with spaces'
    fake.write_text('#!' + sys.executable + '\n' + '''
import importlib.util, json, os, sys
import subprocess
from pathlib import Path
with open(os.environ['HOOK_FIXTURE_LOG'], 'a') as handle:
    handle.write(json.dumps({'cwd': os.getcwd(), 'argv': sys.argv[1:]}) + '\\n')
if sys.argv[1] == '-c':
    mode = os.environ.get('HOOK_FIXTURE_PREREQUISITE')
    sys.version_info = (3, 10, 0) if mode == 'version' else (3, 11, 0)
    importlib.util.find_spec = (lambda name: None) if mode == 'pytest' else (lambda name: object())
    exec(sys.argv[2])
elif sys.argv[1:] == ['-m', 'pytest', '-q']:
    with open(os.environ['HOOK_FIXTURE_LOG'], 'a') as handle:
        handle.write(json.dumps({'test_git_env': {key: os.environ.get(key) for key in
            ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_PREFIX')}}) + '\\n')
    nested = Path(os.environ['HOOK_FIXTURE_LOG']).parent / 'nested-repository'
    nested.mkdir(exist_ok=True)
    subprocess = __import__('subprocess')
    subprocess.run(['git', 'init', '-q', str(nested)], check=True)
    (nested / 'fixture.txt').write_text('nested git works\\n')
    subprocess.run(['git', '-C', str(nested), 'add', 'fixture.txt'], check=True)
    sys.exit(int(os.environ.get('HOOK_FIXTURE_EXIT', '0')))
else:
    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
''')
    fake.chmod(0o755)
    env = {'PATH': os.environ['PATH'], 'LANG': 'C', 'HOOK_FIXTURE_LOG': str(tmp_path / 'calls.jsonl'), 'HOOK_FIXTURE_EXIT': '0'}
    git(repo, 'config', 'praesagus.testPython', str(fake))
    return repo, fake, env


def install(repo):
    result = subprocess.run(['sh', 'scripts/install_git_hooks.sh'], cwd=repo, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def stage(repo):
    (repo / 'owned.txt').write_text('synthetic\n')
    assert git(repo, 'add', 'owned.txt').returncode == 0


def hook_env(repo, env):
    return {**env, 'GIT_DIR': str(repo / '.git'), 'GIT_WORK_TREE': str(repo),
            'GIT_INDEX_FILE': str(repo / '.git/index'), 'GIT_PREFIX': ''}


def calls(env):
    return [json.loads(line) for line in Path(env['HOOK_FIXTURE_LOG']).read_text().splitlines()]


@pytest.mark.parametrize('hook', ['pre-commit', 'pre-push'])
def test_hook_context_isolated_test_child_and_exit_status(checkout, hook):
    repo, _, env = checkout
    install(repo)
    env = hook_env(repo, env)
    env['HOOK_FIXTURE_EXIT'] = '37'
    result = subprocess.run([str(repo / '.githooks' / hook)], cwd=repo, env=env, capture_output=True, text=True)
    assert result.returncode == 37, result.stderr
    recorded = calls(env)
    invocations = [call for call in recorded if 'argv' in call]
    assert [call['argv'][0] for call in invocations] == ['-c', '-m']
    assert invocations[-1] == {'cwd': str(repo), 'argv': ['-m', 'pytest', '-q']}
    child_env = next(call['test_git_env'] for call in recorded if 'test_git_env' in call)
    assert child_env == {key: None for key in ('GIT_DIR','GIT_WORK_TREE','GIT_INDEX_FILE','GIT_PREFIX')}
    assert (Path(env['HOOK_FIXTURE_LOG']).parent / 'nested-repository/.git/index').is_file()


@pytest.mark.parametrize('hook', ['pre-commit', 'pre-push'])
def test_hook_runner_uses_checkout_root_from_nested_cwd(checkout, hook):
    repo, _, env = checkout
    install(repo)
    child = repo / 'nested-cwd'
    child.mkdir()
    env['HOOK_FIXTURE_EXIT'] = '37'
    result = subprocess.run([str(repo / '.githooks' / hook)], cwd=child, env=env, capture_output=True, text=True)
    assert result.returncode == 37, result.stderr
    invocations = [call for call in calls(env) if 'argv' in call]
    assert invocations[-1] == {'cwd': str(repo), 'argv': ['-m', 'pytest', '-q']}


def test_failed_tests_block_commit_and_success_keeps_commit_message_gate(checkout):
    repo, _, env = checkout
    install(repo)
    stage(repo)
    env = hook_env(repo, env)
    env['HOOK_FIXTURE_EXIT'] = '1'
    assert git(repo, 'commit', '-qm', 'PRSG-57 Synthetic failure', env=env).returncode != 0
    assert git(repo, 'rev-parse', '--verify', 'HEAD').returncode != 0
    env['HOOK_FIXTURE_EXIT'] = '0'
    assert git(repo, 'commit', '-qm', 'Invalid title', env=env).returncode != 0
    assert git(repo, 'commit', '-qm', 'PRSG-57 Synthetic success', env=env).returncode == 0
    assert git(repo, 'config', '--get', 'core.hooksPath').stdout.strip() == '.githooks'


def test_failed_tests_block_push_and_success_allows_local_push(checkout, tmp_path):
    repo, _, env = checkout
    install(repo)
    stage(repo)
    env = hook_env(repo, env)
    assert git(repo, 'commit', '-qm', 'PRSG-57 Synthetic baseline', env=env).returncode == 0
    remote = tmp_path / 'remote.git'
    subprocess.run(['git', 'init', '--bare', '-q', str(remote)], check=True)
    assert git(repo, 'remote', 'add', 'fixture', str(remote)).returncode == 0
    env['HOOK_FIXTURE_EXIT'] = '1'
    assert git(repo, 'push', 'fixture', 'HEAD:refs/heads/fixture', env=env).returncode != 0
    assert git(remote, 'rev-parse', '--verify', 'refs/heads/fixture').returncode != 0
    env['HOOK_FIXTURE_EXIT'] = '0'
    assert git(repo, 'push', 'fixture', 'HEAD:refs/heads/fixture', env=env).returncode == 0
    assert git(remote, 'rev-parse', 'refs/heads/fixture').stdout == git(repo, 'rev-parse', 'HEAD').stdout


@pytest.mark.parametrize('mode', ['version', 'pytest'])
def test_prerequisite_failure_blocks_commit(checkout, mode):
    repo, _, env = checkout
    install(repo)
    stage(repo)
    env['HOOK_FIXTURE_PREREQUISITE'] = mode
    result = git(repo, 'commit', '-qm', 'PRSG-57 Missing prerequisite', env=env)
    assert result.returncode != 0 and 'Python >=3.11 with pytest' in result.stderr
    assert len(calls(env)) == 1, 'Full suite never executes after failed prerequisite'


def test_missing_interpreter_blocks_push_gate(checkout):
    repo, _, env = checkout
    install(repo)
    git(repo, 'config', 'praesagus.testPython', str(repo / 'does-not-exist'))
    result = subprocess.run([str(repo / '.githooks/pre-push')], cwd=repo, env=env, capture_output=True, text=True)
    assert result.returncode != 0 and 'interpreter unavailable' in result.stderr
    assert not Path(env['HOOK_FIXTURE_LOG']).exists()


def test_default_active_python_and_installer_modes(checkout, tmp_path):
    repo, fake, env = checkout
    git(repo, 'config', '--unset', 'praesagus.testPython')
    tools = tmp_path / 'tools'
    tools.mkdir()
    (tools / 'python3').symlink_to(fake)
    env['PATH'] = str(tools) + os.pathsep + env['PATH']
    for hook in (repo / '.githooks').iterdir():
        hook.chmod(0o644)
    install(repo)
    assert all(os.access(hook, os.X_OK) for hook in (repo / '.githooks').iterdir())
    stage(repo)
    assert git(repo, 'commit', '-qm', 'PRSG-57 Active interpreter', env=env).returncode == 0
    assert any(call['argv'] == ['-m', 'pytest', '-q'] for call in calls(env))


@pytest.mark.parametrize('configured', [False, True])
def test_installer_preserves_existing_hooks(checkout, configured):
    repo, _, _ = checkout
    custom = repo / 'custom-hooks' if configured else repo / '.git/hooks'
    custom.mkdir(exist_ok=True)
    hook = custom / 'pre-commit'
    hook.write_text('#!/bin/sh\nexit 23\n')
    hook.chmod(0o755)
    before = hook.read_bytes()
    if configured:
        git(repo, 'config', 'core.hooksPath', 'custom-hooks')
    result = subprocess.run(['sh', 'scripts/install_git_hooks.sh'], cwd=repo, capture_output=True, text=True)
    assert result.returncode != 0 and 'preserved' in result.stderr
    assert hook.read_bytes() == before
    current = git(repo, 'config', '--get', 'core.hooksPath')
    assert current.stdout.strip() == ('custom-hooks' if configured else '')
