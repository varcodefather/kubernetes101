#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export KUBECONFIG="$PWD/lab.kubeconfig"
test "$(kubectl config current-context)" = kind-cka-practice
certdir=$(mktemp -d)
trap 'rm -f "$certdir/tls.key" "$certdir/tls.crt"; rmdir "$certdir"' EXIT
openssl req -x509 -newkey rsa:2048 -nodes -days 30 -subj '/CN=compat.cka.test' \
    -addext 'subjectAltName=DNS:compat.cka.test' \
    -keyout "$certdir/tls.key" -out "$certdir/tls.crt" 2>/dev/null
kubectl -n cka-lab create secret tls compat-cert --cert="$certdir/tls.crt" --key="$certdir/tls.key"
kubectl -n cka-lab create configmap compat-config --from-file=default.conf=compat.conf
kubectl apply -f compat.yaml
