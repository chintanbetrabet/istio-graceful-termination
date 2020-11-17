import pytest
import filecmp
from injection import *

def input_files():
    for test in ["tcp", "sidecar_disabled", "http", "invalid_type", "not_in_conf", "invalid_type"]:
        source = "config/test/%s/inp.yml" % (test)
        exp = "config/test/%s/out.yml" % (test)
        
        config = "config/pre_stop.conf.yml"
        output = "config/test/test.yml"
        test_out = patch(config, source)
        statement = "%s case failed" % (test)
        assert yaml_parse(exp) == test_out, statement
input_files()
    
    