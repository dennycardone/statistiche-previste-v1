"""Basket · costruisce basket.html (15/11/2026) prendendo da index.html stile, icone e intestazione (così le due pagine restano uguali nella
grafica) e aggiungendo le sezioni del basket (tools/basket/basket_app.js). Da rilanciare quando cambia lo stile dell'app.
Uso: python tools/basket/build_html.py  → basket.html"""
import re, os
R = os.path.join(os.path.dirname(__file__), "..", "..")
H = open(os.path.join(R, "index.html"), encoding="utf8").read()
APP = open(os.path.join(os.path.dirname(__file__), "basket_app.js"), encoding="utf8").read()
head = H[:H.index("</head>")]
head = re.sub(r"<title>.*?</title>", "<title>Prevista Basket — previsioni basket</title>", head, count=1, flags=re.S)
head = re.sub(r'<meta name="description" content="[^"]*">', '<meta name="description" content="Prevista Basket: previsioni di NBA, Eurolega, Eurocup, Serie A, ACB, BBL e LNB con il grado di fiducia verificato sulle partite passate.">', head, count=1)
icons = H[H.index('<svg width="0" height="0"'):H.index("</defs></svg>") + len("</defs></svg>")]
brand = re.search(r'<h1 class="brand">.*?</h1>', H, re.S).group(0)
CSS = """<style>
/* Basket (15/11/2026) */
.sportpick{flex:0 0 auto;margin-left:auto}.sportpick select{width:auto;padding:6px 28px 6px 10px;font-size:14px;font-weight:600;background:rgba(255,255,255,.12) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 12 8'%3E%3Cpath d='M1 1.5l5 5 5-5' fill='none' stroke='%23ffffff' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat right 9px center/11px;color:#fff;border:1px solid rgba(255,255,255,.25);border-radius:10px;-webkit-appearance:none;appearance:none}
.sportpick select option{color:var(--ink);background:var(--surface)}
.prevpt{color:var(--ink-3);font-weight:600;font-size:12px}
.bkhead{display:grid;grid-template-columns:1fr auto 1fr;gap:8px;align-items:center;padding:14px 10px;text-align:center}
.bkt{display:flex;flex-direction:column;align-items:center;gap:4px;min-width:0}.bkt b{font-size:14px;line-height:1.2}.bkt small{color:var(--ink-2);font-size:12px}
.bkt .tlogo.big{width:54px;height:54px;object-fit:contain}
.bkc{display:flex;flex-direction:column;gap:3px;align-items:center}.bkc small{color:var(--ink-2);font-size:12px}.bksc{font-size:30px;font-variant-numeric:tabular-nums;color:var(--accent)}
.bkl{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}.bkl th{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--accent);text-align:center;padding:9px 4px 2px}
.bkl td,.bkl th{padding:6px 8px;text-align:center;border-top:1px solid var(--line)}.bkl td small{color:var(--ink-2);display:block;font-size:12px}.bkl td b{font-size:18px}
.bkl tr.sub td{border-top:0;padding-top:0;color:var(--ink-2);font-size:12.5px}
.bkq{margin-top:12px}.bkq h3,.card h3{font-size:14px;margin:0 0 8px;display:flex;align-items:center;gap:6px}.bkq h3 small,.card h3 small{color:var(--ink-3);font-weight:500}
.bkt2{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:13px}.bkt2 th,.bkt2 td{padding:6px 4px;border-top:1px solid var(--line);text-align:left}
.bkt2 thead th{border-top:0;color:var(--ink-3);font-size:11.5px;font-weight:600}.bkt2 td.num,.bkt2 th.num{text-align:right}.bkt2 td small{display:block;color:var(--ink-3);font-size:11px}
.bkt2 .tlogo{width:18px;height:18px;margin-right:6px;vertical-align:-4px}.cls tr.hl td{background:color-mix(in srgb,var(--accent) 12%,transparent)}
.vgood{color:var(--gold);font-weight:700}.okc{color:#47d18c}.koc{color:#ff6b6b}
.gbadge{display:inline-flex;align-items:center;justify-content:center;min-width:30px;padding:2px 7px;border-radius:8px;font-weight:800;font-size:13px}
.gbadge.ap{background:#d4ff3f;color:#111}.gbadge.a{background:#5fe0a0;color:#062014}.gbadge.b{background:#3b6fb6;color:#fff}.gbadge.c{background:var(--surface-2);color:var(--ink);border:1px solid var(--line)}
.grow{display:grid;grid-template-columns:1fr auto auto;gap:12px;align-items:center;padding:10px 0;border-top:1px solid var(--line)}.grow small{display:block;color:var(--ink-3);font-size:12px}.grow .num{text-align:right}.grow .num b{font-size:20px}
.glegend{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:12px;font-size:12.5px;color:var(--ink-2)}
.selrow,.sigrow{display:grid;grid-template-columns:1fr auto;gap:4px 10px;width:100%;text-align:left;padding:10px 2px;border:0;border-top:1px solid var(--line);background:none;color:inherit;font:inherit;cursor:pointer}
.selt b{display:block;font-size:14px}.selt small{color:var(--ink-3);font-size:12px}.selp{grid-column:1;display:flex;gap:8px;align-items:center;font-size:13.5px}.selp small{color:var(--ink-2)}
.selv{grid-column:2;grid-row:1/3;text-align:right;align-self:center}.selv b{font-size:18px;display:block}.selv small{color:var(--ink-3);font-size:11.5px}
.sigrow{grid-template-columns:auto 1fr}.sigp{display:flex;flex-direction:column;align-items:center;gap:4px;min-width:54px}.sigp b{font-size:20px}
.sigt b{display:block;font-size:14px}.sigt span{display:block;font-size:13.5px}.sigt small{color:var(--ink-3);font-size:12px}
.opnote{background:var(--surface-2);border:1px solid var(--line);border-radius:12px;padding:10px 12px;font-size:13px;margin-bottom:8px}
.tgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}.tgrid div{background:var(--surface-2);border-radius:10px;padding:10px}.tgrid b{font-size:20px;display:block}.tgrid small{color:var(--ink-2);font-size:12px}
.formrow{display:flex;gap:4px;flex-wrap:wrap;margin:6px 0 8px}.fpill{display:inline-flex;width:22px;height:22px;border-radius:6px;align-items:center;justify-content:center;font-size:11px;font-weight:800}
.fpill.w{background:#2e8b57;color:#fff}.fpill.l{background:#7a2e3a;color:#fff}
.bkstamp{color:var(--ink-3);font-size:11.5px;text-align:center;margin:14px 0}
</style>"""
SPORT = """<label class="sportpick"><span class="sr">Sport</span><select id="sport" autocomplete="off" onchange="if(this.value!=='basket'){try{localStorage.setItem('prevista.sport',this.value)}catch(e){}location.assign(new window.URL('./?s='+Date.now(),location.href).href)}"><option value="calcio">⚽ Calcio</option><option value="basket" selected>🏀 Basket</option></select></label><script data-sport>addEventListener("pageshow",function(){var s=document.getElementById("sport");if(s)s.value="basket"});</script>"""
BODY = f"""<body>
{icons}
<header class="appbar">
  <div class="appbar-in">
    {brand}
    {SPORT}
    <p class="bslog">Guarda la partita <b>prima</b> che si giochi</p>
  </div>
  <nav class="tabbar" aria-label="Sezioni">
  <button type="button" id="navSel" aria-pressed="false"><svg class="ic" aria-hidden="true"><use href="#i-radar"/></svg>Radar</button>
  <button type="button" id="navSig" aria-pressed="false"><svg class="ic" aria-hidden="true"><use href="#i-segnali"/></svg>Segnali</button>
  <button type="button" id="navStats" class="navmain" aria-pressed="true"><span class="nmc"><svg class="ic" aria-hidden="true"><use href="#i-partite"/></svg></span>Partite</button>
  <button type="button" id="navGen" aria-pressed="false"><svg class="ic" aria-hidden="true"><use href="#i-tendenze"/></svg>Tendenze</button>
  <button type="button" id="navRit" aria-pressed="false"><svg class="ic" aria-hidden="true"><use href="#i-ritardi"/></svg>Digiuni</button>
  </nav>
</header>
<div class="wrap">
  <div class="boot" id="boot" role="status"><p class="muted">Carico il basket…</p></div>
  <div class="view" id="viewPart">
    <div class="daystrip" id="days" role="tablist" aria-label="Giorni"></div>
    <div id="sched" class="sched"></div>
  </div>
  <div class="view" id="viewMatch" hidden>
    <div class="mtop"><button type="button" id="back" class="backbtn" aria-label="Torna alle partite">‹ Partite</button><span class="tag" id="seasonTag"></span></div>
    <div class="mtabs" role="tablist" aria-label="Sezioni della partita">
      <button type="button" class="mtab" data-mt="prev" aria-pressed="true">Lettura</button>
      <button type="button" class="mtab" data-mt="sig" aria-pressed="false">Grado</button>
      <button type="button" class="mtab" data-mt="h2h" aria-pressed="false">Precedenti</button>
      <button type="button" class="mtab" data-mt="tab" aria-pressed="false">Classifica</button>
      <button type="button" class="mtab" data-mt="rend" aria-pressed="false">Rendimento</button>
    </div>
    <div class="mpane" data-mp="prev"><section class="card mhead" id="mhead" aria-label="Lettura della partita"></section></div>
    <div class="mpane" data-mp="sig" hidden><section class="card" id="mgrado"></section></div>
    <div class="mpane" data-mp="h2h" hidden><section class="card" id="mh2h"></section></div>
    <div class="mpane" data-mp="tab" hidden><section class="card" id="mtab"></section></div>
    <div class="mpane" data-mp="rend" hidden><div id="mrend"></div></div>
  </div>
  <div class="view" id="viewSel" hidden>
    <div class="daystrip" id="rdays" role="tablist" aria-label="Giorni"></div>
    <div class="seg rtabs" id="selTabs" role="tablist" aria-label="Sezioni del Radar">
      <button type="button" class="segb" data-rt="gr" aria-pressed="true"><svg class="ic ic-tutte" aria-hidden="true"><use href="#i-tutte"/></svg>Grado <b id="rtA"></b></button>
      <button type="button" class="segb" data-rt="mk" aria-pressed="false"><svg class="ic ic-mercato gold" aria-hidden="true"><use href="#i-mercato"/></svg>Mercato <b id="rtB"></b></button>
      <button type="button" class="segb" data-rt="op" aria-pressed="false"><svg class="ic ic-op" aria-hidden="true"><use href="#i-op"/></svg>Operatività <b id="rtO"></b></button>
    </div>
    <section class="card" id="selOut"></section>
  </div>
  <div class="view" id="viewSig" hidden>
    <section class="card" aria-label="Filtri segnali"><div class="selhead"><h2>Segnali</h2></div>
      <div class="row"><label for="sigLeague">Campionato<select id="sigLeague"></select></label></div>
      <div class="self" id="sigWhen" role="group" aria-label="Quando"><button type="button" class="chip" data-sw="0" aria-pressed="true">Oggi</button><button type="button" class="chip" data-sw="1" aria-pressed="true">Domani</button><button type="button" class="chip" data-sw="r" aria-pressed="false">Giornata</button></div>
      <p class="small muted" style="margin:0">Previsioni dalla parte della lettura che, nelle stagioni passate, sono uscite almeno 72 volte su 100 (grado A o A+). Totale e handicap sulla linea del book quando c'è.</p></section>
    <section class="card" id="sigOut"></section>
  </div>
  <div class="view" id="viewGen" hidden><section class="card" id="genOut"></section></div>
  <div class="view" id="viewRit" hidden><section class="card" id="ritOut"></section></div>
  <p class="bkstamp" id="stamp"></p>
</div>
<script>
{APP}
</script>
</body>
</html>
"""
open(os.path.join(R, "basket.html"), "w", encoding="utf8").write(head + CSS + "\n</head>\n" + BODY)
print("basket.html", os.path.getsize(os.path.join(R, "basket.html")) // 1024, "KB")
