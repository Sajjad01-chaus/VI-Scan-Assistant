"""Render concise answers from exact report excerpts, never model-authored claims."""
import re
from fastapi import HTTPException


def all_reports_requested(request):
    text=request.casefold()
    return bool(re.search(r'\b(?:all|every|each|both)\b.{0,65}\breports?\b|\breports?\b.{0,35}\b(?:all|every|each|both)\b|\b(?:entire|complete|full)\s+(?:report|reporting)\s+history\b',text))


def readable_excerpt(quote):
    technique={
        'Synthetic panoramic dental radiograph text scenario.':'The mock report describes a panoramic dental X-ray (OPG).',
        'No definite carious lesion is established in the described tooth; early disease is not excluded.':'The report does not confirm tooth decay in that tooth, but early decay cannot be ruled out.',
    }
    if quote in technique:return technique[quote]
    impacted=re.fullmatch(r'(Lower (?:left|right)) third molar is horizontally impacted\.',quote,re.I)
    if impacted:return f'The {impacted[1].lower()} wisdom tooth is lying sideways and is impacted (stuck).'
    impacted=re.fullmatch(r'Horizontally impacted (lower (?:left|right)) third molar\.',quote,re.I)
    if impacted:return f'The {impacted[1].lower()} wisdom tooth is lying sideways and is impacted (stuck).'
    erupted=re.fullmatch(r'(Lower (?:left|right)) third molar is partially erupted\.',quote,re.I)
    if erupted:return f'The {erupted[1].lower()} wisdom tooth has only partly come through the gum.'
    if quote in {
        'The relationship to the inferior alveolar canal cannot be determined confidently on this panoramic examination.',
        'The relationship to the inferior alveolar canal cannot be determined confidently in this recorded field.',
    }:return 'The report cannot clearly establish how the tooth relates to the nerve canal in the lower jaw.'
    if quote=='Superimposition limits assessment of the apices.':
        return 'Overlapping structures make the root tips difficult to assess.'
    match=re.fullmatch(r'Possible periapical radiolucency near (.+)\.',quote,re.I)
    if match:
        return f'The report notes a possible darker area near the root tip of {match[1]}.'
    quote=re.sub(r'\bperiapical radiolucency\b','darker area near a root tip',quote,flags=re.I)
    quote=quote.replace('not a definitive diagnosis','not a confirmed diagnosis')
    return re.sub(r'\bcaries\b','tooth decay',quote,flags=re.I)


def diagnosis_terms(request):
    match=re.search(r'\b(?:confirm|confirms|diagnose|diagnosed|rule out)\s+(.+)',request,re.I)
    if not match:
        match=re.search(r'\b(?:she|he|they|the patient|this patient)\s+(?:have|has)\s+(.+)',request,re.I)
    if not match:
        match=re.search(r'\b(?:is|could|might)\s+(?:it|this|that)\s+(?:be\s+)?(.+)',request,re.I)
    if not match:return set()
    phrase=re.split(r'\b(?:based on|according to|from this|in this report)\b',match[1],flags=re.I)[0]
    generic={'a','an','the','any','that','it','its','is','she','he','they','her','his','have','has','with','been','definite','definitely','confirmed','possible','suspected','evidence','of','signs','or','not','tooth','teeth','report','this',
             'key','finding','findings','observation','observations','anything','something','important','abnormal','normal','abnormality','abnormalities','notable','recorded','mentioned','significant','in','results'}
    return set(re.findall(r'[a-z]+',phrase.casefold()))-generic


def compose_answer(request, report, claims, summarize=False):
    source=report['content']
    quoted=[]
    for claim in claims:
        quote=claim['evidence']
        if quote not in source:
            raise HTTPException(422,'Answer contains unsupported source evidence.')
        quote=re.split(r'(?<=[.!?])\s+',quote.strip())[0]
        if not quote or '\n' in quote or len(quote)>450:
            raise HTTPException(422,'Answer evidence must be a short source sentence.')
        if not any(item['quote']==quote for item in quoted):
            quoted.append({'quote':quote,'purpose':claim.get('purpose','finding')})

    summary=summarize or bool(re.search(r'\b(summari[sz]e|summary)\b',request,re.I))
    asks_cause=bool(re.search(r'\b(why|cause|caused|causes|causing|reason)\b',request,re.I))
    targets=diagnosis_terms(request)
    source_terms=set(re.findall(r'[a-z]+',source.casefold()))
    relevant=[q for q in quoted if targets.intersection(re.findall(r'[a-z]+',q['quote'].casefold()))] if targets else quoted
    missing_diagnosis=bool(targets) and (not targets.issubset(source_terms) or not relevant)
    if missing_diagnosis and not summary:
        return {'message':'That information is not stated in the selected report. I cannot infer it.','evidence':[],'cause_not_established':asks_cause}
    if targets and not summary:quoted=relevant
    selected=[]
    parts=[]
    if summary:
        findings=[q for q in quoted if q['purpose']=='finding']
        if findings:
            selected.append(findings[0])
            parts.append(readable_excerpt(findings[0]['quote']))
    elif asks_cause:
        findings=[q for q in quoted if q['purpose']=='finding']
        if findings:
            selected.append(findings[0])
            parts.append(readable_excerpt(findings[0]['quote']))
    elif not asks_cause:
        for item in quoted[:2]:
            selected.append(item)
            parts.append(readable_excerpt(item['quote']))

    if missing_diagnosis:
        parts.append('The report does not establish that diagnosis. I cannot infer it.')

    if asks_cause:
        explicit=[q for q in quoted if q['purpose']=='cause'
                  and re.search(r'\b(caused by|cause is|attributed to)\b',q['quote'],re.I)
                  and not re.search(r'\b(no|not|without|unknown|cannot|uncertain|possible|possibly|suspected|may|might)\b',q['quote'],re.I)]
        if explicit:
            selected.append(explicit[0])
            parts.append('On the cause, the report states: '+readable_excerpt(explicit[0]['quote']))
        else:
            parts.append('The cited report does not establish the underlying cause, so I cannot tell you why it happened.')
        recommendations=[q for q in quoted if q['purpose']=='next_step']
        if not summary and recommendations:
            selected.append(recommendations[0])
            parts.append(readable_excerpt(recommendations[0]['quote']))

    if summary:
        caveats=[q for q in quoted if q['purpose'] in {'limitation','next_step'}]
        if caveats:
            selected.append(caveats[0])
            parts.append(readable_excerpt(caveats[0]['quote']))

    evidence=[]
    for item in selected:
        quote=item['quote']
        if any(e['quote']==quote for e in evidence):continue
        start=source.index(quote)
        evidence.append({'report_id':report['id'],'report_version':report['version'],'quote':quote,'start':start,'end':start+len(quote)})
    return {'message':' '.join(dict.fromkeys(parts)) if parts else 'That information is not stated in the selected report. I cannot infer it.',
            'evidence':evidence,'cause_not_established':asks_cause and not explicit}
