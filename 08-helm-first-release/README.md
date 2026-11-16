# Install, change and roll back one Helm release

A small chart supplies a Deployment and Service for a local web app. Install it,
change values, inspect a failed rollout and return to an observed good revision.
Tested with Helm **4.3.0** against the pinned local kind node below.

Requirements: Docker, kind, kubectl, Helm 4, editor and browser. This lesson
creates only a disposable local cluster. The provided app needs no cloud account.

## Prepare the image and cluster

Work in this folder:

```sh
helm version --short
export KUBECONFIG="$PWD/lab.kubeconfig"
docker build -t helm-web:v1 .
kind create cluster --name helm-demo --image kindest/node:v1.36.4@sha256:099e049362a1526b2db71494e1947aae99bd16290d7c895f2b7ea312e3cbfaed --wait 120s
kind load docker-image helm-web:v1 --name helm-demo
```

Keep the kubeconfig export in this terminal. Use a fresh cluster name and project
folder; cleanup below removes this named cluster.

## Read the chart before installing it

```text
web-demo/
  Chart.yaml
  values.yaml
  values.schema.json
  templates/
    deployment.yaml
    service.yaml
```

`Chart.yaml` identifies the chart. `values.yaml` supplies its defaults, the schema
checks those inputs, and templates turn the values plus release information into
Kubernetes resources. Read both templates in your editor: release name `hello`
produces resources named `hello-web`, while values supply the image, replicas and
message. The message is injected directly into the Pod template as an environment
variable, so changing it creates a new rollout.

```sh
helm lint ./web-demo
helm template hello ./web-demo --namespace helm101 > rendered.yaml
```

Open `rendered.yaml` and compare the generated names, image and message with the
templates and defaults. Rendering alone hasn't installed a release. This deliberate
invalid input should be rejected by the schema:

```sh
helm lint ./web-demo --set replicaCount=0
```

## Install and open the app

```sh
helm install hello ./web-demo --namespace helm101 --create-namespace --wait --timeout 120s
helm status hello -n helm101 -o json
kubectl get pods,service -n helm101
kubectl port-forward -n helm101 --address 127.0.0.1 service/hello-web 18089:80
```

Open <http://127.0.0.1:18089>. Expect **Hello from Helm**. Keep the forward in a
second terminal if you want the first terminal available for Helm commands.
The clean exercise starts with release revision **1** and one ready replica.

## Upgrade with a values file

Read `values.local.yaml`: two replicas and a changed message.

```sh
helm upgrade hello ./web-demo -n helm101 -f values.local.yaml --wait --timeout 120s
helm get values hello -n helm101 -o json
helm get manifest hello -n helm101
helm history hello -n helm101 -o json
```

Restart the port-forward if its selected Pod was replaced. Reload the page and
expect **Updated through the values file**. Check two replicas are ready.
`get values` shows supplied overrides, while `get manifest` shows the installed
resources. In this clean sequence revision **2** is the successful changed release.

## Reproduce a failed rollout

Read `values.bad-image.yaml`. It selects the intentionally unloaded image tag
`not-loaded`. The chart keeps `imagePullPolicy: Never` for this local image demo.

```sh
helm upgrade hello ./web-demo -n helm101 -f values.bad-image.yaml --wait --timeout 20s
helm status hello -n helm101 -o json
kubectl get pods -n helm101
```

The upgrade should time out and mark the release failed. Select the new failing
Pod's actual name, then describe it:

```sh
kubectl describe pod ACTUAL_POD_NAME -n helm101
helm history hello -n helm101 -o json
```

Expect **ErrImageNeverPull** for that deliberately absent local image. Don't
change registry credentials to fix a tag we deliberately didn't build or load.
The old healthy replicas may keep serving during the failed rolling update;
a failed rollout doesn't necessarily mean the whole app has disappeared.

## Roll back to the observed good revision

Read history and choose the successful revision you checked earlier. For this
fresh sequence it's **2**:

```sh
helm rollback hello 2 -n helm101 --wait --timeout 120s
helm status hello -n helm101 -o json
helm history hello -n helm101 -o json
kubectl get pods -n helm101
```

Rollback creates a new release revision containing the earlier configuration;
it doesn't erase the failed revision from history. Restart the forward if needed
and confirm **Updated through the values file** in the browser again.

## Cleanup

Stop the port-forward with Ctrl+C, then:

```sh
helm uninstall hello -n helm101 --wait --timeout 90s
helm list -n helm101 -o json
kind delete cluster --name helm-demo --kubeconfig lab.kubeconfig
docker image rm helm-web:v1
```

Uninstall removes this release. Cluster deletion removes the remaining disposable
lab cluster. Source, values and rendered YAML remain locally.

## References

- [Charts](https://helm.sh/docs/topics/charts/)
- [Upgrade](https://helm.sh/docs/helm/helm_upgrade/)
- [Rollback](https://helm.sh/docs/helm/helm_rollback/)
