import yaml

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
    if not should_run_istio_patch(target):
        return yaml.dump(target)
    
    loop = target["spec"]["template"]["spec"]["containers"]
    i = 0
    for container in loop:
        print container["name"]
        if container["name"] in conf[type][name]:
            print("YO")
            prestop_patch = { "preStop": {  "exec": { "command": conf[type][name][container["name"]] }  } }
            target["spec"]["template"]["spec"]["containers"][i]["lifecycle"] = prestop_patch
        else:
            print(container["name"]+ "NOT"+ str(conf[type][name]))
        i+=1
    return yaml.dump(target)

source = sys.argv[1]
config = sys.argv[2]
output = sys.argv[3]
f = open(output, "w")
f.write(patch("config/pre_stop.conf.yml", "config/http-svc.yml"))