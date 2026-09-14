import urllib.request
import urllib.parse
import json
import time

queries = [
    'Loras College, Dubuque, Iowa',
    'Finley Hospital, Dubuque, Iowa',
    'Flora Park, Dubuque, Iowa',
    'Mercy Medical Center, Dubuque, Iowa',
    'Clarke University, Dubuque, Iowa'
]

headers = {'User-Agent': 'TRACE-Location-Checker/1.0'}
for q in queries:
    url = f'https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(q)}&format=json&limit=1'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data:
                print(f'{q} -> lat: {data[0]["lat"]}, lon: {data[0]["lon"]}')
            else:
                print(f'{q} -> NOT FOUND')
    except Exception as e:
        print(f'{q} -> error: {e}')
    time.sleep(1.0)
