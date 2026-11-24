#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export KUBECONFIG="$PWD/lab.kubeconfig"
test "$(kubectl config current-context)" = kind-cka-practice
mkdir -p answers
ns=(kubectl -n cka-lab)
node=cka-practice-control-plane
subject=system:serviceaccount:cka-lab:reporter
fqdn=web-http.cka-lab.svc.cluster.local
gateway_selector='gateway.envoyproxy.io/owning-gateway-namespace=cka-lab,gateway.envoyproxy.io/owning-gateway-name=practice-gateway'

rollout() { "${ns[@]}" rollout status "deployment/$1" --timeout=90s; }
ready() { "${ns[@]}" wait "pod/$1" --for=condition=Ready --timeout=90s; }
expect() { [[ $1 == "$2" ]] || { echo "Expected [$2], got [$1]" >&2; return 1; }; }
web_release() {
    "${ns[@]}" get deploy web -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="RELEASE")].value}'
}

case "${1:-}" in
    1)
        docker exec "$node" kubeadm certs check-expiration | tee answers/certificates.txt
        grep -Eq '^apiserver[[:space:]]' answers/certificates.txt
        expect "$(kubectl get --raw='/readyz')" ok
        ;;
    2)
        "${ns[@]}" create serviceaccount reporter
        "${ns[@]}" create role report-read --verb=get --resource=configmaps --resource-name=cluster-notes
        "${ns[@]}" create rolebinding reporter-can-read --role=report-read --serviceaccount=cka-lab:reporter
        expect "$("${ns[@]}" auth can-i get configmap/cluster-notes --as="$subject")" yes
        expect "$("${ns[@]}" auth can-i get configmap/spare-notes --as="$subject" || :)" no
        expect "$("${ns[@]}" auth can-i list configmaps --as="$subject" || :)" no
        expect "$("${ns[@]}" auth can-i patch configmap/cluster-notes --as="$subject" || :)" no
        ;;
    3)
        helm template status charts/status -n cka-lab --set-string site=perth > status-rendered.yaml
        grep -Fq 'site: "perth"' status-rendered.yaml
        helm install status charts/status -n cka-lab --set-string site=perth
        expect "$("${ns[@]}" get cm status-settings -o jsonpath='{.data.site}')" perth
        ;;
    4)
        kubectl apply -k customize/exam
        expect "$("${ns[@]}" get cm lab-mode -o jsonpath='{.data.MODE}')" exam
        kubectl kustomize customize/base | grep -Fq 'MODE: dev'
        ;;
    5)
        "${ns[@]}" set env deployment/web RELEASE=trial
        rollout web
        expect "$(web_release)" trial
        "${ns[@]}" rollout history deployment/web | tee answers/trial-rollout.txt
        "${ns[@]}" rollout undo deployment/web
        rollout web
        expect "$(web_release)" base
        ;;
    6)
        kubectl patch --local -f sidecar-base.yaml --patch-file solutions/reader-patch.yaml -o yaml > answers/log-reader.yaml
        kubectl apply -f answers/log-reader.yaml
        ready log-reader
        for _ in {1..20}; do
            if "${ns[@]}" logs log-reader -c reader | grep -Fq cka-log-ready; then
                echo cka-log-ready
                exit 0
            fi
            sleep 1
        done
        echo "Reader did not receive the application log." >&2
        exit 1
        ;;
    7)
        "${ns[@]}" autoscale deployment web --cpu=65% --min=2 --max=4
        expect "$("${ns[@]}" get hpa web -o jsonpath='{.spec.minReplicas}/{.spec.maxReplicas}/{.spec.metrics[0].resource.target.averageUtilization}')" 2/4/65
        "${ns[@]}" get hpa web
        ;;
    8)
        "${ns[@]}" get ingress legacy-ingress
        kubectl apply -f solutions/route.yaml
        "${ns[@]}" wait gateway/practice-gateway --for=condition=Programmed --timeout=150s
        expect "$("${ns[@]}" get httproute practice-route -o jsonpath='{.status.parents[0].conditions[?(@.type=="Accepted")].status}')" True
        expect "$("${ns[@]}" get httproute practice-route -o jsonpath='{.status.parents[0].conditions[?(@.type=="ResolvedRefs")].status}')" True
        gateway_service=$(kubectl -n envoy-gateway-system get svc -l "$gateway_selector" -o jsonpath='{.items[0].metadata.name}')
        test -n "$gateway_service"
        kubectl -n envoy-gateway-system rollout status deploy -l "$gateway_selector" --timeout=120s
        expect "$("${ns[@]}" exec client -- wget -qO- -T 4 --header 'Host: app.cka.test' "http://$gateway_service.envoy-gateway-system.svc.cluster.local/")" 'CKA practice web'
        ;;
    9)
        rollout policy-web
        kubectl -n probe exec outsider -- wget -qO /dev/null -T 4 http://policy-web.cka-lab.svc.cluster.local/
        kubectl apply -f solutions/policy.yaml
        "${ns[@]}" exec client -- wget -qO /dev/null -T 4 http://policy-web/
        denied=false
        for _ in {1..15}; do
            if ! kubectl -n probe exec outsider -- wget -qO /dev/null -T 3 http://policy-web.cka-lab.svc.cluster.local/; then
                denied=true
                break
            fi
            sleep 1
        done
        expect "$denied" true
        expect "$(kubectl -n probe exec outsider -- wget -qO- -T 4 "http://$fqdn/")" 'CKA practice web'
        ;;
    10)
        kubectl -n probe exec outsider -- nslookup "$fqdn"
        expect "$(kubectl -n probe exec outsider -- wget -qO- -T 4 "http://$fqdn/")" 'CKA practice web'
        ;;
    11)
        kubectl apply -f solutions/archive-claim.yaml
        "${ns[@]}" wait pvc/archive-data --for=jsonpath='{.status.phase}'=Bound --timeout=90s
        expect "$("${ns[@]}" get pvc archive-data -o jsonpath='{.spec.volumeName}')" archive-pv
        ;;
    12)
        kubectl apply -f writer.yaml
        ready writer
        "${ns[@]}" exec writer -- sh -c 'echo checkpoint-42 > /data/checkpoint'
        old_uid=$("${ns[@]}" get pod writer -o jsonpath='{.metadata.uid}')
        old_volume=$("${ns[@]}" get pvc scratch-data -o jsonpath='{.spec.volumeName}')
        test -n "$old_volume"
        "${ns[@]}" delete pod writer --wait --timeout=90s
        kubectl apply -f writer.yaml
        ready writer
        test "$("${ns[@]}" get pod writer -o jsonpath='{.metadata.uid}')" != "$old_uid"
        expect "$("${ns[@]}" get pvc scratch-data -o jsonpath='{.spec.volumeName}')" "$old_volume"
        expect "$("${ns[@]}" exec writer -- cat /data/checkpoint)" checkpoint-42
        ;;
    13)
        selector='kubernetes.io/service-name=legacy-web'
        before=$("${ns[@]}" get endpointslices -l "$selector" -o jsonpath='{.items[*].endpoints[*].addresses[*]}')
        expect "$before" ''
        "${ns[@]}" patch svc legacy-web --type=merge -p '{"spec":{"selector":{"app":"web"}}}'
        for _ in {1..30}; do
            addresses=$("${ns[@]}" get endpointslices -l "$selector" -o jsonpath='{.items[*].endpoints[?(@.conditions.ready==true)].addresses[*]}')
            if [[ -n $addresses ]]; then break; fi
            sleep 1
        done
        test -n "$addresses"
        expect "$("${ns[@]}" exec client -- wget -qO- -T 4 http://legacy-web/)" 'CKA practice web'
        ;;
    14)
        "${ns[@]}" logs deployment/broken-worker | grep -F 'missing GREETING'
        "${ns[@]}" set env deploy/broken-worker GREETING=ready
        rollout broken-worker
        expect "$("${ns[@]}" logs deployment/broken-worker)" ready
        ;;
    15)
        "${ns[@]}" describe pod -l app=oversized | grep -F 'Insufficient cpu'
        "${ns[@]}" patch deployment oversized --type=strategic -p '{"spec":{"template":{"spec":{"containers":[{"name":"worker","resources":{"requests":{"cpu":"100m"}}}]}}}}'
        rollout oversized
        expect "$("${ns[@]}" get deploy oversized -o jsonpath='{.spec.template.spec.containers[0].resources.requests.cpu}/{.spec.template.spec.containers[0].resources.requests.memory}')" 100m/32Mi
        ;;
    16)
        rollout compat-web
        bash check-tls.sh before
        sed 's/ssl_protocols TLSv1.3;/ssl_protocols TLSv1.2 TLSv1.3;/' compat.conf > answers/compat.conf
        "${ns[@]}" create configmap compat-config --from-file=default.conf=answers/compat.conf --dry-run=client -o yaml | "${ns[@]}" apply -f -
        "${ns[@]}" rollout restart deployment/compat-web
        rollout compat-web
        bash check-tls.sh after
        ;;
    17)
        if ! docker exec "$node" test -f /tmp/cka-apiserver-known-good.yaml; then
            bash break-control-plane.sh
        fi
        docker exec "$node" crictl ps -a --name kube-apiserver
        docker exec "$node" sh -eu -c '
            for container in $(crictl ps -a --name kube-apiserver -q); do
                logs=$(crictl logs "$container" 2>&1 || :)
                if echo "$logs" | grep -q "12379"; then
                    echo "$logs" | grep "12379" | tail -n 3
                    exit 0
                fi
            done
            exit 1
        '
        etcd_url=$(docker exec "$node" sed -n 's/^[[:space:]]*- --advertise-client-urls=\(https:[^, ]*\).*$/\1/p' /etc/kubernetes/manifests/etcd.yaml)
        [[ $etcd_url =~ ^https://[a-zA-Z0-9.]+:2379$ ]]
        docker exec "$node" grep -F -- '--etcd-servers=' /etc/kubernetes/manifests/kube-apiserver.yaml
        docker exec "$node" sh -eu -c '
            manifest=/etc/kubernetes/manifests/kube-apiserver.yaml
            grep -q -- ":12379$" "$manifest"
            sed "s@--etcd-servers=.*@--etcd-servers=$1@" "$manifest" >/tmp/cka-apiserver-fixed.yaml
            mv /tmp/cka-apiserver-fixed.yaml "$manifest"
        ' sh "$etcd_url"
        status=
        for _ in {1..60}; do
            status=$(kubectl --request-timeout=2s get --raw='/readyz' 2>/dev/null || :)
            if [[ $status == ok ]]; then break; fi
            sleep 2
        done
        expect "$status" ok
        "${ns[@]}" get deployment web
        ;;
    *)
        echo "Usage: bash solve.sh <task number 1–17>" >&2
        exit 2
        ;;
esac
echo "Task $1 verified."
