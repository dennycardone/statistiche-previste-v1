#!/bin/bash
# 27/10/2026: giro lungo del micro-processo delle formazioni. GitHub fa partire i giri programmati con 30-40 minuti di ritardo e a volte
# per ore non ne fa partire nessuno: un solo giro resta attivo fino a ~5 ore e 45 minuti e controlla ogni 5 minuti (0 richieste API se
# non c'è niente da fare). Un avviso riassuntivo alla fine (gli avvisi di GitHub sono limitati).
set -u
END=$(( $(date +%s) + ${LOOP_SECONDS:-20700} )); n=0; npub=0; nkick=0; : > /tmp/fl_log.txt
REPO="https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git"
publish() {
  for t in 1 2 3 4; do
    rm -rf _p && git init -q _p && ( cd _p
      git fetch -q --depth 1 "$REPO" pages && git checkout -q -b pages FETCH_HEAD || exit 1
      v=$(sha1sum ../out/formazioni.json | cut -c1-12)
      for d in data docs/data; do
        [ -d $d ] || continue
        cp ../out/formazioni.json $d/formazioni.json
        python3 -c "import json,sys; p=sys.argv[1]; s=json.load(open(p)); s['v']['formazioni']=sys.argv[2]; json.dump(s,open(p,'w'),separators=(',',':'))" $d/stato.json $v
      done
      git config user.name "corner-bot" && git config user.email "corner-bot@users.noreply.github.com"
      git add -A && { git commit -q -m "Formazioni ufficiali $(date -u '+%F %H:%M')" || exit 0; }
      git push -q "$REPO" pages ) && return 0
    sleep 15
  done
  echo "::warning title=Formazioni (micro)::pubblicazione sul sito non riuscita"; return 1
}
while :; do
  n=$((n+1)); mkdir -p pub xi_live valori; rm -f pub/*.json out/formazioni.json
  git fetch -q --depth 1 origin pages 2>/dev/null && { git show FETCH_HEAD:data/prossime.json > pub/prossime.json 2>/dev/null; git show FETCH_HEAD:data/formazioni.json > pub/formazioni.json 2>/dev/null; }
  if git ls-remote --exit-code origin xi >/dev/null 2>&1; then git fetch -q --depth 1 origin xi && git show FETCH_HEAD:xi.json > xi_live/xi.json; fi
  : > /tmp/fl_chk; GITHUB_OUTPUT=/tmp/fl_chk python3 tools/formazioni_live.py check >/dev/null
  if grep -q 'need=1' /tmp/fl_chk; then
    if [ ! -s valori/valori.json ] || [ $(( $(date +%s) - $(stat -c %Y valori/valori.json) )) -gt 3600 ]; then
      git fetch -q --depth 1 origin valori && git show FETCH_HEAD:valori.json > valori/valori.json || echo "ramo valori non letto"
    fi
    FL_LOOP=1 python3 tools/formazioni_live.py run | sed 's/^::notice title=[^:]*:://' | tee -a /tmp/fl_log.txt
    ( rm -rf _x && mkdir _x && cp xi_live/xi.json _x/ && cd _x && git init -q -b xi && git config user.name "corner-bot" && git config user.email "corner-bot@users.noreply.github.com" \
      && git add -A && git commit -q -m "Formazioni $(date -u '+%F %H:%M')" && for t in 1 2 3; do git push -q -f "$REPO" xi && break; sleep 10; done )
    if [ -s out/formazioni.json ]; then publish && npub=$((npub+1)); fi
  fi
  # 27/10/2026: anche l'aggiornamento principale (quote, risultati) dipende dai giri programmati di GitHub, che saltano: se l'ultimo è
  # partito più di 30 minuti fa e non ce n'è uno in coda o in corso, lo fa partire (workflow_dispatch; nessuna richiesta API qui).
  last=$(curl -s -H "Authorization: Bearer ${GH_TOKEN}" "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/workflows/update.yml/runs?per_page=5" \
    | python3 -c "import json,sys,datetime
try:
    R=json.load(sys.stdin)['workflow_runs']
    if any(r['status'] in ('queued','in_progress','waiting','pending','requested') for r in R): print('busy')
    else:
        t=max(datetime.datetime.fromisoformat(r['created_at'].replace('Z','+00:00')) for r in R)
        print(int((datetime.datetime.now(datetime.timezone.utc)-t).total_seconds()//60))
except Exception: print('err')")
  if [ "$last" != "busy" ] && [ "$last" != "err" ] && [ "$last" -ge 30 ]; then
    curl -s -o /dev/null -w "%{http_code}" -X POST -H "Authorization: Bearer ${GH_TOKEN}" -H "Accept: application/vnd.github+json" \
      "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/workflows/update.yml/dispatches" -d '{"ref":"main"}' | grep -q 204 && { nkick=$((nkick+1)); echo "aggiornamento principale fatto partire (ultimo $last minuti fa)" >> /tmp/fl_log.txt; }
  fi
  # 31/10/2026: probabilità corretta della vista Operatività (corretta.yml): GitHub fa partire il giro delle 4:47 UTC anche 6 ore dopo;
  # dalle 5:00 UTC, se oggi non è ancora partito, lo fa partire (nessuna richiesta API, solo l'archivio quote già scaricato)
  if [ "$(date -u +%H)" -ge 5 ]; then
    cr=$(curl -s -H "Authorization: Bearer ${GH_TOKEN}" "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/workflows/corretta.yml/runs?per_page=3" \
      | python3 -c "import json,sys,datetime
try:
    R=json.load(sys.stdin)['workflow_runs']; oggi=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT04')
    print('ok' if any(r['created_at']>=oggi for r in R) else 'manca')
except Exception: print('err')")
    if [ "$cr" = "manca" ]; then curl -s -o /dev/null -X POST -H "Authorization: Bearer ${GH_TOKEN}" -H "Accept: application/vnd.github+json" \
      "https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/workflows/corretta.yml/dispatches" -d '{"ref":"main"}' && echo "probabilità corretta fatta partire" >> /tmp/fl_log.txt; fi
  fi
  [ $(( $(date +%s) + 300 )) -ge $END ] && break
  sleep 300
done
echo "::notice title=Formazioni (micro, giro lungo)::controlli $n · formazioni prese $(grep -o ': presa' /tmp/fl_log.txt | wc -l) · pubblicazioni sul sito $npub · aggiornamenti principali fatti partire $nkick · ultime: $(grep -o '[^·]*: presa' /tmp/fl_log.txt | tail -12 | tr '\n' ';')"
grep -q 'non ancora uscita' /tmp/fl_log.txt && echo "::notice title=Formazioni (micro) · tentativi a vuoto::$(grep -o '[^·]*non ancora uscita' /tmp/fl_log.txt | sort | uniq -c | sort -rn | head -10 | tr '\n' ';')"
exit 0
