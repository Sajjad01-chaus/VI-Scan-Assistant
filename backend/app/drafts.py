"""Format validated dictation fields without adding clinical inference."""
import re

def render_draft_report(findings, transcript):
    groups={'Findings':[], 'Uncertain findings':[], 'Pertinent negatives':[]}
    for finding in findings:
        observation=finding['observation'].strip().rstrip('.!?')
        evidence=finding['evidence'].strip()
        qualified=bool(re.search(r'\b(no|not|without|absent|possible|possibly|suspected|may|might|uncertain)\b',observation,re.I))
        if qualified or (finding['polarity']=='negated' and finding['certainty']=='uncertain'):
            statement=evidence.rstrip('.!?')
        elif finding['certainty']=='not_definite' or finding['polarity']=='unspecified':
            statement=evidence.rstrip('.!?')
        elif finding['polarity']=='negated':
            statement='No evidence of '+observation
        elif finding['certainty']=='uncertain':
            statement='Possible '+observation
        else:
            statement=observation
        site=finding['anatomical_site'].strip()
        if site and site!='unspecified' and site.casefold() not in statement.casefold():
            statement=site[0].upper()+site[1:]+': '+statement[0].lower()+statement[1:]
        else:
            statement=statement[0].upper()+statement[1:]
        if not site or site=='unspecified':statement+=' (site not specified)'
        section='Pertinent negatives' if finding['polarity']=='negated' else 'Uncertain findings' if finding['certainty']!='asserted' else 'Findings'
        line='- '+statement+'.'
        if line not in groups[section]:groups[section].append(line)
    # Retain only explicit recommendation sentences after any spoken correction.
    current=re.split(r'\bcorrection\b[,\s:]*',transcript,flags=re.I)[-1]
    notes=[s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+',current) if re.match(r'^(?:Further\s+.+(?:required|recommended)|Correlate\s+with\b|Recommend(?:ed)?\b)',s.strip(),re.I)]
    sections=['CLINICAL DICTATION DRAFT']
    sections.extend(title+'\n'+'\n'.join(lines) for title,lines in groups.items() if lines)
    if notes:sections.append('Recorded recommendations\n'+'\n'.join('- '+note for note in dict.fromkeys(notes)))
    sections.append('Review status\nDraft based on dictated observations only. Clinician review required; not a signed report.')
    return '\n\n'.join(sections)
