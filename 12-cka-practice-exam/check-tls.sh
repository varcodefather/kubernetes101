#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export KUBECONFIG="$PWD/lab.kubeconfig"
test "$(kubectl config current-context)" = kind-cka-practice
mode=${1:-after}
[[ $mode == before || $mode == after ]]
port=${TLS_LAB_PORT:-18443}
work=$(mktemp -d)
forwarder=
cleanup() {
    if [[ -n $forwarder ]]; then
        kill "$forwarder" 2>/dev/null || :
        wait "$forwarder" 2>/dev/null || :
    fi
    rm -f "$work/cert.crt" "$work/forward.log"
    rmdir "$work"
}
trap cleanup EXIT
kubectl -n cka-lab get secret compat-cert -o jsonpath='{.data.tls\.crt}' | base64 -d > "$work/cert.crt"
kubectl -n cka-lab port-forward --address 127.0.0.1 svc/compat-web "$port:443" > "$work/forward.log" 2>&1 &
forwarder=$!
for _ in {1..50}; do
    if grep -Fq "Forwarding from 127.0.0.1:$port" "$work/forward.log"; then break; fi
    if ! kill -0 "$forwarder" 2>/dev/null; then cat "$work/forward.log"; exit 1; fi
    sleep .2
done
grep -Fq "Forwarding from 127.0.0.1:$port" "$work/forward.log"

request() {
    curl --fail --silent --show-error --max-time 5 --noproxy '*' \
        --cacert "$work/cert.crt" --resolve "compat.cka.test:$port:127.0.0.1" \
        "--tlsv$1" --tls-max "$1" "https://compat.cka.test:$port/"
}
message='CKA TLS compatibility'
test "$(request 1.3)" = "$message"
echo "TLS 1.3: $message"
if [[ $mode == before ]]; then
    result=0
    request 1.2 || result=$?
    test "$result" = 35
    echo "TLS 1.2: handshake rejected"
else
    test "$(request 1.2)" = "$message"
    echo "TLS 1.2: $message"
fi
