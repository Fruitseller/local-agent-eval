PYTHON ?= python3
BASELINE_ID ?= make-test

.PHONY: list check test baseline

list:
	$(PYTHON) harness/run.py --list

check:
	$(PYTHON) -m py_compile harness/*.py tasks/py-semver/seed/*.py tasks/py-semver/seed/tests/*.py tasks/py-logstats/seed/*.py tasks/py-logstats/seed/tests/*.py
	bash -n tasks/sh-logrotate-audit/seed/logrotate-audit.sh tasks/sh-logrotate-audit/seed/tests/run.sh
	cd tasks/go-cronparse/seed && go test -run '^$$' ./...
	cd tasks/go-tablefmt/seed && go test -run '^$$' ./...
	cd tasks/go-tally/seed && go test -run '^$$' ./...
	$(PYTHON) harness/run.py --list

baseline:
	$(PYTHON) harness/run.py --baseline --all --run-id $(BASELINE_ID)

test: check baseline
	$(PYTHON) -c 'import json, pathlib; p=pathlib.Path("results/$(BASELINE_ID)"); s=json.loads((p/"summary.json").read_text()); assert s["totals"]["tasks"] == 6; results=[json.loads(f.read_text()) for f in p.glob("*/result.json")]; assert len(results) == 6; suites=[x for r in results for x in r["suites"]]; assert suites and all(x["exit_code"] is not None and not x["timed_out"] for x in suites); print(f"validated {len(results)} tasks and {len(suites)} runnable public suites")'
