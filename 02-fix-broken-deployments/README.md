# Fix image pull errors and crashing containers

Two local Kubernetes faults: an image tag that does not exist, then a container that exits immediately. Use a disposable kind cluster with Docker running, kind and kubectl installed.

Lab uses kind 0.33.0 with the pinned Kubernetes 1.36.4 node below.

## Start this lab

Run from this folder, using the same terminal throughout:

```sh
export KUBECONFIG="$PWD/lab.kubeconfig"
kind create cluster --name troubleshooting \
  --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed \
  --kubeconfig lab.kubeconfig --wait 180s
kubectl config current-context
kubectl get nodes
kubectl create namespace troubleshooting101
```

Context should be `kind-troubleshooting`; node should become `Ready`.

## Image cannot be downloaded

```sh
kubectl apply -f 01-image-pull-error.yaml
kubectl get pods -n troubleshooting101 --watch
```

Stop watching with Ctrl+C. Copy the name of the failing Pod into `<pod-name>`:

```sh
kubectl describe pod <pod-name> -n troubleshooting101
kubectl logs <pod-name> -n troubleshooting101 -c nginx
```

`nginx:missing-demo-tag` is deliberately invalid. Events explain the pull failure; application logs are unavailable because the container has not started.

Repair and check the rollout:

```sh
kubectl apply -f 03-working.yaml
kubectl rollout status deployment/web -n troubleshooting101 --timeout=180s
kubectl get pods -n troubleshooting101
kubectl expose deployment web -n troubleshooting101 --port=80 --target-port=80
kubectl port-forward --address 127.0.0.1 -n troubleshooting101 service/web 8080:80
```

Open [localhost:8080](http://localhost:8080/) in your browser. Expect the nginx welcome page. Stop the forward with Ctrl+C before continuing.

## Container starts, then exits

```sh
kubectl apply -f 02-startup-crash.yaml
kubectl get pods -n troubleshooting101 --watch
```

The new Pod restarts; its status eventually shows `CrashLoopBackOff`. The old healthy Pod can keep serving during this stalled rolling update. These examples set `minReadySeconds: 5`, so a replacement must remain ready for five seconds before it counts as available. This is distinct from a readiness probe.

Stop watching, then use the **failing replacement's** name:

```sh
kubectl get deployment web -n troubleshooting101
kubectl rollout status deployment/web -n troubleshooting101 --timeout=10s
kubectl describe pod <pod-name> -n troubleshooting101
kubectl logs <pod-name> -n troubleshooting101 -c nginx --timestamps
```

The short rollout timeout is expected to fail while the update is broken. Read the latest failed attempt with the command above. `--previous` requests an earlier container instance after a restart, when that instance is still retained; it is not needed for this example. The startup override writes `Demo startup error: missing config`, waits two seconds, then exits with code 1.

Repair and verify again:

```sh
kubectl apply -f 03-working.yaml
kubectl rollout status deployment/web -n troubleshooting101 --timeout=180s
kubectl get pods -n troubleshooting101
kubectl port-forward --address 127.0.0.1 -n troubleshooting101 service/web 8080:80
```

Reload the browser. A completed rollout plus a fresh application response confirms recovery.

## Clean up

Stop the forward, then remove only this lab:

```sh
kind delete cluster --name troubleshooting --kubeconfig lab.kubeconfig
kind get clusters
```

Companion examples intentionally use a moving `nginx:alpine` tag for a short local exercise. Pin tested image digests in reproducible production deployments.

References: [debug Pods](https://kubernetes.io/docs/tasks/debug/debug-application/debug-pods/), [container lifecycle](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/), [kubectl logs](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_logs/), [minimum ready seconds](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#min-ready-seconds).
