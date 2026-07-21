import requests
import json
import pprint

url = "http://127.0.0.1:5000/compare"
headers = {'Content-Type': 'application/json'}
payload = {
    "text_a": "દુનિયાની દરેક છોકરીની પંચાત છે યાર એક કામ કર પેલા બધા જ કપડાં બહાર કાઢીને બેટ પર નાખી દે પછી એના ત્રણ ભાગ કર એક જે તું રોજ",
    "text_b": "બહાર જવાનું હોય ત્યારે મને એક પણ કપડું ગમતું નથી આ જ તો દુનિયાની દરેક છોકરીની પંચાયત છે યાર એક કામ કર પહેલા બધા જ કપડાં બહાર",
    "text_c": "જ્યારે કંઈક બહાર જવાનું હોય ત્યારે મને એક પણ કપડું ગમતું નથી દુનિયાની દરેક છોકરીની પંચાયત છે યાર એક કામ કર પેલા બધા જ કપડાં",
    "mode": "word",
    "flag_script_mismatch": True
}

try:
    response = requests.post(url, json=payload)
    data = response.json()

    print("=== PANEL A ===")
    pprint.pprint([(d['text'], d['operation']) for d in data['comparison']['panels']['panel_a'] if d['text'] in ['પંચાત', 'છે', 'પેલા']])

    print("=== PANEL B ===")
    pprint.pprint([(d['text'], d['operation']) for d in data['comparison']['panels']['panel_b'] if d['text'] in ['પંચાયત', 'છે', 'પહેલા']])

    print("=== PANEL C ===")
    pprint.pprint([(d['text'], d['operation']) for d in data['comparison']['panels']['panel_c'] if d['text'] in ['પંચાયત', 'છે', 'પેલા']])
except Exception as e:
    print("Error:", e)
