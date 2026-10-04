"""Fresh-process local helper resolution despite an unrelated installed package."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_competing_tests_package_cannot_shadow_helpers_or_collection(tmp_path):
    shadow = tmp_path / 'unrelated-dependency'
    package = shadow / 'tests'
    package.mkdir(parents=True)
    (package / '__init__.py').write_text('UNRELATED_PACKAGE = True\n')
    # No inherited credentials or account environment enters the child fixtures.
    env = {'PATH': os.environ['PATH'], 'LANG': 'C', 'PYTHONPATH': str(shadow)}
    command = [sys.executable, '-m', 'pytest', '--collect-only', '-q',
               'tests/test_daily_quote_report.py', '--tb=short']
    collision = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=30)
    assert collision.returncode == 0, collision.stdout + collision.stderr
    nodes = [line for line in collision.stdout.splitlines() if line.startswith('tests/test_daily_quote_report.py::')]
    assert nodes, 'Existing real quote-report cases must still collect'
    baseline = subprocess.run(command, cwd=ROOT, env={key: value for key, value in env.items() if key != 'PYTHONPATH'},
                              capture_output=True, text=True, timeout=30)
    assert baseline.returncode == 0, baseline.stdout + baseline.stderr
    assert nodes == [line for line in baseline.stdout.splitlines() if line.startswith('tests/test_daily_quote_report.py::')]
    code = ('from pathlib import Path; import tests; import tests.test_daily_report_projection as helper; '
            f'assert Path(tests.__file__).resolve() == Path({str(ROOT / "tests/__init__.py")!r}); '
            f'assert Path(helper.__file__).resolve() == Path({str(ROOT / "tests/test_daily_report_projection.py")!r}); '
            'assert callable(helper.inputs)')
    resolution = subprocess.run([sys.executable, '-c', code], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=30)
    assert resolution.returncode == 0, resolution.stdout + resolution.stderr
