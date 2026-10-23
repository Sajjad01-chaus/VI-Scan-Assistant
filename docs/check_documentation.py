"""Check local links, canonical diagrams and current evidence counts."""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[1]
errors=[]
documents=[ROOT/'README.md',*sorted((ROOT/'docs').glob('*.md')),*sorted((ROOT/'verification').glob('*.md'))]
links=0
for document in documents:
    for raw in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',document.read_text(encoding='utf-8-sig')):
        target=raw.strip().split(' "')[0].strip('<>')
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'):continue
        target=unquote(target.split('#')[0])
        if target:
            links+=1
            if not (document.parent/target).exists():errors.append(f'{document.relative_to(ROOT)}: missing {target}')
design=(ROOT/'docs/system-design.md').read_text(encoding='utf-8-sig')
blocks=re.findall(r'```mermaid\n(.*?)\n```',design,re.S)
names=['system-architecture','retrieval','dictation','voice-sequence','voice-state','data-model']
if len(blocks)!=len(names):errors.append('Expected six canonical Mermaid blocks')
for name,block in zip(names,blocks):
    if (ROOT/f'docs/diagrams/{name}.mmd').read_text(encoding='utf-8').strip()!=block.strip():errors.append(f'Mermaid source differs: {name}')
suites=ET.parse(ROOT/'verification/tests.xml').getroot().findall('.//testsuite')
tests=sum(int(s.attrib['tests']) for s in suites)
failures=sum(int(s.attrib.get('failures',0))+int(s.attrib.get('errors',0)) for s in suites)
for name in ['README.md','docs/system-design.md','docs/implementation-status.md','docs/REQUIREMENTS-CHECKLIST.md','docs/FOUR-MINUTE-DEMO.md']:
    if str(tests) not in (ROOT/name).read_text(encoding='utf-8-sig'):errors.append(f'Current test count missing: {name}')
if failures:errors.append('Latest test evidence contains failures/errors')
result={'documents':len(documents),'checked_local_links':links,'canonical_mermaid_sources':len(blocks),'recorded_tests':tests,'recorded_failures':failures,'errors':errors,'limits':'Local consistency check only; historical failure-log counts are intentionally retained. External URLs and actual device/provider behavior were not retested.'}
(ROOT/'verification/documentation-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
if errors:raise SystemExit(1)
