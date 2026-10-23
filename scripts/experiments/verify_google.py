"""Check Google model access without exposing credentials."""
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def read_key():
    for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
        if line.strip().startswith('GOOGLE_API_KEY='):
            value = line.split('=', 1)[1].strip().strip('\"').strip("'")
            if value:
                return value
    raise ValueError('GOOGLE_API_KEY is empty')

def main():
    key = read_key()
    request = urllib.request.Request(
        'https://generativelanguage.googleapis.com/v1beta/models',
        headers={'x-goog-api-key': key},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.load(response)
        output = ROOT / 'verification'
        output.mkdir(exist_ok=True)
        (output / 'google-models.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        models = result.get('models', [])
        print('Model listing succeeded. Models returned:', len(models))
        for model in models:
            print(json.dumps({'name': model['name'], 'methods': model.get('supportedGenerationMethods', [])}))
    except urllib.error.HTTPError as error:
        print('HTTP', error.code)
        print(error.read().decode().replace(key, '[REDACTED]')[:2500])
        raise SystemExit(1)
    except urllib.error.URLError:
        print('Network connection failed before Google could respond.')
        raise SystemExit(2)

if __name__ == '__main__':
    main()
