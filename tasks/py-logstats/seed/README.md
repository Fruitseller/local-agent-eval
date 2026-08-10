# logstats

A statistics tool for line-oriented application logs.

**The full specification is in [`TASK.md`](TASK.md).** This file only
describes the layout of the repository.

```
logstats.py          the module and CLI you implement (stub)
tests/               public smoke tests - read-only
samples/app.log      a small example log for manual runs
```

## Running the tests

```sh
python3 -m unittest -v tests.test_logstats
python3 -m unittest -v tests.test_cli
```

Both commands are run from the repository root and use nothing but the
Python standard library (3.9+).

## Trying it by hand

```sh
python3 logstats.py samples/app.log
python3 logstats.py --min-level WARN --json < samples/app.log
```
