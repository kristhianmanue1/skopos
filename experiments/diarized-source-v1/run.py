"""Inspección local: informe privado sin copiar texto de la reunión."""
import argparse
import json
import os
from pathlib import Path
from source import DiarizedSource, inspect


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--term',action='append',default=[])
    args=parser.parse_args()
    report=inspect(args.source)
    source=DiarizedSource(args.source,report['source_sha256'])
    queries=[]
    for term in args.term:
        hits=source.search(term);checks=[]
        for hit in hits[:3]:
            result=source.fetch(hit['id'])
            checks.append({k:result['segment'][k] for k in ('id','line','start_ms','end_ms','start_byte','end_byte')})
        queries.append({'term':term,'matching_segments':len(hits),'checked_locators':checks})
    report['queries']=queries
    report['source_unchanged']=inspect(args.source)['source_sha256']==report['source_sha256']
    if not report['source_unchanged']:raise ValueError('source_changed_during_inspection')
    os.umask(0o077)
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='queries'},ensure_ascii=False))
    print(json.dumps({'queries':[{'term':q['term'],'matching_segments':q['matching_segments'],'verified_fetches':len(q['checked_locators'])} for q in queries]},ensure_ascii=False))

if __name__=='__main__':main()
