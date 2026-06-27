# calpha engine

A from-scratch flow engine that **owns its runtime** instead of compiling to
LangGraph. Designed from a study of graphon's `graph_engine`
(`docs/graphon-study.md`), trimmed to calpha's deterministic-workflow needs.
This is now *the* engine, and flows are authored as **Compose-shaped YAML** read
by the `compose/` loader (the legacy `FlowSpec`/`IOField` authoring contract and
the `manifest` layer were retired in the v0 cutover).

## The vision: a functional language for data transformation

The engine is, at heart, a **small functional programming language** — one whose
leaf computations may be LLM agents. If you know OCaml, you already know the
shape of it:

- A **flow is a function**: typed inputs in, typed outputs out, and nothing
  hidden. An **agent is just a flow** whose leaf computation happens to be an LLM
  loop — same contract, same composability.
- Flows **compose**. A node can *be* another flow, so you build a big
  transformation out of small ones, nested to any depth — function composition,
  not a monolith.
- Computation is **pure at the boundary**: a node *returns* its outputs and the
  engine *binds* them; a node never reaches in and mutates shared state. Outputs
  are immutable, typed, losslessly serializable values.
- The **program's structure is fixed by the author**, the way a function's call
  graph is fixed by its source. The LLM fills leaf boxes; it does **not** rewrite
  the graph at runtime. That referential transparency is what makes runs
  reproducible, checkpointable, and resumable.

So the goal when extending the engine is not "add a feature to a workflow tool" —
it's "add a construct to a language," and the bar is the same as a language's:
does it have a clear type, does it compose, is it pure where it should be?

### Concept map (OCaml ↔ engine)

| Functional programming (OCaml)                  | Calpha engine                                                                 |
|-------------------------------------------------|-------------------------------------------------------------------------------|
| A function `'a -> 'b`                           | A **flow** — typed inputs → typed outputs (an agent is one kind of flow)       |
| The function body                               | the flow's nodes (its graph)                                                   |
| A value — immutable, typed                      | a `Segment` in the `TypedVariablePool`                                         |
| `let x = e in …`                                | a node output bound once under `(node_id, key)`, read via `${x.output.output.k}` |
| A pure function (referentially transparent)     | a node **returns** outputs; the engine binds them — a node never mutates state |
| Function application (`f x`)                    | `CALL` (`kind: call`): a node *is* another flow, seeded once from the caller's bindings, nesting freely |
| `List.map f xs`                                 | `MAP` (`kind: map` + `over:`): apply a child flow per element of the `over:` list (`${item}`), collecting `list[U]` |
| `if … then … else` (an expression)             | `IF_ELSE` — a pure `when:` expression over the pool                            |
| Pattern match selecting a branch                | branch selection; the recursive skip-flood prunes the untaken branch           |
| Algebraic effects + handlers (OCaml 5)          | **suspend/resume**: `HUMAN_INPUT`/`WAIT` *perform* a pause-effect; an external scheduler is the *handler* that resumes with a value |
| The type system                                 | the `Segment` / `SegmentType` value system (lossless JSON round-trip)          |
| A program = functions composed at author time   | a flow = nodes composed by the human; the LLM only fills leaf boxes            |

## Why own the runtime

A language needs a runtime that honors its semantics. Owning ours buys three
things LangGraph made hard:

1. **Real parallel execution** — a fixed worker pool with a single-writer
   dispatcher (independent branches overlap), while keeping binding pure.
2. **Typed, losslessly-serializable state** — the value system above, and the
   basis for durable checkpoints and structured references
   (`${x.output.output.ratio}`).
3. **Durable suspend/resume** — the effect/handler model: a node can pause (await
   a person or an external event), the run serializes to a checkpoint, and an
   external scheduler resumes it later, in any process.

## Layout

```
spec/         shared values: LLMConfig + START/END ids (the __start__/__end__
              sentinels retired in Phase 2.5 → boundary node kinds)              [leaf]
state/        typed value system (segments) + variable pool              [leaf, no deps]
events.py     run + node event vocabulary
nodes/        Node contract (base) + per-kind implementations
compile/      compiled IR (CompiledFlow) + representation-neutral validation checkers
compose/      the Compose-YAML loader: text -> CompiledFlow (parser/shapes/build/
              cases/validate/asserts/loader/run)
expr/         ${...} resolution + when: evaluator on the typed pool
runtime/      state_manager, single-threaded engine, parallel worker pool
suspension/   pause reasons, commands, checkpoint
```

Import direction (acyclic): `events <- state <- nodes <- compile <- compose`,
with `compile`/`state`/`nodes`/`expr` feeding `compose` (the front-end that reads
YAML into the IR), `expr` feeding nodes, and `suspension` feeding runtime.
(Package layout conventions — charters, `common.py`/`utils.py`, import direction —
live in the `structure` skill.)

## What runs today

- **Typed state** — `Segment`/`SegmentType` (scalars, lists, object, reserved
  `FILE` placeholder), `TypedVariablePool` with write-time type-drift detection
  and lossless JSON round-trip.
- **Execution** — single-threaded inline drain *and* a fixed parallel worker
  pool, both with: 3-state edge join (exact-once diamond fan-in),
  outputs-before-successors, IF_ELSE branch + recursive skip-flood, failure,
  cooperative abort.
- **Durable suspend/resume** — `RunCheckpoint` (pool + node/edge state + paused/
  deferred + typed pause reasons), `snapshot()` / `restore()` / `resume()`,
  `DeliverAnswerCommand` delivery (deliver-as-Output on the parked leaf).
- **Loading** — `load_flow(yaml) -> LoadedFlow` (a `CompiledFlow` + input decls +
  asserts) and `run_flow(loaded, inputs) -> RunResult`, running a real branching
  Compose flow end-to-end.
- **Node kinds** — `IF_ELSE` (when: expression), `TOOL`
  (TOOL_REGISTRY), `CODE` (`module:function`), and the effect kinds `HUMAN_INPUT`
  (suspend for a person; the typed answer is the node's output) and `WAIT` (timed
  `until:` → `ScheduledPause`, command-driven release). Both became **authorable in
  Compose YAML** in feature E (`compose/` parser + build arms).
- **Host resume seam** — `run_flow` returns the engine + checkpoint + pause reasons
  when a run suspends, and `resume_flow(loaded, *, engine|checkpoint, commands)` drives
  a suspended run to its next terminal (in-process + multi-pause).
- **External callables — `uses:` (feature F)** — a top-level `uses:` block binds an
  external flow to a local alias (Python-import style); a node `call:`s the alias
  (defs-first → `uses:` alias → host). The injected `child_resolver` is the whole
  surface; the default local file resolver (`make_file_resolver`) resolves a ref on a
  `sys.path`-style search path rooted at the importing file's dir (extended by its
  `system: paths:`), re-rooting per child, with cross-file cycle detection (L4). A `hub:`
  scheme is reserved for a future marketplace (deferred). `load_flow(text,
  search_paths=[dir])` opts in; with neither `search_paths` nor `child_resolver`,
  behavior is unchanged (a non-def `call:` is loud).

Run the tests:

```bash
python -m pytest tests/engine -q
```

## Roadmap (remaining)

- **More agent modes / tools** — an AGENT node has three knobs: **mode**
  (`AgentBody.mode`, the loop — `plain` = single call, `tool_calling` = loop;
  registered in `MODES`, in `nodes/agent/modes/`), **tools** (`AgentBody.tools`,
  ordinary *tools* from `calpha/tools/`, e.g. `web_search`), and **controls**
  (`AgentBody.controls`, *control tools* from `nodes/agent/controls/`, e.g.
  `ask_user`, which suspends the loop via `PauseRequested` and resumes with the
  user's answer — `tool_calling` memoizes its conversation in the pool so resume
  replays). `ask_user` is **model-chosen** — the agent asks only when it decides it
  needs to (non-deterministic); for a deterministic gate that *always* pauses at a
  fixed point, use the `HUMAN_INPUT` node instead. The single `AgentNode` builds
  its own model via `model_from_config`; a
  mode talks to langchain directly — no injected client seam. Add a `react` mode;
  add token streaming as a mode that yields `StreamChunk`.
- **Contract extension** — `HUMAN_INPUT` / `WAIT` are now authorable in Compose YAML
  (feature E); `WATCH` still needs a `compose/` parser arm. Input-binding
  semantics for CODE/TOOL/AGENT (the explicit typed input signature — the
  function's parameter list).
- **WATCH** — a predefined composite flow (TOOL + IF_ELSE + WAIT + loop),
  run via `ref` and shown as one collapsed node; needs cyclic-graph validation +
  engine-level re-enqueue.
- **Durable transport** — Redis or Mongo-collection impls of the ready-queue +
  command-channel, injected from `server/`; the watcher/scheduler that pokes
  suspended runs. Parallel `snapshot()` of the live ready-queue.
- **Error strategies** — retry / fail-branch / default-value (engine-side seam).
```

