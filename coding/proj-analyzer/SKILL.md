---
name: proj-analyzer
description: "Deep-read a whole repository from source and produce a single self-contained PROJECT-ANALYSIS.html that works offline as an architecture explorer, codebase map, API explorer and onboarding guide. Use this whenever someone needs to understand, hand over, onboard onto, audit, map, or document an unfamiliar or large codebase — including phrasings like \"分析这个项目\", \"生成项目分析报告\", \"整理项目架构\", \"帮我快速接手这个仓库\", \"codebase overview\", \"architecture report\", \"onboarding doc\", \"map this repo\", \"document the API surface\", \"what does this project do\", \"reverse-engineer this codebase\", or any request to explain a repository's structure, modules, endpoints, data model, config, auth, deployment, or risks. Also use it when someone inherits a project and wants a durable map before changing anything, or asks for a \"project analysis\", \"architecture explorer\", or technical due diligence on a repository. Stack-agnostic: it works for any language or framework by having you write a small mechanical extractor for that project's routing and models, then rendering everything into one offline HTML file."
---

# Project Analyzer

Turn an entire repository into one self-contained HTML report that a newcomer can
open in a browser and use to build a complete mental model — without re-reading
the source, and without trusting the README.

The report is the deliverable. Everything else (findings JSON, the extractors you
write, the temp directory) exists to produce it and must be cleaned up afterwards.

This skill is **stack-agnostic**. It ships the parts that are genuinely universal
— the report shell, the renderer, the file-tree builder, the findings contract —
and leaves the parts that must be tailored to the project to you. Do not look for
a bundled route extractor: writing one for the project in front of you is part of
the job, and the method is specified below.

## Why this shape

Reading a large codebase and *writing prose about it* produces something nobody
can use twice. What makes a report durable is:

- **Evidence over narrative.** Every claim carries a `path:line` the reader can
  jump to. A claim without a location is an opinion.
- **Mechanical enumeration over sampling.** "There are about 200 endpoints" is
  useless; a complete table of every endpoint with method, path, handler, auth and
  source line is a tool. Enumerate exhaustively wherever a script can.
- **Falsifiable extraction.** An enumerator that reports "0 handlers unreached" is
  trustworthy; one that just prints what it found is not. Always make your script
  tell you what it *missed*.
- **Explicit ignorance.** Anything you could not confirm from source gets marked
  `未确认` / `unconfirmed`, with a reason. A report that quietly guesses is worse
  than one that admits a gap, because the guess will be acted on.

## Non-negotiable rules

1. **Read the source, never infer from docs.** README and `docs/*` are leads, not
   evidence. Repositories routinely document files that no longer exist. Cite what
   you read.
2. **Do not modify the project.** Read-only except for the report and a temp
   analysis directory. Verify with `git status` at the end: the only new path
   should be the report.
3. **Never emit secrets.** Tokens, passwords, API keys, connection strings and
   private keys appear as *names and purposes* only. Run the renderer's secret scan
   and redact everything it flags. Development credentials are still credentials.
4. **Mark unconfirmed work.** Use `未确认` / `unconfirmed` plus a short reason (no
   runtime access, no DB connection, generated code, etc.).
5. **Delete the temp directory when done.** The report is self-contained; the
   findings JSON and your extractors are scratch, and
   `scripts/extract_findings.py` can recover the data from the report if it is
   ever needed again.

## Workflow

Rough budget: recon 10%, four parallel deep dives 35%, enumerators 15%,
synthesis 20%, render + browser verification 20%.

### Phase 0 — Recon (do this yourself, do not delegate)

Identify the skeleton before delegating, or the subagents will each rediscover it
and drift.

```bash
pwd && ls -la
# manifests / workspace boundaries — whatever exists
cat package.json pnpm-workspace.yaml Cargo.toml go.mod pyproject.toml requirements.txt \
    pom.xml build.gradle Gemfile composer.json mise.toml Makefile 2>/dev/null
find . -maxdepth 3 \( -name 'Dockerfile*' -o -name 'docker-compose*' -o -name '*.tf' \) 2>/dev/null
ls .github/workflows 2>/dev/null
# source shape
find <src-dirs> -type d | sort
find <src-dirs> -type f | wc -l
```

Answer, with evidence: what kind of thing is this (service? monorepo? library?
CLI? desktop?), what is the runtime, **where is the real entry point**, where are
routes/handlers registered, where is config loaded, is there a database. Find the
entry point by following imports from `main`/`index`/`app`, not by guessing from
directory names.

### Phase 1 — Four parallel deep dives

Delegate four independent sweeps as subagents **in the same turn** so they run
concurrently. Each writes exactly one JSON file and returns a summary. The exact
shape of each file, plus copy-pasteable subagent briefs, are in
`references/findings-schema.md`.

| Sweep | Investigates | Output |
|---|---|---|
| **frontend / client** | router and every page, state, API client, realtime transports, UI kit, build/test tooling, per-page → endpoint trace | `frontend.json` |
| **infra** | every workspace member/binary, process topology, dev + prod deploy, CI/CD, images, scheduler, external services | `infra.json` → feeds `jobs.json`, `deps.json`, `deploy.json` |
| **database / persistence** | engine, ORM, migration tool, every table with purpose/PK/FK/constraints, entity groups, core relations, enums, status fields | `database.json` |
| **modules** | per-module responsibility, entry, key files/symbols, upstream/downstream, core request flows, largest files, coupling | `modules.json` |

Rules to give every subagent verbatim (they matter more than the schema):

- Read-only. Create or modify **only** the one output JSON.
- Every important claim cites `path:line`. Verify each cited path exists.
- Anything not confirmable from source is the exact string `未确认` — never guess.
- Never reproduce secret values; names and purposes only.
- Do not stop at the top level — open the files.
- Verify the JSON parses before finishing.

Two files are best written by you while the sweeps run, because they need
cross-cutting judgement:

- `flows.json` — the 4–8 business-critical request paths, step by step, each step
  with a source location. This is the most-read page of the report.
- `risks.json` — see Phase 3.

### Phase 2 — Write the enumerators

Sampling is where reports lose their value. For anything countable — endpoints,
tables, pages, tasks, config keys — write a small script that enumerates it
mechanically and **reports what it could not reach**. Put these in the temp
directory; they are scratch, not project code.

#### 2a. Route / endpoint extractor

There is deliberately no bundled extractor, because route registration is the one
thing that differs wildly between frameworks. `references/extractor-recipes.md`
explains how prefixes compose in the common families (Express/NestJS/Fastify,
FastAPI/Flask/Django, Spring, Go chi/gin/echo, Rails, Next.js file routes, actix,
ASP.NET) and lists the traps. Read it, then write one for this project.

The job is always the same three steps:

1. **Index the handler declarations.** Find every place a route is declared —
   decorators, attributes, macro annotations, a routes file, a file-system
   convention — and record method, path fragment, handler name, file and line.
2. **Index the mount points.** Find where those handler groups are registered onto
   parent routers, recursively, so a nested prefix chain can be composed.
3. **Walk the mount graph** from the router root(s), accumulating prefixes, and
   emit one row per reachable endpoint.

Emit a JSON array where each item satisfies this contract — the renderer's API
explorer, prefix tree, filters and search all depend on these field names:

| field | meaning |
|---|---|
| `method` | `GET` / `POST` / … (upper case) |
| `path` | **fully resolved** path with every prefix concatenated |
| `handler` | handler function/method name |
| `file`, `line` | where the route is declared |
| `module` | grouping label (`identity`, `admin/users`, …) |
| `auth` | `public` / `user` / `admin` / `internal-token` / `query-ticket` / your own label |
| `summary` | the handler's doc comment, with a redundant `METHOD path` prefix trimmed |
| `middleware` | middleware/guard chain, if you can determine it |
| `mounts` | every prefix this endpoint is reachable from |
| `alsoAt` | other paths the *same handler* is registered at (duplicate surface) |
| `id` | stable slug for deep links (`#api::<id>`) |

**Acceptance criteria — the script must report all four, and you must read them:**

- **Total count**, plus breakdowns by method / auth / module.
- **Unreached handlers**: every handler that carries a route declaration but was
  not reached from the roots. This must be **zero**. A non-empty list means your
  prefix chain is incomplete — chase it before trusting the table. This single
  check is what separates enumeration from guessing.
- **Duplicate mounts**: the same handler reachable at several paths. That is a
  real finding for the Risks page, not a data quirk.
- **Warnings**: unresolved mount references, or a cycle. Both indicate a bug in
  your resolver.

Do not skip the unreached check because the numbers "look right". In practice it
is what surfaces an entire module missing from the table.

#### 2b. File tree and annotations

The bundled tree builder is stack-agnostic — use it:

```bash
python3 <skill>/scripts/build_tree.py --root . \
  --out .proj-analysis/tree.json \
  --annotations .proj-analysis/tree-notes.json \
  --exclude <extra-noise-dirs>
```

`tree-notes.json` is a hand-written `path -> {role, module, core, exports, deps,
usedBy, api, note}` map. **Annotate the 15–30 paths that matter** — entry points,
routers, config, schema, auth, the main service of each domain. Without
annotations the explorer is a directory listing; with them it is a map. Confirm
the builder's own output does not contain your temp directory (it excludes
`.proj-analysis`, `.agents`, `.claude` by default).

### Phase 3 — Risks (write this yourself)

Risks are where the report earns its keep, and exactly what a subagent gets wrong:
either generic ("could be better structured") or unverified. Every entry needs:

- **phenomenon** — what is actually true, and the mechanism behind it.
- **sources** — `path:line` for each claim.
- **impact** — what it costs someone trying to understand or change the project.
- **advice** — what to do about it while onboarding.

High-yield patterns, all found by running this skill on real repositories:

- A comment or doc claim that contradicts the code.
- The same handler registered under two prefixes (shadow endpoints).
- Two similarly-named fields with different semantics, only one validated.
- A response convention that breaks the obvious assumption (e.g. always HTTP 200
  with the business code in the body).
- Duplicated handler sets or parallel pipelines that must be kept in sync.
- A config value read with `unwrap()`/`expect()` on a request path.
- A cache or global that makes configuration changes appear not to take effect.
- Generated artifacts that people edit by mistake.
- CI steps that silently do nothing.

Do not pad the list. Ten verified risks beat thirty speculative ones. Anything you
could not confirm goes in the findings file's `notes` array — the renderer
aggregates all of those into one "未确认事项" list at the bottom of the Risks page.

### Phase 4 — Build the report

```bash
python3 <skill>/scripts/render_report.py \
  --findings .proj-analysis --out PROJECT-ANALYSIS.html \
  --name "<Project>" --brand "<Project> · 项目分析"
```

The renderer prints which sections it included and which it omitted for lack of
findings, checks that the embedded JSON round-trips, warns about external
resources (the report must work offline), and scans its own output for
credential-looking strings. Read all four blocks of that output. Sections
disappear automatically when their findings file is missing, so a project with no
database or no frontend simply does not show those pages.

Rendering is **deterministic**: the same findings always produce the same bytes, so
re-rendering after a template tweak gives a diff of exactly what you changed. And
because the report embeds its full findings payload, the scratch directory is
disposable — recover it any time with:

```bash
python3 <skill>/scripts/extract_findings.py --report PROJECT-ANALYSIS.html --out .proj-analysis
```

That is how you re-render, restyle, or diff against a report produced earlier
(including one produced before this skill existed).

### Phase 5 — Verify in a browser (do not skip)

A report with one JavaScript error renders as a blank page, and a 700 KB file looks
perfectly healthy from the shell. Serve it and drive a real browser:

```bash
python3 -m http.server 8791 --bind 0.0.0.0 &     # file:// is usually blocked
```

`references/browser-verification.md` has nine runnable checks. In order of
importance: the number of mounted sections matches what the renderer promised; no
console exceptions; **zero duplicate element ids**; filters and the tree↔list
toggle change the visible count; deep links (`#api::<id>`, `#model-<table>`,
`#files::file-<slug>`) switch page and reveal the target; theme toggle persists.
Fix, re-render with a cache-busting query, re-verify. Then kill the server.

### Phase 6 — Clean up

```bash
rm -rf .proj-analysis
git status --short          # must show only the new report
```

If `git status` shows anything else, you modified the project — revert it.

## Pitfalls

Ordered by how often they bite. The first four are extractor traps specifically.

- **A prefix chain has more shapes than the framework's docs suggest.** Besides
  the obvious registration call, modules often delegate with a plain call
  (`register_admin_routes(app);`) or an attribute (`@Import`). Miss a shape and
  whole modules vanish from the table.
- **"Same file wins" is wrong for qualified references.** Resolving a
  fully-qualified reference to the same-named symbol in the current file creates a
  self-cycle that grows the prefix forever. Only bare/sibling names should resolve
  locally.
- **Bound every graph walk.** Cap prefix depth and detect ancestor repetition, so
  a resolver bug prints a warning instead of hanging.
- **Make the extractor report misses, not just hits.** Without the unreached-handler
  list you cannot tell a complete enumeration from a partial one.
- **Your temp directory can end up inside your own output** if you build the file
  tree after creating it. Exclude it, and check the tree's root listing before
  shipping.
- **Table helpers that take cell arrays will throw** if one caller passes
  pre-built `<tr>` HTML strings. Keep the contract.
- **Duplicate element ids across pages** break deep links silently. Each page's
  filter counter needs a unique id, and two views of the same list must never both
  be mounted.
- **Section predicates must match the findings shape.** A predicate reading
  `d.flows.length` hides the section when the file is `{summary, flows:[...]}`.
  The template's `arr()` helper accepts either — use it.
- **JSON inside `<script>`**: escape `</` as `<\/` when embedding, or a string
  containing `</script>` ends the block early.
- **Doc comments vanish if you strip comments before reading them.** If you want
  the description above a handler, read it from the raw text — line numbers still
  align because newlines survive comment stripping.
- **`file://` navigation is often blocked** in automated browsers. Serve over HTTP;
  a loopback port may be refused where a LAN IP works, so try both.
- **Screenshots may hang** on some CDP setups. DOM assertions (element counts,
  `offsetParent`, computed styles) verify a report just as well and never time out.

## Files in this skill

- `scripts/build_tree.py` — noise-excluding, annotation-aware file tree builder
  (stack-agnostic).
- `scripts/render_report.py` — findings → single offline HTML, with section
  omission, embedded-JSON validation, a secret scan and deterministic output
  (stack-agnostic).
- `scripts/extract_findings.py` — recover a findings directory from a rendered
  report, so the scratch directory is always disposable.
- `assets/tpl_head.html` — report shell styles: light/dark, no CDN.
- `assets/tpl_body.html` — navigation, global search, API explorer (prefix tree +
  list), file explorer, ER diagram rendering, deep links, theme toggle.
- `references/findings-schema.md` — exact shape of every findings file, plus
  copy-pasteable subagent briefs.
- `references/extractor-recipes.md` — how route prefixes compose across framework
  families, the universal traps, and the worked method for writing an extractor.
- `references/browser-verification.md` — the verification checklist with runnable
  assertions.
