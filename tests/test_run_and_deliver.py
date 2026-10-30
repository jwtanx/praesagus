"""Wrapper-only fixtures and real bounded synthetic subprocesses; no real evaluation."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'scripts/stock-research/run_and_deliver.py'
spec = importlib.util.spec_from_file_location('run_and_deliver163',SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
MS = 1793293200000


def put(p, value):
    p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    raw = value if type(value) is bytes else m.encoded(value)
    p.write_bytes(raw)
    p.chmod(0o600)
    return dict(path=str(p),sha256=m.sha(raw),bytes=len(raw))


def source_ref(p, *, label=None):
    raw = Path(p).read_bytes()
    return dict(path=str(label or p),sha256=m.sha(raw),bytes=len(raw))


def save_plan(f):
    ref = put(f['root']/'inputs/plan.json',f['plan'])
    f['plan_ref'] = ref
    return ref


def authorize(f):
    ref = save_plan(f)
    p = f['plan']
    review = put(f['root']/'inputs/review.json',dict(approved=True,plan_sha256=ref['sha256'],workflow_id=p['workflow_id']))
    f['approval_ref'] = put(f['root']/'inputs/approval.json',dict(schema_version=1,kind='run-and-deliver-execution',
        approved=True,plan_sha256=ref['sha256'],workflow_id=p['workflow_id'],runner=p['runner'],
        not_before_ms=MS-1000,expires_at_ms=MS+599000,resources=p['resources'],resources_confirmed=True,
        exclusive_local_run_confirmed=True,review_reference=review))
    return f['approval_ref']


@pytest.fixture
def f(tmp_path,monkeypatch):
    tmp_path.chmod(0o700)
    for name in ('attempts','outputs','inputs'):
        (tmp_path/name).mkdir(mode=0o700)
    (tmp_path/'outputs/.run-and-deliver-claims').mkdir(mode=0o700)
    monkeypatch.setattr(m,'now_ms',lambda:MS)
    analysis = put(tmp_path/'inputs/analysis.json',dict(schema_version=1,qualification_policy=None,
        review_at='2026-10-30T01:13:35+08:00',cohorts=[]))
    financial = put(tmp_path/'inputs/financial.json',dict(fixture='Wrapper contract fixture; no financial acceptance.'))
    bundle = put(tmp_path/'inputs/bundle.json',dict(schema_version=1,kind='quality-scorecard-inputs',analysis=analysis,financial_review=financial))
    summary = dict(total=2,scored=1,withheld=1)
    values = {'scorecard.json':m.encoded(dict(summary=summary,review_at='2026-10-30T01:13:35+08:00')),
        'scorecard.csv':b'code,status\nSYNTHETIC,withheld\n', 'scorecard.html':b'<!doctype html><p>Authored fixture</p>',
        'provenance.json':m.encoded(dict(bundle=bundle,operations=dict(provider_calls=0,fit=False,prediction=False,model_artifact_loaded=False)))}
    artifacts = {k:dict(sha256=m.sha(v),bytes=len(v)) for k,v in values.items()}
    plan = dict(schema_version=1,workflow_id='synthetic-one',runner='quality-scorecard161',
        python=source_ref(Path(m.PYTHON).resolve(),label=m.PYTHON),
        runtime_files=[source_ref(ROOT/n) for n in sorted(m.COMMON_FILES|m.QUALITY_FILES)],
        inputs=dict(bundle=bundle,output_parent=str(tmp_path/'outputs')),
        attempt_parent=str(tmp_path/'attempts'),target_claim_parent=str(tmp_path/'outputs/.run-and-deliver-claims'),
        resources=m.LIMITS['quality-scorecard161'],
        expected_outputs=dict(artifacts=artifacts,summary=summary,review_at='2026-10-30T01:13:35+08:00'))
    result = dict(root=tmp_path,plan=plan,values=values,calls=[])
    save_plan(result)

    def child(argv,limits,helper):
        result['calls'].append(list(argv))
        target=Path(plan['inputs']['output_parent'])/('scorecard-'+bundle['sha256'][:20])
        target.mkdir(mode=0o700)
        for name,raw in values.items():
            put(target/name,raw)
        return dict(approved=True,cleanup_verified=True,returncode=0,reason=None,limits=limits,
            peak_group_rss_bytes=2000000,max_sample_gap_seconds=.05,samples=2,elapsed_seconds=.1,
            owned_pid_births={'123':'fixture'},owned_groups={'123':'fixture'},stderr='',
            stdout=json.dumps(dict(status='scorecard-written',folder=str(target),summary=summary,artifacts=artifacts)))
    result['mock_child']=child
    return result


def run(f,mode='inspect'):
    ref=f['plan_ref']
    return m.operate(ref['path'],ref['sha256'],mode,f.get('approval_ref'))


def test_default_inspection_is_read_only_no_evaluator_or_subprocess(f,monkeypatch):
    before={str(p):p.read_bytes() for p in f['root'].rglob('*') if p.is_file()}
    modules=set(sys.modules)
    def forbidden(*a,**k):
        raise AssertionError('Inspection must never dispatch')
    monkeypatch.setattr(subprocess,'Popen',forbidden)
    result=run(f)
    assert result['stage']=='planned' and result['child_invoked'] is False
    assert not ({'evaluation','model','quality_scorecard'}&(set(sys.modules)-modules))
    assert before=={str(p):p.read_bytes() for p in f['root'].rglob('*') if p.is_file()}


def test_explicit_approved_dispatch_and_repeat_recovery(f,monkeypatch):
    authorize(f)
    monkeypatch.setattr(m,'supervise',f['mock_child'])
    result=run(f,'execute')
    assert result['status']=='evaluation-complete' and result['child_invoked'] is True
    argv=f['calls'][0]
    assert argv[:3]==[m.PYTHON,'-I','-B'] and '/runtime/scripts/stock-research/quality_scorecard.py' in argv[3]
    assert argv[4:]==['--bundle',f['plan']['inputs']['bundle']['path'],'--bundle-sha256',
        f['plan']['inputs']['bundle']['sha256'],'--output-parent',f['plan']['inputs']['output_parent']]
    original={str(p):p.read_bytes() for p in f['root'].rglob('*') if p.is_file()}
    recovered=run(f,'recover')
    assert recovered['recovered'] and not recovered['child_invoked']
    assert len(f['calls'])==1 and original=={str(p):p.read_bytes() for p in f['root'].rglob('*') if p.is_file()}
    with pytest.raises(m.Held,match='consumed'):
        run(f,'execute')
    assert len(f['calls'])==1
    runtime=f['root']/'attempts/synthetic-one/runtime'
    assert all(p.stat().st_mode&0o777==0o700 for p in runtime.rglob('*') if p.is_dir())


def test_complete_child_outer_seal_interruption_only_finishes_seal(f,monkeypatch):
    authorize(f)
    monkeypatch.setattr(m,'supervise',f['mock_child'])
    original=m.stage
    def interrupt(directory,name,*a,**kw):
        if name=='delivery.json':
            raise m.Held('simulated-outer-seal-interruption')
        return original(directory,name,*a,**kw)
    monkeypatch.setattr(m,'stage',interrupt)
    with pytest.raises(m.Held,match='simulated'):
        run(f,'execute')
    monkeypatch.setattr(m,'stage',original)
    result=run(f,'recover')
    assert result['status']=='evaluation-complete' and result['child_invoked'] is False and len(f['calls'])==1


def test_child_files_without_supervisor_proof_stay_held(f,monkeypatch):
    authorize(f)
    monkeypatch.setattr(m,'supervise',f['mock_child'])
    original=m.stage
    def interrupt(directory,name,*a,**kw):
        if name=='supervisor.json':
            raise m.Held('simulated-receipt-interruption')
        return original(directory,name,*a,**kw)
    monkeypatch.setattr(m,'stage',interrupt)
    with pytest.raises(m.Held):
        run(f,'execute')
    monkeypatch.setattr(m,'stage',original)
    with pytest.raises(m.Held,match='required-file-missing'):
        run(f,'recover')
    assert len(f['calls'])==1


def test_existing_unclaimed_attempt_is_uncertain(f):
    authorize(f)
    (f['root']/'attempts/synthetic-one').mkdir(mode=0o700)
    with pytest.raises(m.Held,match='consumed'):
        run(f,'execute')
    with pytest.raises(m.Held,match='required-file-missing'):
        run(f,'recover')


def test_different_workflow_ids_cannot_race_one_unfinished_target(f,monkeypatch):
    authorize(f)
    calls=[]
    def failed(*args):
        calls.append(args)
        raise m.Held('uncertain-launch')
    monkeypatch.setattr(m,'supervise',failed)
    with pytest.raises(m.Held,match='uncertain-launch'):
        run(f,'execute')
    f['plan']['workflow_id']='synthetic-two'
    authorize(f)
    with pytest.raises(m.Held,match='target-already-claimed'):
        run(f,'execute')
    assert len(calls)==1


@pytest.mark.parametrize('change', ['unknown','bool-version','bad-alias','command','environment','limits','python',
    'runtime-missing','runtime-duplicate','runtime-foreign','root-overlap','alternate-claim-root','bad-id','bad-output-set','bad-cutoff'])
def test_typed_plan_rejections(f,change):
    p=f['plan']
    if change=='unknown':p['approved']=True
    elif change=='bool-version':p['schema_version']=True
    elif change=='bad-alias':p['runner']='standalone-offline109'
    elif change=='command':p['inputs']['command']='echo arbitrary'
    elif change=='environment':p['env']={'PYTHONPATH':'/tmp'}
    elif change=='limits':p['resources']=p['resources']|dict(retries=True)
    elif change=='python':p['python']['path']='/tmp/foreign-python'
    elif change=='runtime-missing':p['runtime_files'].pop()
    elif change=='runtime-duplicate':p['runtime_files'][-1]=p['runtime_files'][0]
    elif change=='runtime-foreign':p['runtime_files'][0]['path']='/tmp/foreign.py'
    elif change=='root-overlap':p['attempt_parent']=p['target_claim_parent']
    elif change=='alternate-claim-root':p['target_claim_parent']=p['attempt_parent']
    elif change=='bad-id':p['workflow_id']='../other'
    elif change=='bad-output-set':p['expected_outputs']['artifacts'].pop('provenance.json')
    else:p['expected_outputs']['review_at']='2026-10-31T00:00:00Z'
    save_plan(f)
    with pytest.raises((m.Held,ValueError)):
        run(f)


@pytest.mark.parametrize('change',['absent','expired','not-started','too-long','no-reserve','wrong-plan','wrong-id',
    'unapproved','resources','review-hash','review-binding','unknown'])
def test_approval_rejections_do_not_claim_or_dispatch(f,change,monkeypatch):
    authorize(f)
    ref=f['approval_ref'];a=json.loads(Path(ref['path']).read_text())
    if change=='absent':f.pop('approval_ref')
    elif change=='expired':a['expires_at_ms']=MS
    elif change=='not-started':a['not_before_ms']=MS+1
    elif change=='too-long':a['expires_at_ms']=MS+700000
    elif change=='no-reserve':a['expires_at_ms']=MS+62000
    elif change=='wrong-plan':a['plan_sha256']='f'*64
    elif change=='wrong-id':a['workflow_id']='foreign'
    elif change=='unapproved':a['approved']=False
    elif change=='resources':a['resources']=a['resources']|dict(rss_bytes=1)
    elif change=='review-hash':a['review_reference']['sha256']='f'*64
    elif change=='review-binding':a['review_reference']=put(f['root']/'inputs/review.json',dict(approved=True,plan_sha256='f'*64,workflow_id=a['workflow_id']))
    else:a['unknown']=True
    if change!='absent':f['approval_ref']=put(Path(ref['path']),a)
    with pytest.raises(m.Held):
        run(f,'execute')
    assert not list((f['root']/'attempts').iterdir()) and not list((f['root']/'outputs/.run-and-deliver-claims').iterdir())


@pytest.mark.parametrize('file',['scorecard.json','scorecard.csv','scorecard.html','provenance.json'])
def test_post_delivery_tamper_is_not_recovered(f,monkeypatch,file):
    authorize(f);monkeypatch.setattr(m,'supervise',f['mock_child']);result=run(f,'execute')
    p=Path(result['result']['folder'])/file
    p.write_bytes(b'tampered')
    with pytest.raises(m.Held,match='artifact-mismatch'):
        run(f,'recover')
    assert len(f['calls'])==1


@pytest.mark.parametrize('field,value',[('cleanup_verified',False),('approved',False),('peak_group_rss_bytes',0),
    ('max_sample_gap_seconds',2),('returncode',False),('owned_pid_births',{}),('elapsed_seconds',63)])
def test_recovery_requires_original_successful_resource_gate(f,monkeypatch,field,value):
    authorize(f);monkeypatch.setattr(m,'supervise',f['mock_child']);run(f,'execute')
    p=f['root']/'attempts/synthetic-one/supervisor.json';d=json.loads(p.read_text());d['result'][field]=value;put(p,d)
    with pytest.raises(m.Held,match='original-supervision-required'):
        run(f,'recover')


def test_quality_cannot_adopt_unsupervised_foreign_outputs(f):
    attempt=f['root']/'attempts/synthetic-one';attempt.mkdir(mode=0o700)
    put(attempt/'claim.json',dict(plan_sha256=f['plan_ref']['sha256'],recorded_at_ms=MS,
        runner=f['plan']['runner'],target=str(f['root']/'outputs'/('scorecard-'+f['plan']['inputs']['bundle']['sha256'][:20])),mode='adopt-historical-us30'))
    with pytest.raises(m.Held,match='adoption-binding'):
        run(f,'recover')


def test_snapshot_tamper_held_without_second_child(f,monkeypatch):
    authorize(f);monkeypatch.setattr(m,'supervise',f['mock_child']);run(f,'execute')
    p=f['root']/'attempts/synthetic-one/runtime/scripts/stock-research/quality_scorecard.py';p.write_bytes(b'changed')
    with pytest.raises(m.Held,match='snapshot-changed'):
        run(f,'recover')
    assert len(f['calls'])==1


def test_target_claim_tamper_held(f,monkeypatch):
    authorize(f);monkeypatch.setattr(m,'supervise',f['mock_child']);run(f,'execute')
    put(next((f['root']/'outputs/.run-and-deliver-claims').iterdir()),dict(plan_sha256='f'*64))
    with pytest.raises(m.Held,match='target-claim-binding'):
        run(f,'recover')


@pytest.mark.parametrize('change',['symlink','permissions','source-hash','private-overlap','bool-bytes'])
def test_safe_input_failures(f,change):
    if change=='symlink':
        p=Path(f['plan']['inputs']['bundle']['path']);p.rename(p.with_name('real.json'));p.symlink_to(p.with_name('real.json'))
    elif change=='permissions':Path(f['plan']['inputs']['bundle']['path']).chmod(0o644)
    elif change=='source-hash':f['plan']['runtime_files'][0]['sha256']='f'*64
    elif change=='private-overlap':f['plan']['inputs']['output_parent']=str(ROOT)
    else:f['plan']['inputs']['bundle']['bytes']=True
    save_plan(f)
    with pytest.raises(m.Held):run(f)


def us_plan(f):
    s=importlib.util.spec_from_file_location('_delivery_test_builders',ROOT/'tests/test_delivery_readiness.py')
    builders=importlib.util.module_from_spec(s);s.loader.exec_module(builders)
    usroot=f['root']/'us';usroot.mkdir(mode=0o700)
    us=builders.build_us(usroot)
    (usroot/'runs').chmod(0o700)
    (usroot/'runs/.run-and-deliver-claims').mkdir(mode=0o700)
    f['plan']['target_claim_parent']=str(usroot/'runs/.run-and-deliver-claims')
    fixed=builders.build_fixed(usroot)
    inspection=put(usroot/'inspection.json',dict(schema_version=1,read_roots=[str(usroot)],
        products=[fixed,us,dict(product='standalone100',manifest=None)]))
    p=f['plan'];p.update(runner='us30-reviewed155',resources=m.LIMITS['us30-reviewed155'],
        runtime_files=[source_ref(ROOT/n) for n in sorted(m.COMMON_FILES)],
        inputs=dict(bundle=us['bundle'],child_release=us['release'],inspection_bundle=inspection),expected_outputs=None)
    save_plan(f)
    return us


def test_historical155_recovery_uses_original_receipts_no_model(f,monkeypatch):
    us_plan(f)
    def no_run(*args):raise AssertionError('Historical recovery must not dispatch')
    monkeypatch.setattr(m,'supervise',no_run)
    before={str(p):p.read_bytes() for p in (f['root']/'us').rglob('*') if p.is_file()}
    result=run(f,'recover');assert result['status']=='forecast-complete' and result['adopted_historical']
    assert result['result']['counts']['available']==120
    assert run(f,'recover')['child_invoked'] is False
    view=run(f)['current_readiness'];assert view['products'][2]['unnamed_slots']==100
    assert before=={str(p):p.read_bytes() for p in (f['root']/'us').rglob('*') if p.is_file()}


def test155_exact_public_argv_and_expired_child_release_hold(f):
    us=us_plan(f);context=m.prepare(f['plan_ref']['path'],f['plan_ref']['sha256'])
    assert context['argv']==[m.PYTHON,'-I','-B',str(ROOT/'scripts/stock-research/run_reviewed_batch.py'),
        '--bundle',us['bundle']['path'],'--bundle-sha256',us['bundle']['sha256'],'--release',us['release']['path']]
    authorize(f)
    with pytest.raises(m.Held,match='child-release-window'):
        run(f,'execute')
    assert not list((f['root']/'attempts').iterdir())


def test155_foreign_inspection_target_rejected(f):
    us_plan(f);ref=f['plan']['inputs']['inspection_bundle'];d=json.loads(Path(ref['path']).read_text());d['products'][1]['attempt']+='_foreign';f['plan']['inputs']['inspection_bundle']=put(Path(ref['path']),d);save_plan(f)
    with pytest.raises(m.Held,match='inspection-target-binding'):run(f)


@pytest.mark.parametrize('field,value',[('child_sha256','f'*64),('adopted_historical',True)])
def test_sealed_redundant_metadata_is_bound(f,monkeypatch,field,value):
    authorize(f);monkeypatch.setattr(m,'supervise',f['mock_child']);run(f,'execute')
    p=f['root']/'attempts/synthetic-one/delivery.json';d=json.loads(p.read_text());d[field]=value;put(p,d)
    with pytest.raises(m.Held,match='delivery-evidence-binding'):run(f,'recover')


def test_readonly_inspection_reports_durable_stage_without_writes(f,monkeypatch):
    authorize(f);monkeypatch.setattr(m,'supervise',f['mock_child']);run(f,'execute')
    before={str(p):p.read_bytes() for p in f['root'].rglob('*') if p.is_file()}
    assert run(f)['stage']=='outer-delivered'
    assert before=={str(p):p.read_bytes() for p in f['root'].rglob('*') if p.is_file()}
    attempt=f['root']/'attempts/synthetic-one'
    (attempt/'delivery.json').unlink();assert run(f)['stage']=='child-verified'
    (attempt/'child-verified.json').unlink();assert run(f)['stage']=='child-finished-supervisor-recorded'
    assert not (attempt/'child-verified.json').exists()
    (attempt/'supervisor.json').unlink();assert run(f)['stage']=='dispatch-uncertain'
    (attempt/'dispatch-intent.json').unlink();assert run(f)['stage']=='claimed'
    (attempt/'claim.json').unlink();assert run(f)['stage']=='interrupted-before-claim'


@pytest.mark.parametrize('raw',[b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":1e999}',b'['*40+b'0'+b']'*40])
def test_malformed_control_json(raw):
    with pytest.raises(m.Held):m.decode(raw)


def test_isolated_cli_from_clean_directory(f):
    r=subprocess.run([sys.executable,'-I','-B',str(SCRIPT),'--plan',f['plan_ref']['path'],
        '--plan-sha256',f['plan_ref']['sha256']],cwd='/tmp',capture_output=True,text=True,timeout=10)
    assert r.returncode==0 and json.loads(r.stdout)['child_invoked'] is False and not r.stderr


def helper():
    p=ROOT/'scripts/stock-research/run_reviewed_batch.py'
    return m.module_from_bytes('_test_supervisor_primitives',p,p.read_bytes())


def test_real_mock_child_supervision_and_bounded_pipes():
    result=m.supervise([sys.executable,'-I','-B','-c','import time;print("fixture-only");time.sleep(.15)'],
        dict(work_seconds=2,cleanup_seconds=1,rss_bytes=536870912,threads=1,retries=0),helper())
    assert result['approved'] and result['cleanup_verified'] and result['stdout']=='fixture-only\n'
    assert result['peak_group_rss_bytes']>0 and result['owned_pid_births']


@pytest.mark.parametrize('code,reason',[
    ('import time;time.sleep(30)','execution-timeout'),
    ('import sys,time;sys.stdout.write("x"*70000);sys.stdout.flush();time.sleep(1)','child-output-budget')])
def test_real_mock_child_timeout_and_output_limit(code,reason):
    result=m.supervise([sys.executable,'-I','-B','-c',code],
        dict(work_seconds=.4,cleanup_seconds=1,rss_bytes=536870912,threads=1,retries=0),helper())
    assert not result['approved'] and result['cleanup_verified'] and result['reason']==reason,result
    assert len(result['stdout'].encode())<=65536
