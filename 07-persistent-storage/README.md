# Kubernetes storage: keep data across Pod replacement

Run browser counter with temporary storage, attach persistent claim, replace Pod, diagnose missing claim reference, then export and restore counter value.

Tested locally with kind and pinned Kubernetes 1.36.4 node image. Docker must be running; install kind, kubectl and Neovim first. No AWS resources.

## Start lab

From this lesson folder:

```bash
mkdir -p ~/tutorials/storage
cp -R starter/. ~/tutorials/storage/
cd ~/tutorials/storage
export KUBECONFIG="$PWD/lab.kubeconfig"
kind create cluster --name storage-demo \
  --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed \
  --kubeconfig lab.kubeconfig --wait 180s
kubectl get nodes
docker build -t counter-web:v1 .
kind load docker-image counter-web:v1 --name storage-demo
kubectl create namespace storage101
kubectl apply -f deployment.yaml -f service.yaml
kubectl rollout status deployment/counter -n storage101 --timeout=180s
kubectl get pods -n storage101
```

Use native Docker context if another desktop app changed your default context. The studio uses `DOCKER_CONTEXT=default`; choose your own working Docker backend. No Docker credentials needed for these public images.

In second terminal:

```bash
cd ~/tutorials/storage
export KUBECONFIG="$PWD/lab.kubeconfig"
kubectl port-forward --address 127.0.0.1 -n storage101 service/counter 8080:80
```

Open [counter](http://127.0.0.1:8080) on machine running forward. Click **Add one** twice; note count and Pod name. App saves `/data/counter.json`.

## Replace temporary-storage Pod

Stop second terminal's forward with **Ctrl+C**, then run in first terminal:

```bash
kubectl get pods -n storage101 -l app=counter
kubectl delete pod -n storage101 -l app=counter
kubectl wait --for=condition=Ready pod -n storage101 -l app=counter --timeout=120s
kubectl get pods -n storage101 -l app=counter
```

Reconnect forward and reload page. New Pod starts at zero. `emptyDir` survives container restarts within same Pod, but its lifetime ends with Pod. This test replaces whole Pod.

## Request persistent storage

```bash
kubectl get storageclass
kubectl get storageclass standard -o yaml
nvim pvc.yaml
```

Save following claim:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: counter-data
  namespace: storage101
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard
  resources:
    requests:
      storage: 1Gi
```

```bash
kubectl apply -f pvc.yaml
kubectl get pvc -n storage101
kubectl describe pvc counter-data -n storage101
```

Kind's `standard` class uses `WaitForFirstConsumer`. Pending is expected before consuming Pod exists. Check Events for reason.

Stop forward, open `deployment.yaml`, replace:

```yaml
          emptyDir: {}
```

with:

```yaml
          persistentVolumeClaim:
            claimName: counter-data
```

Keep `name: data` and existing `mountPath: /data`. Save and apply:

```bash
kubectl apply -f deployment.yaml
kubectl rollout status deployment/counter -n storage101 --timeout=180s
kubectl get pods,pvc -n storage101
kubectl get pv
kubectl get pvc counter-data -n storage101 -o wide
```

Claim becomes Bound. Fresh volume starts empty; changing mount does not migrate previous emptyDir data. Reconnect forward, reload browser and click twice.

`ReadWriteOnce` allows read-write mounting by one node; it does not enforce one application writer. This demo uses one replica with Recreate strategy. Requested capacity is not guaranteed directory quota for every local provisioner.

## Repeat replacement with claim retained

Stop forward, repeat Pod replacement commands, reconnect and reload. Pod name changes; count remains two. Claim stays bound to same volume.

Do not delete claim during this test. Claim deletion can remove backing storage according to PV reclaim policy. Kind's local storage remains inside node; deleting kind cluster is outside protection shown by this test.

## Diagnose missing claim

Stop forward. In saved Deployment, temporarily change `claimName: counter-data` to `claimName: couter-data`.

```bash
kubectl apply -f deployment.yaml
kubectl get pods,pvc -n storage101
```

Describe **actual Pending Pod name** from table:

```bash
kubectl describe pod YOUR_PENDING_POD_NAME -n storage101
```

Scheduling Events identify missing `couter-data`. Existing `counter-data` remains Bound. Correct Deployment reference to `counter-data`, save, apply and wait:

```bash
kubectl apply -f deployment.yaml
kubectl rollout status deployment/counter -n storage101 --timeout=180s
kubectl get pods,pvc -n storage101
```

Reconnect forward and reload browser. Count remains two. Do not create fresh empty claim to satisfy typo or delete existing data to clear Pending status.

## Export and restore app value

In first terminal:

```bash
kubectl exec -n storage101 deployment/counter -- python /app/backup.py > counter-backup.json
cat counter-backup.json
nvim counter-backup.json
```

Export should contain `{"count": 2}`. Quit editor without changing file. Shell redirection writes export onto your laptop, outside kind cluster.

In browser, click once so live count becomes three. Restore saved value:

```bash
kubectl exec -i -n storage101 deployment/counter -- python /app/restore.py < counter-backup.json
```

Reload browser and confirm two. This is app-specific logical export/restore, **not generic database backup recipe**. Databases need supported backup tools and consistency handling.

## Cleanup

Stop forward first. Following command deletes disposable cluster **and its node-local storage**. Local export and source files remain.

```bash
kind delete cluster --name storage-demo --kubeconfig lab.kubeconfig
kind get clusters
docker image rm counter-web:v1
```

Keep `lab.kubeconfig` private. Demo app has no authentication and belongs only in disposable local lab.

## References

- [Persistent volumes and claims](https://kubernetes.io/docs/concepts/storage/persistent-volumes/)
- [emptyDir](https://kubernetes.io/docs/concepts/storage/volumes/#emptydir)
- [Storage classes](https://kubernetes.io/docs/concepts/storage/storage-classes/)
- [kind image loading](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster)
