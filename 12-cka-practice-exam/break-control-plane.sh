#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export KUBECONFIG="$PWD/lab.kubeconfig"
node=cka-practice-control-plane
test "$(kubectl config current-context)" = kind-cka-practice
test "$(docker inspect --format '{{index .Config.Labels "io.x-k8s.kind.cluster"}}' "$node")" = cka-practice
kubectl get --raw='/readyz' >/dev/null

docker exec "$node" sh -eu -c '
    manifest=/etc/kubernetes/manifests/kube-apiserver.yaml
    backup=/tmp/cka-apiserver-known-good.yaml
    test ! -e "$backup"
    grep -Eq -- "--etcd-servers=https://[^[:space:]]+:2379$" "$manifest"
    cp "$manifest" "$backup"
    sed -E "s@(--etcd-servers=https://[^[:space:]]+):2379\$@\1:12379@" "$backup" >/tmp/cka-apiserver-broken.yaml
    grep -q -- ":12379$" /tmp/cka-apiserver-broken.yaml
    mv /tmp/cka-apiserver-broken.yaml "$manifest"
'

for _ in {1..60}; do
    if ! kubectl --request-timeout=2s get --raw='/readyz' >/dev/null 2>&1 &&
        docker exec "$node" sh -c '
            for container in $(crictl ps -a --name kube-apiserver -q); do
                crictl logs "$container" 2>&1 | grep -q "12379" && exit 0
            done
            exit 1
        '; then
        echo "Practice API server is unavailable. A failed attempt logged the configured endpoint."
        exit 0
    fi
    sleep 2
done
echo "API server stayed available. Check the practice node logs." >&2
exit 1
