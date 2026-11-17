# Build Path Audit: release-manifest quickstart

Catch Windows-reserved names, case/Unicode filename collisions, duplicate entries and paths outside the package root before shipping a ZIP or installer. File contents are **not scanned**. This is a path-list check, not malware detection, an archive extractor or a guarantee that a release will install.

## 1. Start with a small manifest

Send `POST https://build-path-audit.p.rapidapi.com/audit` with `Content-Type: application/json`, `X-RapidAPI-Host: build-path-audit.p.rapidapi.com` and your own `X-RapidAPI-Key`.

```json
{"paths":["docs/Readme.md","docs/README.md","CON.txt"]}
```

This example should report a `name-collision` and a `windows-name`. Use `["src/main.js","assets/logo.png"]` for a clean reference manifest. These are reference-engine examples; network and gateway errors are separate from audit findings. Use the playground's generated request to test your own subscription.

## 2. Understand the result

`entries` is the number of input paths. `total` counts all findings. `findings` contains objects with `code`, `path`, `related` and `reason`. `truncated: true` means not all findings fit in the response; never treat it as a clean audit. The reference engine returns at most 2,000 finding objects.

Common codes: `name-collision` (rename names that normalize alike), `windows-name` (reserved name or invalid Windows character), `outside-root` (absolute/parent path), `backslash` (use forward slashes), `file-folder` (file/directory conflict), `duplicate-file` and `empty-or-dot`.

Limits: JSON request at most **256 KiB**, at most **20,000** paths, 1–2,048 characters per path and at most 128 components. Use relative paths with `/`. Keep complete manifests together: splitting a manifest can hide collisions across batches. For larger or confidential manifests, use an offline workflow. Even filenames may disclose client information.

## 3. Use it in CI without leaking credentials

Keep your key in `RAPIDAPI_KEY` using your CI secret store. Do not commit keys or paste them into public issue logs. Save the standalone Python 3 client below as `rapid_check.py`. It uses only the standard library. Save a JSON array of paths as `paths.json`.

```sh
python rapid_check.py paths.json
# Validate locally first: this makes no request.
python rapid_check.py paths.json --send
# Explicitly send ONE request using your own subscription.
```

The client exits **0** for a clean response, **1** for findings/truncation, **2** for an invalid response, request or network problem. It never makes an automatic second request. It rejects absolute paths locally before transmission. Treat exit 1 or 2 as a release check requiring review.

## Cost and troubleshooting

The Basic plan shown on this API on November 18, 2026 includes 10 monthly requests and then **$0.01** per additional request. Confirm the current plan and remaining quota before using `--send`; a CI loop can create charges. A local dry run is not an API call. HTTP 401/403: check the key and subscription; 413: reduce request size without hiding cross-batch collisions; 429: stop and review quota/rate limits. Do not put an unbounded loop around this check.

This quickstart adds onboarding material to API version 1.0.0; it does not claim a new server deployment or new paid usage. Client behavior is checked with deterministic tests; a real paid call is intentionally not needed for a local dry run.

## Standalone client

```python
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

```
