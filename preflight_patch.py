from pathlib import Path
p=Path('pro_repair_v3.py')
s=p.read_text(encoding='utf-8')
s=s.replace('["UUID.randomUUID","bridge?.connect","sessionId"]','["UUID.randomUUID","bridge?.connect","sid"]')
p.write_text(s,encoding='utf-8')
print('PRE-FLIGHT PATCH: PASS')
