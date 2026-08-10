# Benchmark task

You are working in a git repository that contains a single, self-contained
coding task. Your job is to complete that task.

## Where the specification is

Read `TASK.md` in the repository root first. It is the authoritative
specification: it defines the required behaviour, the exact output formats and
the acceptance criteria. When this prompt and `TASK.md` disagree, `TASK.md`
wins.

## Rules

1. **Work only inside this repository.** Do not touch files outside the
   working directory.
2. **Do not modify the test files.** Everything under the test directory named
   in `TASK.md` is read-only for you. The benchmark restores those files from
   the pristine seed before scoring, so edits there are wasted work and are
   recorded as a violation.
3. **Standard library only.** Do not add third-party dependencies, do not run
   package managers, and do not access the network. The grading environment is
   offline.
4. **Keep the public interfaces** (module, package, function, flag and file
   names) exactly as specified. They are called directly by the graders.
5. **Do not delete or weaken existing behaviour** that already works.

## How you are graded

* A set of public test suites ships with the repository. Run them yourself and
  make them pass — that is your primary objective.
* A second set of hidden tests, which you cannot see, checks the same
  specification on additional edge cases. Implement what `TASK.md` says, not
  only what the visible tests happen to assert. Special-casing the visible
  test inputs scores badly.

## How to work

* Start by reading `TASK.md` and the existing source files.
* Run the test command shown in `TASK.md` early to see the starting state, and
  again after your changes.
* You have a limited wall-clock budget. Prefer a correct, complete
  implementation of the whole specification over a perfect implementation of
  one part.
* Finish by leaving the repository in a working state. Do not commit; the
  harness records your working tree.

When you are done, reply with a short summary of what you changed.
