import urllib.request
import urllib.parse
import json
import time

streets = [
    "Cherry St, Dubuque, IA",
    "Mineral St, Dubuque, IA",
    "Exsamba St, Dubuque, IA",
    "Wilbur St, Dubuque, IA",
    "Rose St, Dubuque, IA",
    "Hill St, Dubuque, IA"
]

for s in streets:
    url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(s)}&format=json&limit=1"
    req = urllib.request.Request(url, headers={'User-Agent': 'TRACE-Checker-Streets/1.0'})
    try:
        with urllib.request.urlopen(req) as resp:
            d = json.loads(resp.read().decode('utf-8'))
            if d:
                print(f"{s}: lat={d[0]['lat']}, lon={d[0]['lon']}")
            else:
                print(f"{s}: NOT FOUND")
    except Exception as e:
        print(f"{s}: {e}")
    time.sleep(1.5)
