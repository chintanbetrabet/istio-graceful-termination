import pytest
import filecmp
from injection import *

class Case():
    def __init__(self,name, expect_sidecar, prestopConfig):
        self.name = name
        self.expect_sidecar = expect_sidecar
        self.prestopConfig = prestopConfig
        self.source = "config/test/%s/inp.yml" % (name)
        self.exp = "config/test/%s/out.yml" % (name)
    def run(self):
        test_out = patch(self.prestopConfig, self.source)
        exp = yaml_parse(self.exp)
        match_exp = len(exp)
        '''
        1. if injection is not needed, check that output does not have istio-proxy
        2. check if all the expected prestops are added
        '''
        found_istio_proxy = False
        for c in test_out["spec"]["template"]["spec"]["containers"]:
            if c["name"] == "istio-proxy":
                found_istio_proxy = True
            if c["name"] in exp:
                match_exp -=1
                if exp[c["name"]].get("exists", True) == True:
                    assert exp[c["name"]]["lifecycle"]["preStop"]["exec"]["command"] == c["lifecycle"]["preStop"]["exec"]["command"]
                else:
                    assert exp[c["name"]].get("lifecycle") is None
        assert found_istio_proxy == self.expect_sidecar, "In %s Sidecar expected: %s, got %s"% (self.name, self.expect_sidecar,found_istio_proxy)
        assert match_exp == 0, "match missed in %s" % self.name

def run_tests():
    config = "config/pre_stop.conf.yml"
    yaml_parse(config)
    cases = [
        Case("tcp", True, "config/pre_stop.conf.yml"),
        Case("http", True, "config/pre_stop.conf.yml"),
        Case("sidecar_disabled", False, "config/pre_stop.conf.yml"),
        Case("not_in_conf", False, "config/pre_stop.conf.yml"),
        Case("invalid_type", False, "config/pre_stop.conf.yml"),
        Case("no_annotation", False, "config/pre_stop.conf.yml"),
    ]
    for c in cases:
        c.run()
run_tests()
    
    