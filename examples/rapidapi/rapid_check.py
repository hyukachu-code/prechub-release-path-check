"""One-request CI client. Default is local validation without an API request."""
import argparse,json,os,re,sys,urllib.request,urllib.error,operator
ENDPOINT='https://build-path-audit.p.rapidapi.com/audit'
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return None
def payload(paths):
 if not isinstance(paths,list) or operator.gt(len(paths),20000):raise ValueError('Use a JSON array of at most 20,000 paths.')
 for p in paths:
  if not isinstance(p,str) or not (operator.le(1,len(p)) and operator.le(len(p),2048)):raise ValueError('Each path must have 1–2,048 characters.')
  if p.startswith(('/','\\')) or re.match(r'^[A-Za-z]:',p):raise ValueError('Use relative manifest paths; remove absolute/drive paths locally.')
 raw=json.dumps({'paths':paths},ensure_ascii=False,separators=(',',':')).encode('utf8')
 if operator.gt(len(raw),256*1024):raise ValueError('JSON request exceeds 256 KiB; review the manifest locally.')
 return raw
def classify(result):
 if not isinstance(result,dict):return 2
 if any(type(result.get(k)) is not int or operator.lt(result[k],0) for k in ['entries','total']):return 2
 if not isinstance(result.get('findings'),list) or type(result.get('truncated')) is not bool:return 2
 if operator.lt(result['total'],len(result['findings'])):return 2
 if result['total']==0 and (result['findings'] or result['truncated']):return 2
 return 1 if result['total'] or result['truncated'] else 0
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('manifest',help='UTF-8 JSON array of relative paths');parser.add_argument('--send',action='store_true',help='Send one request using your RapidAPI plan; charges may apply');args=parser.parse_args()
 try:
  with open(args.manifest,encoding='utf-8-sig') as f:raw=payload(json.load(f))
  if not args.send:print(f'Validated {len(raw)} request bytes locally. No request sent. Use --send only after checking your plan and quota.');return 0
  key=os.environ.get('RAPIDAPI_KEY','')
  if not key:raise ValueError('Set RAPIDAPI_KEY in your environment or CI secret store.')
  req=urllib.request.Request(ENDPOINT,data=raw,headers={'Content-Type':'application/json','X-RapidAPI-Host':'build-path-audit.p.rapidapi.com','X-RapidAPI-Key':key},method='POST')
  with urllib.request.build_opener(NoRedirect()).open(req,timeout=30) as response:result=json.load(response)
  code=classify(result)
  if code==2:print('Unexpected response: fail closed and inspect the provider response locally.',file=sys.stderr);return 2
  print(json.dumps(result,ensure_ascii=False,indent=2));return code
 except urllib.error.HTTPError as e:print(f'HTTP {e.code}. Check subscription, quota and request; no automatic second request.',file=sys.stderr);return 2
 except (ValueError,OSError,urllib.error.URLError):print('Request or local manifest could not be validated. Check the manifest, credentials and network.',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
