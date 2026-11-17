# Kubernetes resources: requests, limits, Pending and OOMKilled

Run a small web app that holds 128 MiB of memory. Break scheduling with an oversized CPU request, then trigger a container memory limit and repair both faults.

Requires Docker, kind and kubectl. Run commands from this folder. Use a disposable local cluster; the cleanup deletes that cluster. No cloud account is involved.

## Type along from a clean starter

The completed files in this folder run as-is. To write the demonstrated manifests yourself,
copy `starter` into a **new** folder and keep the completed files as a reference.
Run these commands from this repository lesson folder:

```sh
mkdir -p ~/tutorials
mkdir ~/tutorials/kubernetes-resources
cp -a starter/. ~/tutorials/kubernetes-resources/
cd ~/tutorials/kubernetes-resources
```

Create the missing files in Neovim while following the video. The commands below
use the completed manifests; run them after authoring those files.

## Start the working app

Keep this lab's kubeconfig separate from your usual configuration. The cluster and image names below must be unused before starting.

```sh
export KUBECONFIG="$PWD/lab.kubeconfig"
docker build -t resources-web:v1 .
kind create cluster --name resources-demo --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed --wait 120s
kind load docker-image resources-web:v1 --name resources-demo
kubectl create namespace resources101
kubectl get nodes -o wide
kubectl apply -f deployment.yaml -f service.yaml
kubectl rollout status deployment/memory-demo -n resources101 --timeout=120s
kubectl port-forward -n resources101 --address 127.0.0.1 service/memory-demo 18090:80
```

Open <http://127.0.0.1:18090>. The page should show `Held allocation: 128 MiB`. Leave port-forward running while viewing the page; stop it with Ctrl+C before continuing. Restart it after each repaired rollout.

`deployment.yaml` requests 50 millicores and 160 MiB, with limits of 200 millicores and 256 MiB. Requests affect scheduling; they do not preallocate that amount of memory to the Python process. The app explicitly touches its bounded 128 MiB allocation.

## Diagnose an unschedulable Pod

```sh
kubectl apply -f too-large-request.yaml
kubectl get pods -n resources101
```

The new Pod requests 100 CPUs, exceeding the rehearsed node's 8 CPUs. Select its name from the Pending row and run `kubectl describe pod NAME -n resources101`, replacing `NAME` with that actual name. Its Events should include `Insufficient cpu`. Compare the request in the YAML with your node's allocatable CPU.

Restore the original manifest:

```sh
kubectl apply -f deployment.yaml
kubectl rollout status deployment/memory-demo -n resources101 --timeout=120s
```

## Diagnose a memory limit

Preview the live change before applying it:

```sh
kubectl diff -f small-memory-limit.yaml
```

The expected differences return exit status **1** without applying the file.
An API error is a different failure to investigate before continuing.

```sh
kubectl apply -f small-memory-limit.yaml
kubectl get pods -n resources101
```

This version requests 32 MiB and limits the container to 64 MiB. The app's attempted 128 MiB allocation exceeds that limit. Describe the restarting Pod by its actual name; inspect its last terminated state for `OOMKilled`. Run `kubectl logs NAME -n resources101 --previous` to read the previous container's allocation message. The rehearsal observed exit code 137 together with `OOMKilled`; exit code 137 alone does not identify the cause of every termination.

```sh
kubectl apply -f deployment.yaml
kubectl rollout status deployment/memory-demo -n resources101 --timeout=120s
kubectl port-forward -n resources101 --address 127.0.0.1 service/memory-demo 18090:80
```

Reopen the page and check the 128 MiB result. Stop port-forward before cleanup.

Check the saved repair agrees with the live Deployment:

```sh
kubectl diff -f deployment.yaml
```

Expect no output and exit status **0** after restoring the baseline. A repair
made only in the cluster can be undone later by applying a stale local file.

The default rolling update can retain the previous healthy Pod while the new Pod fails. A Pending or OOM-killed replacement does not imply that every existing replica is unavailable. This lesson demonstrates scheduling and memory termination; it does not measure CPU throttling.

## Cleanup

```sh
kind delete cluster --name resources-demo --kubeconfig "$KUBECONFIG"
docker image rm resources-web:v1
unset KUBECONFIG
```

The image and manifests passed a real local rehearsal covering the browser response, actual scheduling Events, previous-container logs, repairs and scoped cleanup. Kubernetes resource behavior: <https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/>.
