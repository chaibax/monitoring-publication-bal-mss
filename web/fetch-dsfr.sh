#!/usr/bin/env bash
# Installe le DSFR auto-hébergé dans web/dsfr/. La page ne doit dépendre
# d'aucun service tiers à l'exécution. Dossier volumineux, hors Git.
set -euo pipefail
VER="${1:-1.15.1}"
cd "$(dirname "$0")"
curl -sL "https://registry.npmjs.org/@gouvfr/dsfr/-/dsfr-$VER.tgz" -o /tmp/dsfr.tgz
rm -rf /tmp/dsfr-x && mkdir -p /tmp/dsfr-x
tar xzf /tmp/dsfr.tgz -C /tmp/dsfr-x
rm -rf dsfr && mkdir -p dsfr
cp -R /tmp/dsfr-x/package/dist/* dsfr/
cd dsfr
rm -rf component core analytics legacy artwork scheme dsfr example
find . -maxdepth 1 -name '*.css' ! -name 'dsfr.min.css' -delete
find utility -maxdepth 1 -name '*.css' ! -name 'utility.min.css' -delete
find utility -mindepth 1 -type d -exec rm -rf {} + 2>/dev/null || true
find . -maxdepth 1 -name '*.js' ! -name 'dsfr.module.min.js' ! -name 'dsfr.nomodule.min.js' -delete
find . -name '*.map' -delete
echo "DSFR $VER installé ($(du -sh . | cut -f1))"
