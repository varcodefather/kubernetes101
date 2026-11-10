# Kubernetes networking: follow the request

Run two small applications in kind and diagnose three different failures: a Service selector that matches no Pods, a wrong target port, and a misspelled backend name. Finish with a two-fault exercise.

Docker, kind and kubectl must already work. This is a local lab; no cloud account needed.

To follow the file authoring in the video, use the **starter** folder and create `service.yaml` as shown. Completed manifests and deliberately broken variants are in this folder. Commands below use those completed examples.

## Start from a working request

Run from this folder, with Docker running:

```sh
export KUBECONFIG="$PWD/lab.kubeconfig"
kind create cluster --name network-demo --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed --kubeconfig lab.kubeconfig --wait 180s
kubectl get nodes
kubectl create namespace network101
docker build -t network-web:v1 .
kind load docker-image network-web:v1 --name network-demo
kubectl apply -f backend.yaml
kubectl apply -f frontend.yaml
kubectl apply -f service.yaml
kubectl rollout status deployment/backend -n network101 --timeout=180s
kubectl rollout status deployment/frontend -n network101 --timeout=180s
```

The image includes BIND lookup tools for this diagnostic lab. `ROLE` selects the frontend or backend behavior; both run the same image and listen on container port 8000. The backend Service exposes port 80 and forwards it to port 8000 on matching backend Pods.

Keep the following command running in another terminal. Export the same **absolute** `KUBECONFIG` path there first; `$PWD` must refer to this lab folder.

```sh
kubectl port-forward --address 127.0.0.1 -n network101 service/frontend 8080:80
```

Open [localhost:8080](http://localhost:8080/). Expect **Backend reached**, the requested backend address, and a backend Pod name. Repeated requests can reach either backend; fixed alternation is not guaranteed.

The local forward selects a frontend Pod. Each frontend request then traverses the **backend ClusterIP Service**. Forwarding directly to the backend Service would select a backend Pod for that forwarding session and would not test normal backend Service routing.

## Wrong selector: no eligible backend addresses

```sh
kubectl apply -f service-wrong-selector.yaml
kubectl get pods -n network101 --show-labels
kubectl describe service backend -n network101
kubectl get endpointslices -n network101 -l kubernetes.io/service-name=backend -o yaml
```

Reload the browser. The frontend answers but cannot get a backend response. Backend Pods remain Ready, while the Service's `app: backned` selector matches none of their `app: backend` labels. An empty EndpointSlice object can still exist; inspect its endpoints, not just its name.

Repair using the correct saved manifest, then wait for addresses to return and reload:

```sh
kubectl apply -f service.yaml
kubectl get endpointslices -n network101 -l kubernetes.io/service-name=backend
```

## Wrong target port: addresses exist, listener mismatch

```sh
kubectl apply -f service-wrong-port.yaml
kubectl exec -n network101 deployment/frontend -- nslookup backend
kubectl get endpointslices -n network101 -l kubernetes.io/service-name=backend -o yaml
kubectl exec -n network101 deployment/backend -- wget -qO- http://127.0.0.1:8000
```

Reload the browser to observe failure. Name lookup works and ready backend addresses exist, but the EndpointSlice port is 8001. The direct request inside a backend Pod succeeds on port 8000. That `127.0.0.1` is inside the Pod where the command runs; it bypasses the Service for diagnosis.

`containerPort` documents a port; it does not make a process listen. Compare the Service mapping with the actual listener.

```sh
kubectl apply -f service.yaml
```

Reload and verify **Backend reached**. Neither Service repair requires replacing the app Pods.

## Wrong name: inspect the caller's lookup

Stop the local forward with Ctrl+C before replacing the frontend:

```sh
kubectl apply -f frontend-wrong-dns.yaml
kubectl rollout status deployment/frontend -n network101 --timeout=180s
```

Restart the forward in its terminal, then reload. The page requests `http://backned` and reports **Name lookup failed**. The app retains the resolver's error details as well.

```sh
kubectl exec -n network101 deployment/frontend -- nslookup backned
kubectl exec -n network101 deployment/frontend -- nslookup backend
```

The first name does not identify a Service in this lab; the real `backend` name resolves. Correct the caller configuration rather than changing a working Service.

Stop the forward, restore the frontend and wait for rollout:

```sh
kubectl apply -f frontend.yaml
kubectl rollout status deployment/frontend -n network101 --timeout=180s
```

Restart the forward and verify the browser response. A forwarding session ends when its selected Pod terminates; a dropped local forward is separate from the backend DNS fault.

## Namespace-relative Service names

Create a disposable client in a different namespace:

```sh
kubectl create namespace client101
kubectl run dns-check -n client101 --image=network-web:v1 --image-pull-policy=Never --restart=Never --command -- sleep 3600
kubectl wait --for=condition=Ready pod/dns-check -n client101 --timeout=60s
kubectl exec -n client101 dns-check -- nslookup backend
kubectl exec -n client101 dns-check -- nslookup backend.network101
kubectl exec -n client101 dns-check -- nslookup backend.network101.svc.cluster.local
kubectl exec -n client101 dns-check -- wget -qO- http://backend.network101
```

The short `backend` lookup fails from `client101`, which has no backend Service. Including `network101` finds the existing Service in its namespace. This kind cluster uses the `cluster.local` domain; other clusters can use a different domain.

Namespaces alone do not provide network isolation. This lesson does not apply NetworkPolicies.

## Worked two-fault exercise

```sh
kubectl apply -f service-two-faults.yaml
```

Reload and diagnose before checking the fix. First repair the selector in your saved `service.yaml`, apply it, and inspect the endpoints. With that match restored, the wrong port still needs correcting. Set `targetPort: 8000`, save, apply, and verify the actual browser response.

If using the provided variants, apply `service-wrong-port.yaml` to represent the intermediate selector-only repair, then apply `service.yaml` for the complete fix. Keep your own final saved file correct so a later apply preserves the repair.

## Cleanup

Stop the forward, then remove only this named cluster and image:

```sh
kind delete cluster --name network-demo --kubeconfig lab.kubeconfig
docker image rm network-web:v1
```

Source files stay on disk. Keep the generated kubeconfig private.

## References

- [Service selectors and port mapping](https://kubernetes.io/docs/concepts/services-networking/service/)
- [DNS names and namespace search](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)
- [Debugging Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/)
- [kubectl port-forward selects a Pod](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_port-forward/)
