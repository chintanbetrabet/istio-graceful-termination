With Istio all requests routed to a pod are intercepted by the envoy sidecar and then proxied to the container running the HTTP service. In most cases, these services are stateless and its pods can be terminated instantly without any loss of data.
However, we may have use cases where a pod needs to gracefully handle termination such as:
a) Sending notifications to listeners or reporting cause of termination
b) Releasing locks on shared resources in a distributed system
 c) Draining existing requests and sending callbacks on completion
All of these require communication with external services and will be routed via the envoy sidecar proxy. 
These operations can be handled gracefully within the application using:
Trapping Sigterm signals within the container
Overriding terminationGracePeriodSeconds for a pod

However, when we introduce an additional hop through the envoy proxy, these external calls will fail as the envoy container will be terminated once Kubernetes sends a Sigterm signal to the pod. Envoy gracefully handles all the existing requests and allows them to drain but any new request, either ingress or egress will fail with 503 as envoy has been terminated and is unable to handle new requests.
```
Solution:
```
The desired solution is to ensure that the proxy sidecar is not terminated before the main container running the service is terminated. The problem is tricky since sidecar injection is performed by Istio and we do not own the lifecycle of the istio-proxy container. There is however a way to tackle the problem.
Step 1: Disable the automatic injection of sidecars
This is essential as manual injection of sidecars allows us to control the final YAML which will be applied. To perform this, disable automatic sidecar injection at the namespace level:
```
kind: Namespace
apiVersion: v1
metadata: 
  name: foo
  labels:
    sidecar.istio.io/inject: "false"
```
2. Inject the sidecars with the correct lifecycle hooks to prevent abrupt termination


The tool aims to simplify this injection of lifecycle hooks for istio-proxy conatainers. The structure is as follows:
a) injection.py: A simple runnable python file which takes 3 arguments:
1. The source file
2. The config file used for injection
3. The output location (if not specified, it overwrites the input file itself)

b) injection_test.py:
Used to validate if the file covers the scenarios expected. The test cases are listed in config/test folder

c) structure of the config file
```
deployment:
  test-tcp-svc:
      test-tcp-svc: ["/bin/sh", "-c", "/bin/graceful_termination.sh"]
      istio-proxy: [ '/bin/sh', '-c', 'while [ 1==1 ]; do netstat -tulpn | grep LISTEN | grep :20000; if [ $? -gt 0 ]; then  break; fi; sleep 1; done']
  http-svc:
      http-svc: ["/bin/sh", "-c", "/bin/graceful_termination.sh"]
      istio-proxy: [ '/bin/sh', '-c', 'while [ 1==1 ]; do curl localhost:3000/health; if [ $? -gt 0 ]; then  break; fi; sleep 1; done']
```
This allows the user to inject lifecycle hooks for all containers present, including istio-proxy which is not added by the user.
The first level key is the type (deployment, statefulset, daemonset) in lowercase, followed by a map of the resource name and the containers to patch, each specifying the pre stop command.
For examplary purpose, a TCP and an HTTP based main container process is chosen. The idea is that the pre stop condition for istio proxy is that the parent process is terminated. To verify this:
a) For TCP container, we do a check to see if the port is still occupied by main process
b) For HTTP, we hit the health endpoint here but in general you may choose to use any http endpoint exposed.

The core phenomena used here is that ports and processes are accessible across the pod, even from different containers. This allows us to view the state of the main process from the istio-proxy container and wait on the same. In both cases, the chosen script is using bash since we do not wish to rely on any underlying language dependencies or packages (gems, jars etc.).