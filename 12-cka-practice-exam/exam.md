# CKA 2026 practice exam

Set a two-hour timer once setup finishes. Work in the isolated `kind-cka-practice` context. Use the Kubernetes, Helm and Gateway API documentation while practising. Each prompt states the end state. Check it after your changes.

This original mock has 17 tasks covering all five published domains. Complete task 8 before task 9 to establish independent checks. Run task 17 last, since it deliberately makes the lab API unavailable. The local grading weights mirror the public blueprint.

## Cluster architecture, installation and configuration · 25

1. **Check control plane health · 5.** On `cka-practice-control-plane`, use kubeadm to find the expiry date of the API server certificate. Verify the API server readiness endpoint from your workstation.
2. **Grant scoped access · 7.** In `cka-lab`, ServiceAccount `reporter` may get ConfigMap `cluster-notes`. It must be unable to get `spare-notes`, list ConfigMaps, or edit the allowed ConfigMap. Prove the permissions with authorization checks.
3. **Render then install a chart · 7.** Render the bundled `charts/status` Helm chart for release `status` in `cka-lab`, with `site=perth`. Save the rendered YAML as `status-rendered.yaml`. Install the release and verify the live ConfigMap records `perth`.
4. **Apply a Kustomize overlay · 6.** Use `customize/exam` to deploy ConfigMap `lab-mode` in namespace `cka-lab` with `MODE=exam`. Preserve the base default.

## Workloads and scheduling · 15

5. **Roll out and roll back · 5.** On Deployment `web` in `cka-lab`, set the `RELEASE` environment variable to `trial`. Wait for rollout and record its revision. Roll back and verify the live Deployment returns to `RELEASE=base`.
6. **Read a file from a sidecar · 5.** Create `log-reader` from `sidecar-base.yaml` in `cka-lab`. Add a container called `reader` from `busybox:1.37.0`. Mount the existing `logs` volume under `/logs` and follow `worker.log` from the reader. Its logs must contain `cka-log-ready`.
7. **Configure an autoscaler · 5.** Create an HPA for Deployment `web` in `cka-lab` with 2–4 replicas and a CPU utilization target of 65%. Verify the resource's settings. Metrics Server is outside this lab, so this task checks configuration.

## Services and networking · 20

8. **Move an Ingress rule to Gateway API · 8.** Read the existing `legacy-ingress` rule in `cka-lab`. Create HTTPRoute `practice-route` on `practice-gateway` with the same hostname and backend. Verify attachment and fetch `CKA practice web` through the actual Gateway.
9. **Allow only one client · 7.** Protect the independent `policy-web` Deployment in `cka-lab`. Permit TCP 80 from Pods in the same namespace labelled `access=allowed`. The `client` Pod must succeed and `probe/outsider` must fail. Leave `web-http` working.
10. **Resolve a Service across namespaces · 5.** From `probe/outsider`, resolve `web-http` using its full in-cluster DNS name and fetch the page over HTTP. Show the name and returned content.

## Storage · 10

11. **Bind to an existing volume · 5.** Create PVC `archive-data` in `cka-lab`. Bind it to the existing `archive-pv`, request 64 MiB, use `ReadWriteOnce` and use no storage class. Verify it binds to the requested PV.
12. **Keep data across Pod replacement · 5.** Use `writer.yaml` and the existing `scratch-data` claim. Write `checkpoint-42` to `/data/checkpoint`, replace Pod `writer`, and retrieve that value. Verify the new Pod uses the same bound claim.

## Troubleshooting · 30

13. **Restore a Service's endpoints · 5.** Service `legacy-web` has no backends in `cka-lab`. Restore connectivity to Deployment `web` without changing its labels. Verify ready endpoints and a response from `client`.
14. **Fix an application crash · 5.** Deployment `broken-worker` keeps restarting. Diagnose it with logs and provide `GREETING=ready`. Verify the rollout and the new log message.
15. **Make a Pending workload schedulable · 5.** Deployment `oversized` stays Pending because of one request. Set container `worker`'s CPU request to `100m`, preserving its other requests. Verify the resulting Pod is Ready.
16. **Restore TLS client compatibility · 5.** Deployment `compat-web` serves HTTPS from ConfigMap `compat-config`. Investigate why a TLS 1.2 client fails. Change the configuration to allow TLS 1.2 and 1.3 and roll the Deployment. Verify both protocols with the lab certificate.
17. **Restore the API server · 10.** Run `bash break-control-plane.sh` from the lab folder. Inspect the failed API server on the kind control-plane node using the container runtime. Find the etcd client endpoint from the etcd manifest and repair the API server manifest. Verify `/readyz` and that `cka-lab/web` can be read again.
