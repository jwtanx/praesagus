"""Modern source quality runs in the existing full pytest pre-commit/push gate."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('current_brief_quality',ROOT/'scripts/planning/check_ticket_briefs.py')
quality=importlib.util.module_from_spec(spec);spec.loader.exec_module(quality)
SECTIONS={'Objective':'Human need with explicit boundaries.','Approach':'Inspect the bounded implementation.',
          'Choices':'Preserve authored source words.','Findings':'Implementation is pending; no results claimed.',
          'Tradeoffs':'Keep older history and unsupported facts unchanged.'}


def brief(title='Restore API and CSV Briefs',omit=None):
    return '# PRSG-120 — '+title+'\n\n'+'\n\n'.join('## '+name+'\n\n'+body for name,body in SECTIONS.items() if name!=omit)


def manifest():return {'ticket_key':'PRSG-120','review':{'status':'pending'},'scope_status':'accepted'}


def test_current_modern_briefs_have_authored_quality():
    errors=quality.check_current_briefs(ROOT)
    assert errors==[], '\n'.join(errors)


@pytest.mark.parametrize('title',['restore api and csv briefs','Restore api and CSV Briefs','PRSG-120'])
def test_lowercase_or_missing_title_rejected_without_rewriting(title):
    text=brief(title);original=text
    assert quality.check_brief(manifest(),text)
    assert text==original


@pytest.mark.parametrize('section,field',[('Objective','purpose'),('Approach','approach'),('Choices','choices'),('Findings','findings'),('Tradeoffs','tradeoffs')])
def test_missing_named_context_rejected(section,field):
    assert any('missing decision context: '+field in e for e in quality.check_brief(manifest(),brief(omit=section)))


def test_acronyms_inline_literals_and_explicit_unknown_findings_preserved():
    text=brief('Keep OpenD API, ETag and `openpyxl` Output')
    assert quality.check_brief(manifest(),text)==[]
    assert 'OpenD API, ETag and `openpyxl`' in text and 'pending; no results claimed' in text


def test_explicit_manifest_context_is_a_real_display_source():
    meta=manifest();meta['decision_context']={'choices':'Explicit attributable choice.'}
    assert quality.check_brief(meta,brief(omit='Choices'))==[]


def test_legacy_quality_is_not_retroactively_enforced():
    assert quality.check_brief({'ticket_key':'PRSG-108'},'# PRSG-108 — old api title\n')==[]


def test_current_cli_reports_negative_source(tmp_path):
    folder=tmp_path/'plans/2026-10-16';folder.mkdir(parents=True)
    meta=manifest()|{'spec_path':'plans/2026-10-16/PRSG-120-fixture.md'}
    (folder/'PRSG-120.harness.json').write_text(json.dumps(meta));(tmp_path/meta['spec_path']).write_text(brief(omit='Findings'))
    result=subprocess.run([sys.executable,str(ROOT/'scripts/planning/check_ticket_briefs.py'),'--repo-root',str(tmp_path)],capture_output=True,text=True,timeout=10)
    assert result.returncode==1 and 'missing decision context: findings' in result.stdout
