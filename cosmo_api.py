#!/usr/bin/env python3
"""
cosmo_api.py — client for the CURRENT COSMO: Mission Control backend (myFilip platform).

Reverse-engineered from com.cosmo.missioncontrol v3.4.1 (static jadx). See BACKEND.md.
COSMO is a white-label of myFilip (whiteLabelId=18). Read-only usage here: log in,
list watches, pull recent location. Only dep beyond stdlib is `requests`.

Usage:
    python3 cosmo_api.py login              # just authenticate
    python3 cosmo_api.py devices            # list the watches on the account
    python3 cosmo_api.py location [hours]   # recent location of each watch (default 24h)

Creds from ~/cosmo/.env (COSMO_EMAIL / COSMO_PASSWORD) or argv:
    python3 cosmo_api.py login <email> <password>
"""
import sys, os, json, time

import requests

BASE = "https://api.myfilip.com/"
WHITE_LABEL_ID = 18          # COSMO, from integers.xml <integer name="white_label_id">
APP_BUILD = "3.4.1.732"      # versionName.versionCode, sent as appBuild
HEADERS_VER = {"Accept-Version": "v1.0", "X-Accept-Version": "1.0"}
UA = "okhttp/4.9.0"


class Cosmo:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.access = None
        self.refresh = None
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept": "application/json"})

    def login(self):
        body = {
            "whiteLabelId": WHITE_LABEL_ID,
            "email": self.email,
            "password": self.password,   # plaintext over HTTPS (no client-side hash in v3.x)
            "appBuild": APP_BUILD,
        }
        r = self.s.post(BASE + "v2/token", json=body, headers=HEADERS_VER, timeout=30)
        data = _json(r)
        sess = data.get("data", data) if isinstance(data, dict) else {}
        self.access = _dig(sess, "access_token", "accessToken") or _dig(data, "access_token", "accessToken")
        self.refresh = _dig(sess, "refreshToken", "refresh_token") or _dig(data, "refreshToken")
        return r.status_code, data

    def _auth(self):
        h = dict(HEADERS_VER)
        h["Authorization"] = "Bearer " + (self.access or "")
        return h

    def devices(self):
        r = self.s.get(BASE + "v3/device/account/devices/full", headers=self._auth(), timeout=30)
        return r.status_code, _json(r)

    def raw_get(self, path):
        r = self.s.get(BASE + path.lstrip("/"), headers=self._auth(), timeout=30)
        return r.status_code, _json(r)

    def map(self):
        """GET v2/map -> all watches with current location, battery, gpsDate, SafeZones."""
        r = self.s.get(BASE + "v2/map", headers=self._auth(), timeout=30)
        return r.status_code, _json(r)

    def location_history(self, device_id, hours=24):
        now = int(time.time() * 1000)
        body = {"from": now - hours * 3600 * 1000, "to": now}
        r = self.s.post(BASE + f"v2/map/history/{device_id}", json=body, headers=self._auth(), timeout=30)
        return r.status_code, _json(r)


def _json(r):
    try:
        return r.json()
    except Exception:
        return {"_status": r.status_code, "_text": r.text[:1000]}


def _dig(d, *keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        if d.get(k) not in (None, ""):
            return d[k]
    return None


def _load_env():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


def _creds(argv):
    _load_env()
    # positional creds may start at argv[2] (login) or argv[2/3] generally
    pos = [a for a in argv[2:] if "@" in a or (argv[1] == "login")]
    email = os.environ.get("COSMO_EMAIL")
    pw = os.environ.get("COSMO_PASSWORD")
    if len(argv) > 3 and argv[1] == "login":
        email, pw = argv[2], argv[3]
    if not email or not pw:
        sys.exit("need COSMO_EMAIL / COSMO_PASSWORD in ~/cosmo/.env (or: login <email> <password>)")
    return email, pw


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    email, pw = _creds(sys.argv)
    c = Cosmo(email, pw)
    code, data = c.login()
    print(f"# login http={code} access_token={'yes' if c.access else 'NO'}")
    if not c.access:
        print(json.dumps(data, indent=2)[:1500]); return
    if cmd == "login":
        print("LOGIN OK."); return
    if cmd == "probe":
        for p in ["v2/map", "v3/device/account/devices", "v2/user/profile", "v2/user/permissions"]:
            sc, body = c.raw_get(p)
            txt = json.dumps(body)[:900]
            print(f"\n## GET {p}  http={sc}\n{txt}")
        return
    if cmd == "get" and len(sys.argv) > 2:
        sc, body = c.raw_get(sys.argv[2])
        print(f"# GET {sys.argv[2]} http={sc}")
        print(json.dumps(body, indent=2)[:4000]); return
    if cmd in ("devices", "map", "location"):
        sc, mp = c.map()
        devs = (mp.get("data", {}) or {}).get("Devices", []) if isinstance(mp, dict) else []
        print(f"# v2/map http={sc}  {len(devs)} watch(es)")
        for d in devs:
            name = (d.get("firstName") or "") + " " + (d.get("lastName") or "")
            print(f"  - {name.strip() or d.get('id')}: "
                  f"lat={d.get('latitude')} lon={d.get('longitude')} "
                  f"acc={d.get('radius')}m batt={d.get('batteryLevel')}% "
                  f"fix={d.get('gpsDate')} fw={d.get('firmwareVersion')}")
        if cmd != "location":
            print("\n" + json.dumps(mp, indent=2)[:3500])
    else:
        sys.exit("commands: login | map | location | devices | probe | get <path>")


if __name__ == "__main__":
    main()
