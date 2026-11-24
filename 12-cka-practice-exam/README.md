# CKA 2026 practice exam

Seventeen hands-on tasks on a disposable Kubernetes 1.37 cluster. Covers all five CKA domains. Run through the prompts before opening the solutions. The lab uses local Docker, kind, Cilium and Envoy Gateway. It creates no AWS resources.

## Set up

Use a machine with Docker running, kind 0.33.0, kubectl 1.37, Helm, OpenSSL and curl. Initial setup pulls public images and installs two charts. It creates a three-node cluster named `cka-practice`; allow room for both workers and the control plane. If you use multiple Docker contexts, select the local development daemon before starting.

```bash
bash setup.sh
export KUBECONFIG="$PWD/lab.kubeconfig"
kubectl config current-context
kubectl get nodes
```

Expect context `kind-cka-practice` and three Ready nodes. Some workloads seeded for troubleshooting will be Pending or restarting. The Ingress in task 8 is a source specification for the migration. Envoy Gateway handles the new route. Cilium enforces the policy in task 9.

## Take the mock

Open [exam.md](exam.md), set a two-hour timer and work through the tasks. Use the allowed official docs. Do the API-server outage task last. Its fault script and repair commands operate only on the disposable kind control plane.

Award each task its listed points when you verify the stated outcomes. Keep notes on tasks that worked but took too long. The score is for this mock. For tasks like rollout and storage replacement, note both states before moving on.

## Review

[solve.sh](solve.sh) contains one worked command sequence and checks per task. It makes changes, so use it only from an untouched lab or against the task's original starting state.

```bash
bash solve.sh 2
```

If your lab API is still down after task 17, the original manifest is in `/tmp/cka-apiserver-known-good.yaml` inside `cka-practice-control-plane`. You can copy it back into place on that **lab node** to recover, then verify `kubectl get --raw=/readyz`.

## Clean up

These commands remove the named practice cluster and its data. Check the cluster name before running them.

```bash
kind delete cluster --name cka-practice
rm -f ./lab.kubeconfig
unset KUBECONFIG
```

[CNCF curriculum](https://github.com/cncf/curriculum/tree/main/cka) · [Linux Foundation exam FAQ](https://docs.linuxfoundation.org/tc-docs/certification/faq-cka-ckad-cks) · [Allowed resources](https://docs.linuxfoundation.org/tc-docs/certification/certification-resources-allowed#certified-kubernetes-administrator-cka-and-certified-kubernetes-application-developer-ckad)
