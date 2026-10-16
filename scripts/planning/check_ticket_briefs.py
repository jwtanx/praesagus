"""Current modern brief quality only; never revalidate or rewrite Git history."""
import argparse
import importlib.util
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
MODERN_MIN_TICKET=109
MINOR_WORDS={'a','an','and','as','at','but','by','for','from','in','of','on','or','per','the','to','via','vs','with'}
_spec=importlib.util.spec_from_file_location('brief_quality_audit',Path(__file__).with_name('build_ticket_audit.py'))
_audit=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_audit)


def check_brief(manifest,text):
    """Validate effective display fields, retaining exact source spelling/content."""
    key=manifest.get('ticket_key','')
    match=re.fullmatch(r'PRSG-(0|[1-9][0-9]*)',key)
    if not match:raise ValueError('invalid-ticket-key')
    if int(match[1])<MODERN_MIN_TICKET:return []
    errors=[]
    heading=re.search(r'^#\s+(.+?)\s*#*$',text,re.M)
    title=_audit.normalize_title(heading[1],key) if heading else ''
    # Authored inline code may intentionally retain package/product spelling.
    words=re.findall(r'[A-Za-z][A-Za-z0-9]*',re.sub(r'`[^`]+`','',title))
    if not heading or not words or title=='Untitled':errors.append('missing authored title')
    elif any(not word[0].isupper() and not (0<i<len(words)-1 and word in MINOR_WORDS) for i,word in enumerate(words)):
        errors.append('title requires authored Title Case; preserve acronyms/literal code, do not auto-capitalize')
    context=_audit.extract_context(manifest,text,'')
    for field in _audit.CONTEXT_FIELDS:
        if not context['fields'][field]['text']:errors.append('missing decision context: '+field)
    return [key+': '+error for error in errors]


def check_current_briefs(root=ROOT):
    root=Path(root).resolve();errors=[]
    for path in sorted((root/'plans').glob('*/*.harness.json')):
        filename=re.fullmatch(r'(PRSG-(0|[1-9][0-9]*))\.harness\.json',path.name)
        if not filename or int(filename[2])<MODERN_MIN_TICKET:continue
        try:
            manifest=json.loads(path.read_text())
            if not isinstance(manifest,dict) or manifest.get('ticket_key')!=filename[1] or not isinstance(manifest.get('review'),dict):
                raise ValueError('invalid modern brief metadata')
            spec=(root/manifest['spec_path']).resolve()
            if not spec.is_relative_to(root/'plans'):raise ValueError('brief path outside plans')
            errors.extend(check_brief(manifest,spec.read_text()))
        except (OSError,ValueError,KeyError,TypeError) as error:
            errors.append(str(path.relative_to(root))+': invalid current brief ('+type(error).__name__+')')
    return errors


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo-root',type=Path,default=ROOT)
    args=parser.parse_args();errors=check_current_briefs(args.repo_root)
    if errors:print('\n'.join(errors));return 1
    print('Current modern ticket briefs: authored titles and five context fields valid');return 0


if __name__=='__main__':raise SystemExit(main())
