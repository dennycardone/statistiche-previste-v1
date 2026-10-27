#!/bin/bash
# 27/10/2026: giro lungo del micro-processo delle formazioni. GitHub fa partire i giri programmati con 30-40 minuti di ritardo e a volte
# per ore non ne fa partire nessuno: un solo giro resta attivo fino a ~5 ore e 45 minuti e controlla ogni 5 minuti (0 richieste API se
# non c'è niente da fare). Un avviso riassuntivo alla fine (gli avvisi di GitHub sono limitati).
set -u
END=$(( $(date +%s) + ${LOOP_SECONDS:-20700} )); n=0; npub=0; : > /tmp/fl_log.txt
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
  [ $(( $(date +%s) + 300 )) -ge $END ] && break
  sleep 300
done
echo "::notice title=Formazioni (micro, giro lungo)::controlli $n · formazioni prese $(grep -o ': presa' /tmp/fl_log.txt | wc -l) · pubblicazioni sul sito $npub · ultime: $(grep -o '[^·]*: presa' /tmp/fl_log.txt | tail -12 | tr '\n' ';')"
grep -q 'non ancora uscita' /tmp/fl_log.txt && echo "::notice title=Formazioni (micro) · tentativi a vuoto::$(grep -o '[^·]*non ancora uscita' /tmp/fl_log.txt | sort | uniq -c | sort -rn | head -10 | tr '\n' ';')"
exit 0
