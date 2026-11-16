# Kubernetes Jobs and CronJobs

Run a bounded totals task once, diagnose bad input, then run the same task manually and on a real CronJob schedule. The task reads `12,18,30` and records three items with a sum of 60 in its logs.

Requires Docker, kind and kubectl. Work from this folder with unused lab names. All resources stay in a disposable local cluster; no cloud account is needed.

## Prepare the image and cluster

```sh
export KUBECONFIG="$PWD/lab.kubeconfig"
docker build -t totals-job:v1 .
kind create cluster --name jobs-demo --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed --wait 120s
kind load docker-image totals-job:v1 --name jobs-demo
kubectl create namespace jobs101
```

## Run one Job

Read `task.py` and `job.yaml` in your editor, then run:

```sh
kubectl apply -f job.yaml
kubectl wait --for=condition=complete job/totals-once -n jobs101 --timeout=90s
kubectl logs job/totals-once -n jobs101
```

Expect JSON with `"items": 3` and `"sum": 60`. A Job is intended to finish; this task does not need a Service or a browser endpoint. The Pod uses `restartPolicy: Never`, and the Job has `backoffLimit: 2`, a 60-second active deadline and a 300-second finished-Job TTL.

## Diagnose a bounded failure

```sh
kubectl apply -f job-failing.yaml
kubectl wait --for=condition=failed job/totals-bad-input -n jobs101 --timeout=100s
```

Read the failed task's Pod logs using its actual Pod name. The input `12,bad,30` causes a Python `ValueError`. This non-indexed example stops retrying within its retry/deadline limits; do not treat repeated attempts as separate successful runs.

Open `job-failing.yaml`, change the input to `12,18,30`, save, then apply that same file again:

```sh
kubectl apply -f job-failing.yaml
```

The attempted change to this existing Job's Pod template should be rejected as immutable. Use the provided new Job, with a different name, for the repaired run:

```sh
kubectl apply -f job-repaired.yaml
kubectl wait --for=condition=complete job/totals-repaired -n jobs101 --timeout=90s
kubectl logs job/totals-repaired -n jobs101
```

Expect the successful sum of 60. Keep failed-run evidence while diagnosing; replacing an input file does not edit a completed task's historical logs.

## Test a CronJob while its schedule is suspended

```sh
kubectl apply -f cronjob.yaml
kubectl create job totals-manual --from=cronjob/minute-totals -n jobs101
kubectl wait --for=condition=complete job/totals-manual -n jobs101 --timeout=90s
kubectl logs job/totals-manual -n jobs101
```

The CronJob starts suspended. That stops its scheduler from creating new Jobs; it does not prevent this explicit manual Job. Read the manifest's every-minute schedule, `Etc/UTC` timezone, 30-second starting deadline and `Forbid` concurrency policy. `Forbid` governs Jobs from this CronJob; it does not globally prevent other tasks from running.

## Observe a real scheduled run

```sh
kubectl patch cronjob minute-totals -n jobs101 --type=merge -p '{"spec":{"suspend":false}}'
```

Watch for the controller-created Job at the next eligible minute. Inspect that actual Job's owner reference and `batch.kubernetes.io/cronjob-scheduled-timestamp` annotation; the manually created Job above is not evidence of a scheduled run. Wait for the new Job to complete and read its logs using its observed name.

Suspend the schedule after checking the result:

```sh
kubectl patch cronjob minute-totals -n jobs101 --type=merge -p '{"spec":{"suspend":true}}'
```

In rehearsal, no new Job appeared across the next minute while the existing completed Job remained. Suspension does not terminate existing Jobs. History limits and finished-Job TTL can later remove old runs; the manifests are not an archival logging system. CronJobs are not an exactly-once execution guarantee, so real tasks should handle retries and duplicate work appropriately.

## Cleanup

```sh
kind delete cluster --name jobs-demo --kubeconfig "$KUBECONFIG"
docker image rm totals-job:v1
unset KUBECONFIG
```

Real local rehearsal covered the successful result, failed attempts, immutable-template rejection, repaired Job, manual run, genuine controller-scheduled run, suspension and cleanup. Kubernetes references: [Jobs](https://kubernetes.io/docs/concepts/workloads/controllers/job/) and [CronJobs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/).
