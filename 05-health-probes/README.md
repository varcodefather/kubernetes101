# Kubernetes health probes

Local lab for startup, readiness and liveness checks. Docker, kind and kubectl required. Run from this folder, with Docker running.

The app intentionally takes 20 seconds to become healthy. Its web controls create disposable failure markers under `/tmp`. Do not add these controls to a production app.

## Start the lab

```sh
export KUBECONFIG="$PWD/lab.kubeconfig"
kind create cluster --name probes-demo --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed --kubeconfig lab.kubeconfig --wait 180s
kubectl get nodes
kubectl create namespace probes101
docker build -t health-web:v1 .
kind load docker-image health-web:v1 --name probes-demo
kubectl apply -f deployment-without-startup.yaml
kubectl apply -f service.yaml
kubectl get pods -n probes101
```

The initial Deployment has readiness and liveness checks, but no startup check. Its liveness failure budget is shorter than the simulated startup time. Inspect the restarts and probe events:

```sh
kubectl describe pods -l app=health-app -n probes101 --show-events=true
```

`--show-events=true` keeps probe Events visible when more than one Pod matches.

Compare both Deployment files in Neovim. `deployment.yaml` adds a startup probe with a longer budget; the image and application code stay unchanged.

```sh
kubectl apply -f deployment.yaml
kubectl rollout status deployment/health-app -n probes101 --timeout=180s
kubectl get pods -n probes101
```

## Recognize a wrong probe path

This version keeps startup and liveness correct but asks readiness to check `/missing`, which the app does not serve:

```sh
kubectl apply -f deployment-wrong-ready-path.yaml
kubectl rollout status deployment/health-app -n probes101 --timeout=25s
kubectl get pods -n probes101
kubectl describe pods -l app=health-app -n probes101 --show-events=true
```

The timeout is expected. The new replica cannot become ready; its Events show a readiness response of `404`. The Deployment's existing healthy replicas remain available while this update is blocked. A container restart will not repair the incorrect path in its configuration.

Restore the known working template and wait for two ready app replicas:

```sh
kubectl apply -f deployment.yaml
kubectl rollout status deployment/health-app -n probes101 --timeout=180s
kubectl get pods -n probes101
```

## Reach the app through its Service

```sh
kubectl apply -f gateway.yaml
kubectl rollout status deployment/health-gateway -n probes101 --timeout=180s
kubectl port-forward --address 127.0.0.1 -n probes101 service/health-gateway 8080:80
```

Open <http://localhost:8080>. Keep the forward running; use another terminal in this folder for the remaining kubectl commands, exporting the same `KUBECONFIG` there.

The gateway is a small nginx reverse proxy. Browser requests pass through the **app's ClusterIP Service**, so readiness changes affect routing. Forwarding directly to `service/health-app` would select a Pod for the forwarding session and would not demonstrate Service load balancing.

## Readiness: stop routing new traffic to one replica

Start with two Ready replicas. Click **Simulate dependency failure**, then note the affected Pod name reported below the button. It may differ from the name on the page: each request can reach either replica.

```sh
kubectl get pods -n probes101 -o wide
kubectl get endpointslices -n probes101 -l kubernetes.io/service-name=health-app -o yaml
```

The affected Pod becomes `0/1` Ready, without a container restart. Its endpoint remains in the EndpointSlice with `ready: false`; it is no longer an eligible target for normal Service traffic. Reloading the page should show the other replica after that change propagates.

Restore the exact affected Pod, replacing `POD_NAME` with the name returned by the button:

```sh
kubectl exec -n probes101 POD_NAME -- rm /tmp/unready
kubectl get pods -n probes101
```

Wait for both replicas to be Ready before the next test.

## Liveness: restart a failed container

Click **Simulate liveness failure** and note the affected Pod name. Inspect its state and events:

```sh
kubectl get pods -n probes101
kubectl describe pod POD_NAME -n probes101
```

Liveness failure causes the container to restart. The Pod name and UID stay the same in this experiment; the container's restart count increases. The replacement process needs its simulated startup time again. Its startup probe prevents the liveness check from interrupting that startup. The failure marker was in the old container's writable layer and disappears on restart; it was not stored in a volume.

## Clean up

Stop the local forward with Ctrl+C, then remove this named lab and image:

```sh
kind delete cluster --name probes-demo --kubeconfig lab.kubeconfig
docker image rm health-web:v1
```

Source files remain on disk. No broad Docker prune is needed.

## References

- [Kubernetes probe configuration](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [EndpointSlice conditions](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/)
