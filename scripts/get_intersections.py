import urllib.request
import urllib.parse
import json

def get_intersection(street1, street2, city="Dubuque", state="Iowa"):
    # Overpass query to find intersection of two streets
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    area["name"="Dubuque"]["admin_level"="8"]->.a;
    way["name"~"{street1}",i](area.a)->.w1;
    way["name"~"{street2}",i](area.a)->.w2;
    node(w.w1)(w.w2);
    out body;
    """
    req = urllib.request.Request(overpass_url, data=urllib.parse.urlencode({'data': query}).encode('utf-8'), headers={'User-Agent': 'TRACE-Intersections/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            elements = data.get('elements', [])
            if elements:
                return elements[0]['lat'], elements[0]['lon']
    except Exception as e:
        print(f"Overpass error for {street1} & {street2}: {e}")
    return None

intersections = [
    ("c035", "University Ave & Cherry St / Mineral St", "University Avenue", "Cherry Street"),
    ("c035_alt", "University Ave & Mineral St", "University Avenue", "Mineral Street"),
    ("c029", "University Ave & Grandview Ave", "University Avenue", "Grandview Avenue"),
    ("c029_custer", "Custer St & Grandview Ave", "Custer Street", "Grandview Avenue"),
    ("c023", "Loras Blvd & Cox St", "Loras Boulevard", "Cox Street"),
    ("c023_park", "University Ave & Cox St", "University Avenue", "Cox Street"),
    ("c020", "Loras Blvd & Wilbur St", "Loras Boulevard", "Wilbur Street"),
    ("c020_rose", "Rose Street & Wilbur Street", "Rose Street", "Wilbur Street"),
]

for cam, desc, s1, s2 in intersections:
    res = get_intersection(s1, s2)
    print(f"{cam} ({desc}): {res}")
