# Kubernetes 101 — varCodeFather

Kubernetes on a laptop first, then production. Each tutorial has its own folder with manifests, a walkthrough and scoped cleanup.

| Tutorial | Files | Video |
| --- | --- | --- |
| 01 — First cluster with kind: deploy, reach, replace and troubleshoot | [Walkthrough](01-first-cluster/README.md) | [Watch tutorial](https://www.youtube.com/watch?v=6t4tAyD1UxQ) |
| 02 — Fix image pull errors and crashing containers | [Walkthrough](02-fix-broken-deployments/README.md) | Video in production |
| 03 — Build a local image, deploy an update and roll back | [Walkthrough](03-local-image-to-kind/README.md) | Video in production |
| 04 — ConfigMaps and Secrets: change settings without rebuilding | [Walkthrough](04-config-and-secrets/README.md) | Video in production |

```bash
git clone https://github.com/varcodefather/kubernetes101.git
cd kubernetes101/01-first-cluster
```

Read the walkthrough before creating a cluster. It uses a dedicated kubeconfig, one named kind cluster and a namespace for demo resources. Do not commit generated kubeconfig files; they contain cluster credentials.

First-cluster lab tested with kind 0.33.0, Kubernetes node 1.37.0 and kubectl 1.37.1 in a local Linux VM. Checks covered two ready Pods, real HTTP response, Pod replacement, broken-selector diagnosis, repair and cleanup. Docker must be running. No AWS account required.

[YouTube — @varCodeFather](https://www.youtube.com/@varCodeFather)
