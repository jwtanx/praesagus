"""CI uses one Poetry interpreter; missing research imports fail collection offline."""
import shlex
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest
import yaml
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

ROOT=Path(__file__).resolve().parents[1]


def test_ci_research_install_precedes_tests_in_same_poetry_interpreter():
    workflow=yaml.safe_load((ROOT/'.github/workflows/ci.yml').read_text())
    steps=workflow['jobs']['test']['steps'];runs=[s.get('run','') for s in steps]
    install='poetry run python -m pip install -r scripts/stock-research/requirements.txt "numpy>=1.26.4,<2"'
    matches=[i for i,command in enumerate(runs) if install in command]
    assert len(matches)==1
    at=matches[0]
    commands=runs[at].splitlines()
    assert commands[0]==install
    assert commands[1]=='poetry run python -m pip check'
    assert shlex.split(commands[2])[:4]==['poetry','run','python','-c']
    smoke=shlex.split(commands[2])[4]
    assert 'import numpy, pyarrow, pyarrow.parquet, pandas, sklearn, exchange_calendars, openpyxl' in smoke
    assert "assert numpy.__version__.split('.')[0] == '1'" in smoke
    assert shlex.split(commands[0])[-1]=='numpy>=1.26.4,<2'
    assert any('poetry install ' in command for command in runs[:at])
    assert all(at<i for i,command in enumerate(runs) if ' -m pytest' in command)
    assert any('poetry run python -m pytest -q'==command for command in runs[at+1:])
    assert not any(command.startswith(('pip install -r','python -m pip install -r')) for command in runs)


def test_dependency_split_explains_collection_gap_without_package_migration():
    poetry=tomllib.loads((ROOT/'pyproject.toml').read_text())['tool']['poetry']['dependencies']
    requirements=(ROOT/'scripts/stock-research/requirements.txt').read_text()
    assert 'exchange_calendars' not in poetry and 'openpyxl' not in poetry
    assert 'exchange_calendars>=4.13,<5' in requirements and 'openpyxl>=3.1,<4' in requirements
    reqs={r.name:r for r in (Requirement(line) for line in requirements.splitlines() if line and not line.startswith('#'))}
    assert poetry['numpy']=='^1.26' and poetry['pyarrow']=='^12.0'
    poetry_numpy=SpecifierSet('>=1.26,<2')  # Exact meaning of the declared ^1.26.
    assert Version('1.26.4') in poetry_numpy and Version('1.26.4') in reqs['numpy'].specifier
    assert Version('1.26.0') not in reqs['numpy'].specifier  # Calendar 4.13.2 metadata floor.
    assert Version('2.0') in reqs['numpy'].specifier and Version('2.4.6') in reqs['numpy'].specifier
    assert Version('3.0') not in reqs['numpy'].specifier and Version('2.0') not in poetry_numpy
    ci_numpy=SpecifierSet('>=1.26.4,<2')
    assert Version('1.26.4') in ci_numpy and Version('2.0') not in ci_numpy
    assert Version('2.3.3') in reqs['pandas'].specifier and Version('3.0') not in reqs['pandas'].specifier
    # Historical declaration conflict is reproduced without retaining it in CI.
    old=SpecifierSet('>=2,<3')
    assert not any(v in old and v in poetry_numpy for v in map(Version,['1.26.4','2.0','2.4.6']))


@pytest.mark.parametrize('dependency,testfile',[('exchange_calendars','test_stock_research_universe.py'),('openpyxl','test_stock_research_exports.py')])
def test_missing_poetry_research_dependency_reproduces_exit2_collection_failure(dependency,testfile):
    # Isolated import blocker reproduces the actual collection path, without a
    # network install or assertion about the unavailable remote traceback.
    code='''import importlib.abc,sys
class Missing(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0]==sys.argv[1]:
            raise ModuleNotFoundError('isolated missing dependency: '+fullname,name=fullname)
sys.meta_path.insert(0,Missing())
import pytest
raise SystemExit(pytest.main(['--collect-only','-q',sys.argv[2]]))
'''
    result=subprocess.run([sys.executable,'-c',code,dependency,str(ROOT/'tests'/testfile)],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==2,result.stdout+result.stderr
    assert 'ModuleNotFoundError' in result.stdout and 'isolated missing dependency: '+dependency in result.stdout
    assert 'ERROR collecting' in result.stdout
