from ddgs import DDGS
import json

results = DDGS().text("Valorant newest agent wiki", max_results=5)
print(json.dumps(results, indent=2))
