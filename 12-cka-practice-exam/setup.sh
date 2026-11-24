#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export KUBECONFIG="$PWD/lab.kubeconfig"
export KIND_EXPERIMENTAL_PROVIDER=docker
cluster=cka-practice
image=kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5

clusters=$(kind get clusters)
if [[ -e $KUBECONFIG ]] || grep -Fxq "$cluster" <<< "$clusters"; then
    echo "Cluster name or lab.kubeconfig already in use. Start with a fresh lab." >&2
    exit 1
fi
docker info >/dev/null
kind create cluster --name "$cluster" --config kind.yaml --image "$image"
test "$(kubectl config current-context)" = "kind-$cluster"

helm upgrade --install cilium oci://quay.io/cilium/charts/cilium \
    --version 1.20.5 --namespace kube-system --set ipam.mode=kubernetes \
    --set operator.replicas=1 --wait --timeout 8m
kubectl wait node --all --for=condition=Ready --timeout=180s
kubectl -n kube-system rollout status deployment/coredns --timeout=180s

helm upgrade --install eg oci://docker.io/envoyproxy/gateway-helm \
    --version v1.8.6 -n envoy-gateway-system --create-namespace --wait --timeout 8m

kubectl apply -f seed.yaml
bash setup-compat.sh
kubectl apply -f legacy-ingress.yaml
kubectl -n cka-lab rollout status deployment/web --timeout=120s
kubectl -n cka-lab wait pod/client --for=condition=Ready --timeout=120s
kubectl -n probe wait pod/outsider --for=condition=Ready --timeout=120s
kubectl get nodes -o wide
