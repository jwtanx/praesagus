# PRSG-56 Deterministic check-evidence regression

Type bug · Modules harness · Owner Engineer · Priority P1 · Effort XS (0.1–0.4 days) · Impact medium: restore meaningful validator regression independent of ticket progress.
Created2026-10-05MYT. Human requestedfixCI. Frozen base 35e3e315fb89be28b73e77b268086f19a52a9b38.

## Reproduction and expected behavior
IsolatedPython3.11.17 fullpytest1failed1090passed; test_check_pass_needs_evidence loads realPRSG1manifest, marks passed but leaves legitimate evidence intact, so validator correctly accepts. CIremoteexit2 not yet explained by localexit1. Expected: rejection fixture explicitly removes evidence; nonempty evidence remains valid. Do not remove PRSG1evidence/changevalidator/skiptest.

## Frozen scope
Only tests/test_ticket_harness.py functional change plus thisspec/manifest. Parameterize terminal passed/failed status and absent/empty evidence rejection; add explicit nonempty evidence acceptance. Retain checked-in-manifest coverage and other assertions. Preserve untrackedPRSG55plans. No workflow/dependency/runtime changes in this ticket. Run isolated3.11 focused test_ticket_harness, fullpytest and test_ticket_verification. Record interpreter/subsetdependency limitation, no fullPoetryparity claim. Leave Lead review pending; no commit/push byEngineer.

## When it's considered done
- [x] PRSG-56-D1: Failing-before/rejection+acceptance regressions and full local suite pass.
- [ ] PRSG-56-D2: Lead independently reviews scope, verifies tests/push and observes remoteCI result; remote failure remains separately diagnosed if different.


## Engineer implementation and environment

Rejection cases use an appended standalone synthetic command check with a unique ID, terminal passed/failed status and deliberately absent/empty evidence. Acceptance cases use the same standalone check with nonempty synthetic evidence. This preserves live ticket evidence and acceptance references, including future completed checklists; no validator or other assertions changed.

Before fix, isolated Python3.11.17 full replay failed `test_check_pass_needs_evidence`:1 failed,1090 passed in33.10s; the targeted old test also failed alone in0.03s. Final focused command `/tmp/praesagus-ci-repro-20261005/bin/python -m pytest -q tests/test_ticket_harness.py` passed57 tests in0.07s. Safety command `/tmp/praesagus-ci-repro-20261005/bin/python -m pytest -q tests/test_ticket_verification.py` passed15 in2.63s. All commands use repository root. Logs: `/tmp/PRSG-CI-311-full-20261005.log`, `/tmp/PRSG-CI-311-focused-20261005.log`, `/tmp/PRSG-56-focused.log`, `/tmp/PRSG-56-full.log`, `/tmp/PRSG-56-safety.log`.

Interpreter is isolated CPython3.11.17 installed outside repository using uv0.12.23 and its official managed distribution; no model weights/providers/credentials were used. Test environment has only selected required test dependencies, not the canonical complete Poetry resolution or Linux platform. Exact installed dependency snapshot:

```text
anyio==4.15.1
boto3==1.43.108
botocore==1.43.108
certifi==2026.7.22
cffi==2.1.1
charset-normalizer==3.5.2
cryptography==50.0.2
fastapi==0.95.2
h11==0.16.0
httpcore==1.0.9
httpx==0.27.2
idna==3.20
iniconfig==2.3.0
jmespath==1.1.0
markupsafe==3.0.4
moto==5.2.3
packaging==26.3
pluggy==1.6.0
prometheus-client==0.16.0
pycparser==3.0
pydantic==1.10.26
pygments==2.21.0
pytest==8.4.2
python-dateutil==2.9.0.post0
pyyaml==6.0.3
requests==2.34.2
responses==0.26.3
s3transfer==0.19.2
six==1.17.0
sniffio==1.3.1
starlette==0.27.0
typing-extensions==4.16.0
urllib3==2.8.0
werkzeug==3.1.9
xmltodict==1.0.4
```

Full-suite invocation is `PATH=/tmp/praesagus-ci-repro-20261005/bin:$PATH AWS_EC2_METADATA_DISABLED=true AWS_ACCESS_KEY_ID=testing AWS_SECRET_ACCESS_KEY=testing AWS_DEFAULT_REGION=us-east-1 PRAESAGUS_API_KEY= /tmp/praesagus-ci-repro-20261005/bin/python -m pytest -q`. AWS values are synthetic test values; metadata lookup disabled. No repository dependency/workflow changes. CI's observed exit2 differs from the reproduced local exit1, so remote cause/parity is not established until Lead inspects the new remote run. No skip or weakened validator, no PRSG-1 evidence removed. PRSG-55 plans preserved. Lead acceptance/remote verification and D2 remain pending; no commit/push by Engineer.

Final full replay after standalone-check refinement:1096 passed,11 warnings in31.49s, exit0. Three-path manifest validation and `git diff --check` passed. D1 demonstrated; D2 and Lead review remain pending.
