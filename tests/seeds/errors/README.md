# Seed gallery — NEGATIVE examples (expected failures)

These flows are **supposed to fail** — most at load/compile, some loudly at runtime. They pin
the *error* behavior of the Compose loader + runtime — Agent Compose **L3: "failures are loud and
located"** — and double as the loader's negative test fixtures
(`tests/engine/test_errors.py`). Each file's header states the expected diagnostic **and
whether it fails at compile or runtime**, and isolates exactly **one** failure (everything
else in the file is valid).

## The rule — every feature gets negative fixtures

**For each seed / engine feature in the gallery, add error fixtures here that capture its
expected failure modes — both compile-time and runtime — that the engine can actually
detect.** Concretely:

- **Compile-time** failures load via `load_flow` and must raise `LoadError`; where the slice
  tracks a position, assert the located `.line` (the offending `.yaml` line, not the IR).
- **Runtime** failures run via `run_flow` and must come back as `RunResult.status == "failed"`
  (or `"aborted"`) with a `.error` substring — never an uncaught crash.
- Each fixture isolates **one** failure, states compile-vs-runtime + the expected diagnostic in
  its header, and gets a matching assertion in `tests/engine/test_errors.py`.
- A failure mode whose check isn't built yet goes under `_future/errors/` with its milestone —
  never assert an error the engine can't yet capture.

A negative gallery is half the value of a type system: it pins what *can't* be written, not
just what can.

## Compile failures (fail at load, regardless of inputs)

| File | Should fail with | Pins |
|---|---|---|
| `e01-undeclared-ref.yaml` | unknown reference `${<typo>.output}` — no such node | L3 reference check |
| `e02-cycle.yaml` | the inferred graph has a cycle (not a DAG) | L4 / C4 edge inference |
| `e03-unknown-field.yaml` | dotted access into a record field that doesn't exist | L3 / C3 type-walk |
| `e06-type-mismatch-ref.yaml` | a `float` bound to a REF child input declared `str` | L3 / C10 cross-flow signature check |
| `e09-unknown-top-level-key.yaml` | an unknown top-level section key (`extra='forbid'`) | strict schema (D-C1) |
| `e10-unknown-node-kind.yaml` | a node `kind:` outside the closed set | closed `NodeKind` |
| `e11-field-not-allowed.yaml` | a flat field illegal for the kind (`prompt` on a `code`) | per-kind body shape |
| `e12-missing-required-field.yaml` | a kind-required field omitted (`code` w/o `code:`) | per-kind body shape |
| `e13-bad-type-expression.yaml` | a malformed type expression (`outputs: list[`) | the `ast` type parser |
| `e14-unknown-system-ambient.yaml` | `${system.bogus}` — only `today`/`now`/`run_id` are valid | strict `system` ambients |
| `e15-prompt-undeclared-input.yaml` | an AGENT prompt references a non-declared input | prompt-L1 |
| `e16-bad-typedef-name.yaml` | a `typedefs:` name shadows a typing constructor | `read_typedefs` rules |
| `e17-case-nonexhaustive.yaml` | a `case … on` enum leaves a tag uncovered, no `else:` | exhaustiveness check |

## Runtime failures (fail during the run; the header states the triggering inputs)

| File | Should fail with | Pins |
|---|---|---|
| `e18-false-boundary-assert.yaml` | a false `${inputs}`-only assert (run `window: -5`) | boundary asserts (F-C5) |
| `e19-false-post-assert.yaml` | a false `${X.output}` assert flips success → failed | post-terminal asserts |
| `e20-code-raises.yaml` | a CODE callable that raises → the run fails | node-failure → `RunFailed` |
| `e21-code-wrong-type.yaml` | a CODE node returns the wrong type for its `outputs:` | typed write boundary |
| `e22-required-missing.yaml` | `${x:?msg}` on an omitted value (run with it omitted) | `:?` use-site required |
| `e23-unknown-tool.yaml` | a TOOL node naming an unregistered `tool_id` | TOOL registry lookup |
| `e08-input-type-mismatch.yaml` | a non-coercible input value for a declared type (run `window: "soon"`) | typed read boundary (mirror of e21) |

## Deferred (`_future/errors/`, until the check lands)

_None._ (`e08` landed — typed input boundary; `e04`/`e05` were dropped with the
`kind: match` + payload-union design — tagged data is a discriminant record routed by
`case … on <field>`.)

(`e07-required-missing.yaml` — `:?` at an AGENT use-site — is now LIVE (M9.2 C): binding runs
before the model is built, so the omitted-required ref fails the run with no LLM creds. The CODE
form ships as `e22`.)
