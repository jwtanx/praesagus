"""Manual export boundaries with fictional evidence, isolated Git and no provider access."""
import csv
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
RELATIVE = Path('scripts/daily-market-brief/run_private_forecast.sh')
ADAPTER = (ROOT / RELATIVE).read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / 'checkout with spaces'
    target = root / RELATIVE
    target.parent.mkdir(parents=True)
    for name in ('run_private_forecast.sh', 'prepare_private_forecast.py', 'prepare_forecast_report.py'):
        shutil.copy2(ROOT / RELATIVE.parent / name, target.parent / name)
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    return root


def configure(root, executable):
    subprocess.run(['git', '-C', str(root), 'config', 'praesagus.testPython', str(executable)], check=True)


def run(root, args, **options):
    return subprocess.run(['sh', str(root / RELATIVE), *args], cwd=root.parent,
                          capture_output=True, text=True, timeout=15, **options)


def fake_python(tmp_path, *, exit_code=0, probe_code=0, name='python with spaces'):
    path = tmp_path / name
    log = tmp_path / (name + '.json')
    path.write_text(f'''#!{sys.executable}
import json, sys
from pathlib import Path
if sys.argv[1] == '-c':
    sys.exit({probe_code})
Path({str(log)!r}).write_text(json.dumps(dict(argv=sys.argv[1:], stdin=sys.stdin.read())))
print('{{"status":"withheld","counts":{{"total":0}},"csv_path":"/fictional/forecasts.csv"}}')
sys.exit({exit_code})
''')
    path.chmod(0o700)
    return path, log


def test_configured_executable_spaces_and_literal_arguments_without_shell_execution(checkout, tmp_path):
    executable, log = fake_python(tmp_path)
    configure(checkout, executable)
    canary = tmp_path / 'MUST_NOT_EXIST'
    batch = f'/private/batch $(touch {canary}); `false` * .json'
    parent = '/private/output ; $HOME "literal"'
    result = run(checkout, ['--batch', batch, '--output-parent', parent])
    assert result.returncode == 0 and result.stderr == ''
    recorded = json.loads(log.read_text())
    assert recorded['argv'] == ['-', str(checkout), batch, parent]
    assert recorded['stdin'] == ADAPTER + '\n'
    assert not canary.exists()


@pytest.mark.parametrize('args', [[], ['--batch'], ['--batch', '', '--output-parent', '/p'],
    ['--batch', '/b'], ['--output-parent', '/p'],
    ['--batch', '/a', '--batch', '/b', '--output-parent', '/p'],
    ['--batch', '/b', '--output-parent', '/p', '--output-parent', '/q'],
    ['--batch', '/b', '--output-parent', '/p', '--issued-at', 'yesterday'],
    ['--batch', '/b', '--output-parent', '/p', '--unknown'], ['--help', '--batch', '/b']])
def test_invalid_options_fail_before_interpreter(checkout, tmp_path, args):
    executable, log = fake_python(tmp_path)
    configure(checkout, executable)
    result = run(checkout, args)
    assert result.returncode == 1 and result.stderr == '' and not log.exists()
    assert json.loads(result.stdout) == dict(status='failed', reason='arguments-invalid')


def test_help_needs_no_interpreter(checkout):
    configure(checkout, '/missing/PRIVATE_CANARY')
    result = run(checkout, ['--help'])
    assert result.returncode == 0 and result.stderr == ''
    assert '--batch' in result.stdout and '--output-parent' in result.stdout
    assert 'PRIVATE_CANARY' not in result.stdout


@pytest.mark.parametrize('missing', [True, False])
def test_missing_or_unsupported_configured_python_is_sanitized_without_fallback(checkout, tmp_path, missing):
    executable, log = fake_python(tmp_path, probe_code=1)
    configure(checkout, tmp_path / 'PRIVATE_CANARY_missing' if missing else executable)
    result = run(checkout, ['--batch', '/b', '--output-parent', '/p'])
    assert result.returncode == 1 and result.stderr == '' and not log.exists()
    assert json.loads(result.stdout) == dict(status='failed', reason=(
        'interpreter-unavailable' if missing else 'interpreter-unsupported'))
    assert 'PRIVATE_CANARY' not in result.stdout


def test_unset_config_discovers_python3_and_preserves_process_failure(checkout, tmp_path):
    _, log = fake_python(tmp_path, name='python3', exit_code=73)
    result = run(checkout, ['--batch', '/b', '--output-parent', '/p'],
                 env=dict(os.environ, PATH=str(tmp_path) + os.pathsep + os.environ['PATH']))
    assert result.returncode == 73 and result.stderr == '' and log.exists()


@pytest.mark.parametrize('failure', [None, 'read', 'prepare', 'write', 'import'])
def test_adapter_single_utc_clock_and_sanitized_stage_errors(monkeypatch, capsys, tmp_path, failure):
    samples = []
    calls = []
    parent = tmp_path / 'private'
    parent.mkdir(mode=0o700)

    class Clock(datetime.datetime):
        @classmethod
        def now(cls, zone):
            samples.append(zone)
            return cls(2026, 10, 21, 21, 0, tzinfo=zone)

    def step(name, value):
        calls.append(name)
        if failure == name:
            raise RuntimeError('PRIVATE_CANARY /private/secret-batch.json')
        return value

    payload = object()
    counts = dict(total=1, generated=1, withheld=0, is_demo=1)

    def prepare(actual, **kwargs):
        assert actual is payload
        assert kwargs == dict(batch_mode=True, issued_at='2026-10-21T21:00:00+00:00',
                              report_cutoff='2026-10-21T21:00:00+00:00')
        return step('prepare', dict(counts=counts))

    directory = parent / 'actual-writer-folder'

    def load(module):
        step('import', None)
        module.private_io = SimpleNamespace(
            read_private_json=lambda value, **kw: step('read', payload),
            _path=lambda value: Path(value),
            _directory=lambda value: os.open(value, os.O_RDONLY | os.O_DIRECTORY))
        module.need = lambda value: value or (_ for _ in ()).throw(ValueError())
        module.prepare_export = prepare
        module.write_export = lambda value, result: step('write', directory)

    monkeypatch.setattr(datetime, 'datetime', Clock)
    monkeypatch.setattr(sys, 'argv', ['-', str(ROOT), '/private/input.json', str(parent)])
    monkeypatch.setattr(importlib.util, 'spec_from_file_location', lambda *a: SimpleNamespace(loader=SimpleNamespace(exec_module=load)))
    monkeypatch.setattr(importlib.util, 'module_from_spec', lambda *a: SimpleNamespace())
    if failure:
        with pytest.raises(SystemExit) as error:
            exec(compile(ADAPTER, '<launcher>', 'exec'), {})
        assert error.value.code == 1
    else:
        exec(compile(ADAPTER, '<launcher>', 'exec'), {})
    output = capsys.readouterr()
    assert output.err == '' and 'PRIVATE_CANARY' not in output.out and 'Traceback' not in output.out
    assert samples == ([] if failure in ('read', 'import') else [datetime.timezone.utc])
    summary = json.loads(output.out)
    if failure:
        reason = {'read': 'private-input-invalid', 'prepare': 'preparation-invalid',
                  'write': 'private-write-failed', 'import': 'exporter-unavailable'}[failure]
        assert summary == dict(status='failed', reason=reason)
        assert calls[-1] == failure
    else:
        assert summary == dict(status='prepared', counts=counts, csv_path=str(directory / 'forecasts.csv'))


@pytest.mark.parametrize('kind', ['generated', 'expired', 'missing-pair', 'malformed', 'missing-file'])
def test_real_private_export_no_network_and_no_input_rewrites(checkout, tmp_path, kind):
    configure(checkout, sys.executable)
    private = tmp_path / 'private with spaces'
    private.mkdir(mode=0o700)
    parent = private / 'exports'
    parent.mkdir(mode=0o700)
    spec = importlib.util.spec_from_file_location('manual_authored_cases', ROOT / 'tests/test_forecast_scenario.py')
    cases = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cases)
    evidence, admission, _, _ = cases.private_case('legacy-raw')
    evidence['classification'] = 'authored_fixture'
    cases.reseal(evidence, admission)
    item = dict(ticker='SPY', market='US', currency='USD', evidence=evidence, admission=admission)
    if kind == 'missing-pair':
        item.update(evidence=None, admission=None)
    batch = private / 'reviewed batch.json'
    batch.write_text(json.dumps(dict(schema_version=1, items=[item]) if kind != 'malformed' else {'PRIVATE_CANARY': True}))
    batch.chmod(0o600)
    before = batch.read_bytes()
    if kind == 'missing-file':
        batch.unlink()
    # Test-only process clock and socket ban; the production launcher has no clock override.
    support = tmp_path / 'support'
    support.mkdir()
    instant = '2026-10-23T21:00:00+00:00' if kind == 'expired' else '2026-10-21T21:00:00+00:00'
    network_attempt = tmp_path / 'network-attempt'
    (support / 'sitecustomize.py').write_text(f'''
import datetime, socket
from pathlib import Path
class Frozen(datetime.datetime):
    @classmethod
    def now(cls, tz=None):
        value=cls.fromisoformat({instant!r})
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)
datetime.datetime=Frozen
def denied(*args, **kwargs):
    Path({str(network_attempt)!r}).write_text('denied')
    raise RuntimeError('network forbidden in fixture')
socket.socket.connect=denied
socket.socket.connect_ex=denied
socket.create_connection=denied
''')
    result = run(checkout, ['--batch', str(batch), '--output-parent', str(parent)],
                 env=dict(os.environ, PYTHONPATH=os.pathsep.join([str(support), str(ROOT)])))
    assert not network_attempt.exists()
    assert result.stderr == '' and 'PRIVATE_CANARY' not in result.stdout
    summary = json.loads(result.stdout)
    if kind in ('malformed', 'missing-file'):
        assert result.returncode == 1 and summary['status'] == 'failed'
        assert not list(parent.iterdir()) and str(private) not in result.stdout
    else:
        assert result.returncode == 0
        path = Path(summary['csv_path'])
        assert path.parent.parent == parent and path.name == 'forecasts.csv'
        assert {p.name for p in path.parent.iterdir()} == {'forecasts.csv', 'private-audit.json', 'manifest.json'}
        with path.open() as stream:
            row, = list(csv.DictReader(stream))
        expected = 'generated' if kind == 'generated' else 'withheld'
        assert row['status'] == expected
        assert row['issued_at'] == row['report_cutoff'] == instant
        assert summary['counts'] == dict(total=1, generated=int(kind == 'generated'),
                                         withheld=int(kind != 'generated'), is_demo=int(kind != 'missing-pair'))
        if kind == 'generated':
            assert row['classification'] == 'fixture_only' and row['point'] != ''
        else:
            assert row['point'] == '' and row['reasons']
        manifest = json.loads((path.parent / 'manifest.json').read_text())
        assert manifest['artifacts']['forecasts.csv']['sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
        assert path.stat().st_mode & 0o777 == 0o600
        assert path.parent.stat().st_mode & 0o777 == 0o700
    if batch.exists():
        assert batch.read_bytes() == before
