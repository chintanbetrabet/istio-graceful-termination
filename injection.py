import yaml
import sys

def is_sidecar_injectable_type(type):
    return type.lower() in ["deployment", "statefulset", "daemonset"]
    

def yaml_parse(file):
    with open(file, 'r') as stream:
        try:
            return yaml.safe_load(stream)
            
        except yaml.YAMLError as exc:
            print(exc)
            
def should_run_istio_patch(yaml_data):
    if is_sidecar_injectable_type(yaml_data.get("kind")):
        return yaml_data.get("spec").get("template").get("metadata").get("annotations").get("sidecar.istio.io/inject") == "true"
    return False
        

def patch(confFile, userFile): 
    conf = yaml_parse(confFile)
    target = yaml_parse(userFile)
    type = target["kind"]
    name = target["metadata"]["name"]
    namespace = target["metadata"].get("namespace") or "default"
    if not should_run_istio_patch(target) or (type not in conf) or (name not in conf[type]):
        return target
    
    loop = target["spec"]["template"]["spec"]["containers"]
    i = 0
    for container in loop:
        if container["name"] in conf[type][name]:
            prestop_patch = { "preStop": {  "exec": { "command": conf[type][name][container["name"]] }  } }
            target["spec"]["template"]["spec"]["containers"][i]["lifecycle"] = prestop_patch
        i+=1
    return target

def main():
    source = sys.argv[1]
    config = sys.argv[2]
    output = sys.argv[3]
    f = open(output, "w")
    f.write(patch(config, source))
