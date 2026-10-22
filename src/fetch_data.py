"""Re-create data/raw sample: 1,600 random pages x 50 rows (seed 42) from NY SPARCS 2016 (Socrata gnzp-ekau).
Run:  python -m src.fetch_data"""
import random, io, gzip, urllib.request, urllib.parse, concurrent.futures as cf
import csv
from pathlib import Path
BASE = "https://health.data.ny.gov/resource/gnzp-ekau.csv"
TOTAL = 2343429
CHUNK, N = 50, 1600
random.seed(42)
offsets = sorted(random.sample(range(0, TOTAL - CHUNK, CHUNK), N))
def get(off):
    q = urllib.parse.urlencode({"$limit": CHUNK, "$offset": off, "$order": ":id"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f"{BASE}?{q}", timeout=120) as r:
                return r.read().decode()
        except Exception as e:
            err = e
    raise err
header, rows = None, []
with cf.ThreadPoolExecutor(16) as ex:
    for txt in ex.map(get, offsets):
        rd = list(csv.reader(io.StringIO(txt)))
        header = header or rd[0]
        assert rd[0] == header
        rows.extend(rd[1:])
with gzip.open(str(Path(__file__).resolve().parent.parent / "data" / "raw" / "sparcs_2016_inpatient_sample.csv.gz"), "wt", newline="") as f:
    w = csv.writer(f); w.writerow(header); w.writerows(rows)
print(len(rows), header)
