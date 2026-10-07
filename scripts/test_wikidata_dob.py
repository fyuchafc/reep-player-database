import json
import urllib.parse
import urllib.request

QIDS = [
    "Q1825157",
    "Q51328289",
    "Q468683",
    "Q16233296",
    "Q2081701",
]

print("=" * 70)
print("WIKIDATA DOB TEST")
print("=" * 70)
print()
print("Testing 5 REEP-linked Wikidata QIDs.")
print("No REEP database will be modified.")
print()

params = {
    "action": "wbgetentities",
    "ids": "|".join(QIDS),
    "props": "claims|labels",
    "languages": "en",
    "format": "json",
    "formatversion": "2",
}

url = "https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(params)

request = urllib.request.Request(
    url,
    headers={
        "User-Agent": "Fyucha REEP Player Database/1.1 (DOB research)"
    }
)

with urllib.request.urlopen(request, timeout=30) as response:
    data = json.load(response)

for qid in QIDS:
    print("-" * 70)

    entity = data.get("entities", {}).get(qid)

    if not entity:
        print(qid, "NOT FOUND")
        continue

    label = entity.get("labels", {}).get("en", {}).get("value", "")
    claims = entity.get("claims", {})
    dob_claims = claims.get("P569", [])

    print("QID:", qid)
    print("Wikidata label:", label)
    print("P569 claims:", len(dob_claims))

    if not dob_claims:
        print("DOB: NO P569 VALUE")
        continue

    for index, claim in enumerate(dob_claims, 1):
        rank = claim.get("rank")
        mainsnak = claim.get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {})
        value = datavalue.get("value", {})

        print("  DOB claim", index)
        print("    Rank:", rank)
        print("    Time:", value.get("time"))
        print("    Precision:", value.get("precision"))
        print("    Calendar:", value.get("calendarmodel"))

print()
print("=" * 70)
print("WIKIDATA DOB TEST COMPLETE")
print("=" * 70)