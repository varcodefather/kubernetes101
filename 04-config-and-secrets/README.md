# ConfigMaps and Secrets: change configuration without rebuilding

Run one local web app, diagnose a missing required Secret key, then compare environment variables with a mounted ConfigMap file. No cloud account needed.

All token values here are **dummy examples**. Do not replace them with real credentials in this public repository. Base64 encoding is not encryption; Secret access and encryption-at-rest depend on your cluster configuration.

## Before starting

Docker must be running; install kind and kubectl first. Rehearsed on Linux with kind 0.33.0, pinned Kubernetes node 1.36.4 and kubectl 1.37.1. Actual checks covered the missing-key error, initial HTTP/API responses, live banner update without Pod replacement, unchanged environment values, and replacement Pod using the same image ID with new settings.

```bash
git clone https://github.com/varcodefather/kubernetes101.git
cd kubernetes101/04-config-and-secrets
```

The video starts with only `starter/app.py`, `starter/Dockerfile` and `starter/.dockerignore`, then writes the manifests in Neovim. This parent folder includes the completed manifests, so you can run the commands below without typing them from scratch.

## Create the isolated lab and image

Keep using this terminal after setting `KUBECONFIG`.

```bash
export KUBECONFIG="$PWD/lab.kubeconfig"
kind create cluster --name config-demo --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed --kubeconfig lab.kubeconfig --wait 180s
kubectl config current-context
kubectl get nodes
kubectl create namespace config101
docker build -t config-web:v1 .
kind load docker-image config-web:v1 --name config-demo
kubectl apply -f configmap.yaml
kubectl apply -f secret.example.yaml
```

Context should be `kind-config-demo`; node should be `Ready`. `.dockerignore` permits only `app.py` and `Dockerfile` into the build context, excluding kubeconfig and manifests.

## Diagnose the deliberately broken reference

```bash
kubectl apply -f deployment-broken.yaml
kubectl rollout status deployment/config-app -n config101 --timeout=10s
kubectl get pods -n config101
kubectl describe pods -n config101 -l app=config-app
```

The rollout timeout is expected. The Pod reaches `CreateContainerConfigError`; its Events identify missing key `API_TOKEN_TYPO` in `app-credentials`. The application has not started. Read the current events if your status differs.

`deployment.yaml` fixes that reference to `API_TOKEN`:

```bash
kubectl apply -f deployment.yaml
kubectl rollout status deployment/config-app -n config101 --timeout=180s
kubectl get pods -n config101
kubectl expose deployment config-app -n config101 --port=80 --target-port=8000
kubectl port-forward --address 127.0.0.1 -n config101 service/config-app 8080:80
```

Leave the forward running; open **http://localhost:8080** on that same machine. Expect `Hello from version one` and `Banner version one`. Test `example-only-key-one`: `200 OK`. A wrong example key returns `401 Unauthorized`.

Press **Ctrl+C** in the forwarding terminal before editing the settings.

## Update both objects without replacing the Pod

Open `configmap.yaml` in your editor and change both `version one` values to `version two`. In `secret.example.yaml`, change the dummy token to `example-only-key-two`. Save both files.

```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.example.yaml
kubectl get pods -n config101
kubectl port-forward --address 127.0.0.1 -n config101 service/config-app 8080:80
```

Reload the browser. Projected ConfigMap files update eventually; allow time and reload again. This app reads the file on every page request. Expect:

| Check | Existing process after object updates |
| --- | --- |
| Greeting environment variable | `Hello from version one` |
| Mounted banner file | `Banner version two` |
| `example-only-key-one` | `200 OK` |
| `example-only-key-two` | `401 Unauthorized` |

Updating a ConfigMap or Secret does not automatically replace this Pod. Environment variables received when the process started remain unchanged. The mounted directory receives projected file updates; `subPath` mounts do not receive these automatic updates. Other applications may cache files and need an application reload too.

## Replace the process and verify

Stop the forward with **Ctrl+C**, then:

```bash
kubectl rollout restart deployment/config-app -n config101
kubectl rollout status deployment/config-app -n config101 --timeout=180s
kubectl get pods -n config101
kubectl get deployment config-app -n config101 -o wide
kubectl port-forward --address 127.0.0.1 -n config101 service/config-app 8080:80
```

The image remains `config-web:v1`. Reload the page: greeting and banner both show version two; the new dummy key succeeds and the old dummy key fails. A fresh forward avoids relying on a connection to the replaced Pod.

## Delete the object while the process keeps running

Stop the forward, then remove only the dummy Secret:

```bash
kubectl delete secret app-credentials -n config101
kubectl port-forward --address 127.0.0.1 -n config101 service/config-app 8080:80
```

Reload the page and test `example-only-key-two`: it still returns `200 OK`. An unrelated key is rejected. The process already received its environment value, so deleting the Kubernetes object does not erase that value from the running application. Credential revocation requires an application-aware rotation/replacement workflow.

Stop the forward and restore the required example object before any future Pod replacement:

```bash
kubectl apply -f secret.example.yaml
kubectl get secret app-credentials -n config101
```

This deletion and restore were rehearsed against the actual local app; all keys are dummy examples.

## Cleanup

Stop the forward, then delete only this named lab and image:

```bash
kind delete cluster --name config-demo --kubeconfig lab.kubeconfig
kind get clusters
docker image rm config-web:v1
```

Keep `lab.kubeconfig` private and out of Git. Keep the source/manifests if you want to repeat the exercise. To return to the initial state, restore version-one values in the two settings files.

## Official references

- [ConfigMaps and update behavior](https://kubernetes.io/docs/concepts/configuration/configmap/)
- [Secrets and stringData](https://kubernetes.io/docs/concepts/configuration/secret/)
- [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)

This small server demonstrates configuration behavior. Its dummy-key endpoint is not a production authentication implementation.
