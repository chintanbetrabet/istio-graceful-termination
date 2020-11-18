#!/usr/bin/python
import yaml
import sys
import os
import re
import datetime

def is_sidecar_injectable_type(type):
    return type.lower() in ["deployment", "statefulset", "daemonset"]

def yaml_parse(file):
    with open(file, 'r') as stream:
        try:
            for f in yaml.load_all(stream):
                return f
            
        except yaml.YAMLError as exc:
            print(exc)

def getFromNestedMap(map, *args):
    for arg in args:
        if arg in map:
            map = map.get(arg)
        else:
            return None
    return map

def should_run_istio_patch(yaml_data):
    if is_sidecar_injectable_type(yaml_data.get("kind")):
        return getFromNestedMap(yaml_data, "spec", "template", "metadata", "annotations", "sidecar.istio.io/inject") == "true"
    return False
        
def kube_injected_output(userFile):
    source = yaml_parse(userFile)
    if should_run_istio_patch(source):
        tempfile_prefix = str(datetime.datetime.now()).replace(".","-").replace(" ", "")
        tempfile_name = tempfile_prefix + ".yml"
        cmd = "istioctl kube-inject -f %s > %s" % (userFile, tempfile_name)
        os.system(cmd)
        target = yaml_parse(tempfile_name)
        os.remove(tempfile_name)
        return target
    return source

def patch(confFile, userFile): 
    conf = yaml_parse(confFile)
    source = yaml_parse(userFile)
    type = source["kind"].lower()
    name = source["metadata"]["name"]
    if (type not in conf) or (name not in conf[type]):
        return source
    target = kube_injected_output(userFile)
    namespace = target["metadata"].get("namespace") or "default"
    
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
    output = source
    if len(sys.argv) >= 3:
        output = sys.argv[3]
    output_data = patch(config, source)
    f = open(output, "w")
    f.write(output_data)
