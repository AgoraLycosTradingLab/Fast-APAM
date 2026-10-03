"""Fresh-process engine execution isolates module-level date contexts."""
import importlib
import json
import sys
from pathlib import Path

STAGES=['operating_company_factor_inputs_v2','operating_company_normalization','operating_company_factor_scores','operating_company_persistence_research','operating_company_independent_review','operating_company_research_pilot']


def main():
    root=Path(sys.argv[1])
    completed=[]
    for name in STAGES:
        importlib.import_module('fast_apam.engine.'+name).run(root,root)
        completed.append(name)
    (root/'execution.json').write_text(json.dumps({'completed_stages':completed,'status':'COMPLETE'}))


if __name__=='__main__':main()
