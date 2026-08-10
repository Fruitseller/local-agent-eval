#!/usr/bin/env bash
# Public smoke tests for logrotate-audit.sh.
# Read-only: the benchmark restores this directory before scoring.

set -u

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PROGRAM=$ROOT_DIR/logrotate-audit.sh
TESTS=0
FAILURES=0
TMP_DIR=$(mktemp -d)
trap 'rm -rf -- "$TMP_DIR"' EXIT

pass() {
    TESTS=$((TESTS + 1))
}

fail() {
    TESTS=$((TESTS + 1))
    FAILURES=$((FAILURES + 1))
    printf 'not ok %d - %s\n' "$TESTS" "$1" >&2
}

assert_run() {
    name=$1
    expected_code=$2
    expected_stdout=$3
    shift 3

    stdout_file=$TMP_DIR/stdout
    stderr_file=$TMP_DIR/stderr
    "$@" >"$stdout_file" 2>"$stderr_file"
    code=$?
    stdout=$(cat "$stdout_file")
    stderr=$(cat "$stderr_file")

    if [ "$code" -ne "$expected_code" ]; then
        fail "$name (exit $code, expected $expected_code; stderr: $stderr)"
    elif [ "$stdout" != "$expected_stdout" ]; then
        fail "$name (stdout mismatch: $stdout)"
    else
        pass
    fi
}

IMAGE=$TMP_DIR/image
mkdir -p "$IMAGE/var/log"
printf 'short\n' >"$IMAGE/var/log/good.log"
chmod 640 "$IMAGE/var/log/good.log"
touch -d @1900000000 "$IMAGE/var/log/good.log"
USER_NAME=$(stat -c %U "$IMAGE/var/log/good.log")

POLICY_OK=$TMP_DIR/ok.policy
printf '/var/log/good.log 100 2 %s 0640\n' "$USER_NAME" >"$POLICY_OK"
assert_run 'compliant file' 0 '' "$PROGRAM" --root "$IMAGE" --now 1900086400 "$POLICY_OK"

printf '0123456789' >"$IMAGE/var/log/bad.log"
chmod 666 "$IMAGE/var/log/bad.log"
touch -d @1899827200 "$IMAGE/var/log/bad.log"
POLICY_BAD=$TMP_DIR/bad.policy
printf '/var/log/bad.log 5 1 %s 0640\n/var/log/missing.log 50 1 %s 0600\n' "$USER_NAME" "$USER_NAME" >"$POLICY_BAD"
EXPECTED=$(printf '/var/log/bad.log\tSIZE\t10\t5\n/var/log/bad.log\tAGE\t3\t1\n/var/log/bad.log\tMODE\t666\t0640\n/var/log/missing.log\tMISSING\t-\t-')
assert_run 'reports ordered violations' 1 "$EXPECTED" "$PROGRAM" --root "$IMAGE" --now 1900086400 "$POLICY_BAD"

POLICY_INVALID=$TMP_DIR/invalid.policy
printf 'relative.log 10 1 root 0640\n' >"$POLICY_INVALID"
stdout_file=$TMP_DIR/invalid.stdout
stderr_file=$TMP_DIR/invalid.stderr
"$PROGRAM" --root "$IMAGE" "$POLICY_INVALID" >"$stdout_file" 2>"$stderr_file"
code=$?
if [ "$code" -eq 2 ] && [ ! -s "$stdout_file" ] && grep -q 'logrotate-audit:' "$stderr_file"; then
    pass
else
    fail 'invalid policy is a diagnostic error'
fi

if [ "$FAILURES" -ne 0 ]; then
    printf '%d of %d public tests failed\n' "$FAILURES" "$TESTS" >&2
    exit 1
fi
printf 'ok - %d public tests passed\n' "$TESTS"
