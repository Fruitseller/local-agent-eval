# Task: `logrotate-audit` — audit rotated log files against a policy

Implement `logrotate-audit.sh`, a Bash command that checks files below an
offline root against a small log-rotation policy. It is intended for image and
backup audits where running the real `logrotate` daemon is neither safe nor
possible.

Bash 4+, standard Unix tools available on Linux (`stat`, `sort`, `mktemp`). No
network and no third-party programs. `tests/` is read-only and restored before
scoring.

## 1. Command line

```text
./logrotate-audit.sh [--root DIR] [--now EPOCH] POLICY
```

* `POLICY` is required and `-` means stdin.
* `--root DIR` maps every absolute policy path below `DIR`; default is `/`.
  For example `/var/log/app.log` with `--root /tmp/image` inspects
  `/tmp/image/var/log/app.log`.
* `--now EPOCH` fixes the current Unix time used for age checks. Without it,
  use the current Unix time. It must be a non-negative decimal integer.
* `--help` prints a short usage message to stdout and exits `0`.
* Unknown options, missing values, extra arguments, an unreadable policy or
  invalid policy data are errors.

Do not follow symlinks. `--root` itself must name an existing directory.

## 2. Policy format

Each non-blank, non-comment line contains exactly five whitespace-separated
fields:

```text
ABSOLUTE_PATH  MAX_BYTES  MAX_AGE_DAYS  OWNER  MODE
```

Leading/trailing whitespace is ignored. A comment begins only when the first
non-whitespace character is `#`; inline comments are not supported.

* `ABSOLUTE_PATH` starts with `/`, contains no whitespace, no `..` path
  component and is unique in the file. Globs are not expanded.
* `MAX_BYTES` and `MAX_AGE_DAYS` are non-negative decimal integers.
* `OWNER` is either `user` or `user:group`, using non-empty names made from
  letters, digits, `_`, `-` and `.`.
* `MODE` is exactly three or four octal digits. Comparison ignores leading
  zeroes, so `0640` and the `stat` result `640` match.

Invalid input is reported with its policy line number.

## 3. Checks and output

Process policy entries in file order. A missing path produces one `MISSING`
record. A symlink produces one `SYMLINK` record. Any other non-regular object
produces one `TYPE` record. No further checks are made for those entries.

For regular files, emit every applicable violation in this fixed order:

1. `SIZE` when actual bytes are greater than `MAX_BYTES`;
2. `AGE` when whole elapsed days are greater than `MAX_AGE_DAYS`;
3. `OWNER` when the owner (or `user:group` when the policy contains `:`)
   differs;
4. `MODE` when the octal mode differs.

Future mtimes have age zero. Output is tab-separated, one violation per line:

```text
PATH<TAB>CHECK<TAB>ACTUAL<TAB>EXPECTED
```

`MISSING`, `SYMLINK` and `TYPE` use `-` for both values. `TYPE` does not need
to identify the concrete object type. Paths in output are the policy paths,
not host paths. There is no header and no diagnostic output on a successful
audit. Examples:

```text
/var/log/app.log	SIZE	1201	1000
/var/log/app.log	MODE	666	0640
/var/log/old.log	MISSING	-	-
```

## 4. Exit status and diagnostics

* `0`: policy valid and no violations (stdout empty);
* `1`: policy valid and at least one violation (records on stdout);
* `2`: command-line, policy or inspection error (stdout empty).

Exit `2` writes a concise message containing `logrotate-audit:` to stderr.
Normal violations never write to stderr. Do not leave temporary files behind.

## 5. Public tests

```sh
bash tests/run.sh
```

Hidden tests exercise the same contract with multiple entries, future mtimes,
owner-with-group policies, symlinks and malformed input. Keep the filename and
CLI exactly as specified.
