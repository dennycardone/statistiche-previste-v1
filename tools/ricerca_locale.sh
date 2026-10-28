#!/bin/bash
# 28/10/2026: archivio di ricerca in locale (solo rami pubblici). Gli archivi privati restano in GitHub Actions.
set -e
cd "$(dirname "$0")/.."
mkdir -p ricerca pub
for b in ricerca:ricerca formazioni:ricerca/form2 statextra:ricerca/sx storico:ricerca/storico tempi:ricerca/tempi; do
  br=${b%%:*}; dir=${b#*:}; mkdir -p "$dir"
  git fetch -q --depth 1 origin "$br" && git archive FETCH_HEAD | tar -x -C "$dir" && echo "$br → $dir: $(ls "$dir" | wc -l) file"
done
git fetch -q --depth 1 origin pages && for f in bundle bundle_storico extra tiri_area fuorigioco; do git show FETCH_HEAD:data/$f.json > pub/$f.json; done && echo "pages → pub/"
