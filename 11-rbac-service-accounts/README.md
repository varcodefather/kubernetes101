# ServiceAccounts and RBAC: read one named ConfigMap

Use a real in-Pod Kubernetes API client to test a narrow permission. Initially five requests are forbidden. A Role and RoleBinding allow only `get` on `lesson-config` in namespace `rbac101`; four other requests remain forbidden. Remove the binding and the same running Pod loses that permission.

Requires Docker, kind and kubectl. Use unused lab names and work from this folder. Fixtures contain disposable demonstration data only, including a dummy Secret. No cloud account or real application credentials are needed.

## Prepare the local cluster

```sh
export KUBECONFIG="$PWD/lab.kubeconfig"
docker build -t rbac-reader:v1 .
kind create cluster --name rbac-demo --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed --wait 120s
kind load docker-image rbac-reader:v1 --name rbac-demo
kubectl apply -f fixtures.yaml -f serviceaccount.yaml -f client.yaml -f service.yaml
kubectl rollout status deployment/api-reader -n rbac101 --timeout=120s
kubectl port-forward -n rbac101 --address 127.0.0.1 service/api-reader 18092:80
```

Open <http://127.0.0.1:18092>. Leave the forward running in a separate terminal while applying permissions. The app uses its own projected ServiceAccount token inside the Pod, verifies API TLS with the mounted CA, and displays request statuses rather than credentials or Secret contents.

The `config-reader` ServiceAccount defaults token automount to false. This particular API-client Pod explicitly sets `automountServiceAccountToken: true`, so only its intended API use opts into the mount. The client does not use your administrative kubeconfig.

## Check the denied baseline

The app makes these five real API requests:

| Request | Initial result |
| --- | --- |
| Get `rbac101/lesson-config` | 403 |
| Get another ConfigMap in `rbac101` | 403 |
| List ConfigMaps in `rbac101` | 403 |
| Get the dummy Secret in `rbac101` | 403 |
| Get `rbac-other/lesson-config` | 403 |

The server itself can be ready while its API requests are forbidden. Browser connectivity and Kubernetes API authorization are separate checks.

## Define a Role, then bind it

Read `role.yaml`. Its empty API group selects core resources; `resources: ["configmaps"]`, `resourceNames: ["lesson-config"]` and `verbs: ["get"]` restrict the operation. The Role belongs to `rbac101`.

```sh
kubectl apply -f role.yaml
```

Reload the page. All five requests should still return 403: defining a Role alone has not assigned it to the client. Read `rolebinding.yaml`, following its ServiceAccount subject and Role reference, then apply it:

```sh
kubectl apply -f rolebinding.yaml
```

Reload again. The named ConfigMap request should return 200 with `Read exactly this named ConfigMap`; all four other requests remain 403. A named-resource `get` permission does not grant collection listing, access to another ConfigMap, Secret access or the same name in a different namespace.

## Revoke the permission on the running client

```sh
kubectl delete rolebinding app-reads-lesson-config -n rbac101
```

Reload and check that all five requests return 403 again. The actual rehearsal compared the client Pod UID before and after the permission changes; it stayed the same. The repair and revocation were tested by a live ServiceAccount client, not inferred solely from an administrative impersonation command.

## Cleanup

Stop port-forward with Ctrl+C, then remove only this disposable cluster and image:

```sh
kind delete cluster --name rbac-demo --kubeconfig "$KUBECONFIG"
docker image rm rbac-reader:v1
unset KUBECONFIG
```

Real local rehearsal verified baseline denial, Role without binding, the single allowed named read, continued denial of four other requests, revocation without Pod replacement, and cleanup. [Kubernetes RBAC reference](https://kubernetes.io/docs/reference/access-authn-authz/rbac/).
