# kind 101 — first local Kubernetes cluster

Create a small local cluster, run nginx, reach it in a browser, observe Pod replacement and repair a Service selector. Companion lesson for Back to Basics: first local Kubernetes cluster.

Tested: kind 0.33.0, Kubernetes node 1.37.0, kubectl 1.37.1, Docker 29.9.2, Linux amd64 in a local VM. No cloud account required. Docker must be running; ports in this walkthrough refer to the machine where kubectl runs. Docker Desktop on macOS supplies a Linux environment.

## Before starting

Use an empty lab folder, or copy these example files into a fresh folder. Tutorial creates/edits them in Neovim. Choose unused cluster name `basics`; do not run two copies of this lab at once. Cluster has one local node, and app uses namespace `kind101`. Keep the lab kubeconfig private; it includes credentials for this cluster. Do not commit it.

For each kubectl terminal:

```bash
export KUBECONFIG="$PWD/lab.kubeconfig"
```

Set this only once the lab file exists and check `kubectl config current-context` before changes. Expected: `kind-basics`. Using dedicated file avoids merging this lesson into your normal kubeconfig. Close lab terminals when finished so their environment does not affect later work.

## Walkthrough

### 01 — What we are building

### 02 — Create a local cluster

**Check the tools**

```bash
kind version
kubectl version --client
```

**Check Docker access**

```bash
docker version
kind get clusters
```

**Describe one node**

Create `kind.yaml` in Neovim, then save:

```yaml
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
```

**Create the cluster with its own kubeconfig**

```bash
kind create cluster --name basics --config kind.yaml --kubeconfig ./lab.kubeconfig --image kindest/node:v1.37.0@sha256:a1ed56cfb0e7b93589bdf97c8cd566405a265939e3620fc4f5de89adff580ae5 --wait 180s
```

**Use the lab connection in this terminal**

```bash
export KUBECONFIG="$PWD/lab.kubeconfig"
kubectl config current-context
```

### 03 — Read the cluster state

**Find the Ready node**

```bash
kubectl get nodes
docker ps
```

**See the system Pods**

```bash
kubectl get pods -n kube-system
kubectl get namespaces
```

**Create our app namespace**

```bash
kubectl create namespace kind101
kubectl get pods -n kind101
```

### 04 — Describe and run the app

**Start a Deployment file**

Append to `deployment.yaml` in Neovim:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: kind101
```

**Ask for two replicas**

Append to `deployment.yaml` in Neovim:

```yaml
spec:
  replicas: 2
  selector:
    matchLabels:
      app: web
```

**Describe the Pod template**

Append to `deployment.yaml` in Neovim:

```yaml
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
        - name: nginx
          image: nginx:alpine
          ports:
            - containerPort: 80
```

**Save and read the whole file**

Press Escape, then `:wq`, pause to read the command, then Enter. Review the saved file with `cat deployment.yaml`.

**Apply the Deployment**

```bash
kubectl apply -f deployment.yaml
kubectl rollout status deployment/web -n kind101 --timeout=180s
```

**Read the Deployment and Pods**

```bash
kubectl get deployment -n kind101
kubectl get pods -n kind101 -o wide
```

### 05 — Reach the app in a browser

**Give the Pods a Service**

Append to `service.yaml` in Neovim:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: kind101
spec:
  selector:
    app: web
```

**Map the Service port**

Append to `service.yaml` in Neovim:

```yaml
  ports:
    - port: 80
      targetPort: 80
```

**Save the Service file**

Press Escape, then `:wq`, pause to read the command, then Enter. Review the saved file with `cat deployment.yaml`.

**Apply and inspect the Service**

```bash
kubectl apply -f service.yaml
kubectl get service,endpointslice -n kind101
```

**Start the temporary local connection**

Run in foreground; leave this terminal open during browser check. Port 8080 must be free.

```bash
kubectl port-forward -n kind101 --address 127.0.0.1 service/web 8080:80
```

**Open the actual website**

Open http://127.0.0.1:8080/ in a browser on the machine running kubectl. Expected: **Welcome to nginx!**.

**Stop the forward**

Press **Ctrl+C** in the terminal running port-forward. Wait for prompt before next command.

### 06 — Watch Kubernetes replace a Pod

**Choose one current Pod**

```bash
kubectl get pods -n kind101 -l app=web
```

**Delete one selected Pod**

Choose one Pod name from the preceding `kubectl get pods` result. Replace `SELECTED_POD` below with that observed name; do not run the placeholder literally.

```bash
kubectl delete pod -n kind101 SELECTED_POD
kubectl rollout status deployment/web -n kind101 --timeout=120s
```

**Compare the replacement**

```bash
kubectl get pods -n kind101 -l app=web
kubectl get deployment web -n kind101
```

**Check the app after replacement**

Run in foreground; leave this terminal open during browser check. Port 8080 must be free.

```bash
kubectl port-forward -n kind101 --address 127.0.0.1 service/web 8080:80
```

**Verify the recovered page**

Open http://127.0.0.1:8080/ in a browser on the machine running kubectl. Expected: **Welcome to nginx!**.

**Close the test connection**

Press **Ctrl+C** in the terminal running port-forward. Wait for prompt before next command.

### 07 — Fix a Service that cannot find its Pods

**Make one deliberate selector mistake**

In `service.yaml`, change `app: web` to `app: wrong-label`, then save.

**Apply the broken Service**

```bash
kubectl apply -f service.yaml
kubectl get pods -n kind101 --show-labels
```

**Read the missing backends**

```bash
kubectl describe service web -n kind101
kubectl get endpointslices -n kind101 -l kubernetes.io/service-name=web
```

Expected: Service selector wrong-label; EndpointSlice endpoint list empty or null after controller update.

**Restore the matching selector**

In `service.yaml`, change `app: wrong-label` to `app: web`, then save.

**Apply the repair and check endpoints**

```bash
kubectl apply -f service.yaml
kubectl get endpointslices -n kind101 -l kubernetes.io/service-name=web
```

**Open a fresh forward**

Run in foreground; leave this terminal open during browser check. Port 8080 must be free.

```bash
kubectl port-forward -n kind101 --address 127.0.0.1 service/web 8080:80
```

**Verify the repaired app**

Open http://127.0.0.1:8080/ in a browser on the machine running kubectl. Expected: **Welcome to nginx!**.

### 08 — Clean up the lab

**Stop the last forward**

Press **Ctrl+C** in the terminal running port-forward. Wait for prompt before next command.

**Delete only this kind cluster**

```bash
kind delete cluster --name basics --kubeconfig ./lab.kubeconfig
```

**Check the lab is gone**

```bash
kind get clusters
docker ps
```

## Reading the checks

- Node: `Ready`.
- Deployment: two desired/ready replicas.
- Pods: two `Running`, each `1/1` ready. Names differ between runs.
- Service selector: `app: web`, matching Pod labels.
- EndpointSlices: two ready Pod endpoints after controller update. Empty or null endpoint lists both mean no backends for this Service.
- Browser: nginx welcome page through fresh local port-forward.

`containerPort: 80` in Deployment does not publish a laptop port. Service is internal. Port-forward chooses a Pod behind Service and can end if that Pod disappears; restart forward when needed. Stop old forward before testing selector changes, otherwise an established connection is not a fresh selector test.

Node image pinned from official kind 0.33.0 release. New machines download it; Kubernetes pulls nginx separately. Private kubeconfig and cluster data are temporary lab state. Cleanup deletes only cluster `basics`; keep manifests for another run. Avoid broad Docker prune commands.

## References

- https://kind.sigs.k8s.io/docs/user/quick-start/
- https://kind.sigs.k8s.io/docs/user/configuration/
- https://github.com/kubernetes-sigs/kind/releases/tag/v0.33.0
- https://kubernetes.io/docs/tutorials/kubernetes-basics/deploy-app/deploy-intro/
- https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/
