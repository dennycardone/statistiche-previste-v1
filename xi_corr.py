"""Correzione dei falli attesi con la formazione ufficiale (fase 1-B, 25/10/2026). Un solo calcolo per update_data.py e per il
micro-processo delle formazioni (tools/formazioni_live.py), così i numeri sono identici.
Per ogni squadra: falli attesi × e^(0,368·falli fatti dei suoi titolari + 0,377·falli subiti dei titolari avversari − 0,030·cartellini
dei suoi titolari), ognuno come log(somma dei valori dei titolari di oggi / somma abituale della squadra). Valori: ramo valori."""
import math

W_XI = (0.368, 0.377, -0.030)

def corr(x, V):
    """x = {"hid", "aid", "h": [[id, nome, numero, ruolo], ...], "a": [...]}; V = valori.json. Restituisce (fh, fa) oppure (None, motivo)."""
    GP, GS, GR = V["giocatori"], V["squadre"], V["ruoli"]
    th, ta = GS.get(str(x["hid"])), GS.get(str(x["aid"]))
    if not th or not ta: return None, "squadra senza valori dei giocatori"
    rate = lambda p: (GP.get(str(p[0])) or GR.get((p[3] or "M")[:1], GR["M"]))[:3]
    sh = [sum(rate(p)[i] for p in x["h"]) for i in range(3)]; sa = [sum(rate(p)[i] for p in x["a"]) for i in range(3)]
    lg_ = lambda s_, t_, i: math.log(max(s_[i], 1e-6) / t_[i]) if t_[i] > 0 else 0.0
    fh = math.exp(max(-3, min(3, W_XI[0] * lg_(sh, th, 0) + W_XI[1] * lg_(sa, ta, 1) + W_XI[2] * lg_(sh, th, 2))))
    fa = math.exp(max(-3, min(3, W_XI[0] * lg_(sa, ta, 0) + W_XI[1] * lg_(sh, th, 1) + W_XI[2] * lg_(sa, ta, 2))))
    return (round(fh, 4), round(fa, 4)), None

def parse_lineups(resp, home_api, away_api):
    """risposta di fixtures/lineups → (hid, aid, xi_h, xi_a) oppure (None, motivo)"""
    T = {}
    for t in resp or []:
        xi_ = [[p["player"]["id"], p["player"].get("name") or "", p["player"].get("number"), p["player"].get("pos") or ""] for p in t.get("startXI") or [] if p.get("player")]
        T[t["team"]["name"]] = (t["team"]["id"], xi_)
    if len(T) != 2: return None, ("non ancora uscita" if not T else f"{len(T)} squadre nella risposta")
    nm = list(T); hk = home_api if home_api in T else nm[0]; ak = away_api if away_api in T else [x for x in nm if x != hk][0]
    if len(T[hk][1]) < 10 or len(T[ak][1]) < 10: return None, f"titolari {len(T[hk][1])}/{len(T[ak][1])}"
    return (T[hk][0], T[ak][0], T[hk][1], T[ak][1]), None

def entry(x):
    """voce pubblicata in formazioni.json (senza id dei giocatori)"""
    return {"h": [[p[1], p[2], p[3]] for p in x["h"]], "a": [[p[1], p[2], p[3]] for p in x["a"]]}
