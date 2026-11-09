# Build locally, run in kind, update and roll back

Use Docker, kind 0.33.0 and kubectl with a disposable local cluster. The starting files build a static nginx website showing **Version 1**. No registry or cloud account needed.

## Create the lab

Run from this folder and keep using the same terminal:

```sh
export KUBECONFIG="$PWD/lab.kubeconfig"
kind create cluster --name image-demo \
  --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed \
  --kubeconfig lab.kubeconfig --wait 180s
kubectl config current-context
kubectl get nodes
kubectl create namespace image101
```

Expect context `kind-image-demo` and a Ready node. Keep generated `lab.kubeconfig` private; `.dockerignore` excludes it from the build context.

## Build and load version 1

```sh
docker build -t local-web:v1 .
docker image ls local-web
kind load docker-image local-web:v1 --name image-demo
kubectl apply -f deployment.yaml
kubectl rollout status deployment/web -n image101 --timeout=180s
kubectl get pods -n image101
kubectl expose deployment web -n image101 --port=80 --target-port=80
kubectl port-forward --address 127.0.0.1 -n image101 service/web 8080:80
```

Open [localhost:8080](http://localhost:8080/) in your browser. Expect the custom heading and **Version 1**. Leave the forward running during this check, then stop it with Ctrl+C.

Host Docker and the runtime inside a kind node have separate image stores. `kind load` imports the built image into the selected cluster. This manifest uses `imagePullPolicy: Never` for a preloaded local image; a registry-based deployment needs a policy appropriate to that workflow.

## Ship version 2

Open `site/index.html` in your editor, change `Version 1` to `Version 2` and save.

```sh
docker build -t local-web:v2 .
docker image ls local-web
kind load docker-image local-web:v2 --name image-demo
```

Edit `deployment.yaml`: change `image: local-web:v1` to `image: local-web:v2`, then save.

```sh
kubectl apply -f deployment.yaml
kubectl rollout status deployment/web -n image101 --timeout=180s
kubectl get pods -n image101
kubectl port-forward --address 127.0.0.1 -n image101 service/web 8080:80
```

Reload the browser. Expect **Version 2**. Stop the forward before continuing. Start a fresh forward after a rollout because an existing forwarding session is tied to a selected Pod.

## Roll back and record the decision

```sh
kubectl rollout history deployment/web -n image101
kubectl rollout undo deployment/web -n image101
kubectl rollout status deployment/web -n image101 --timeout=180s
```

The live Deployment now uses version 1. `rollout undo` does not edit your local manifest. Change its image back to `local-web:v1` and save so another apply will preserve the rollback.

```sh
kubectl apply -f deployment.yaml
kubectl rollout status deployment/web -n image101 --timeout=180s
kubectl get pods -n image101
kubectl port-forward --address 127.0.0.1 -n image101 service/web 8080:80
```

Reload the browser. Expect **Version 1**, even though the source page still says version 2: the older image kept its original copied content. Stop the forward.

## Clean up only this lab

```sh
kind delete cluster --name image-demo --kubeconfig lab.kubeconfig
kind get clusters
docker image rm local-web:v1 local-web:v2
```

References: [load images into kind](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster), [Docker build context and exclusions](https://docs.docker.com/build/concepts/context/#dockerignore-files), [Deployment rollbacks](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-back-a-deployment).
