# Findings schema

Every file lives in the temp analysis directory (`--findings`, default
`.proj-analysis/`) and is named `<key>.json`. The renderer omits any section whose
file is missing, so partial analysis still produces a usable report.

Two shapes appear: a **bare array** (`endpoints.json`) and an **object wrapping a
list** (`flows.json` → `{summary, flows:[...]}`). The template's `arr(v, key)`
helper accepts either for the list-bearing files, so when in doubt wrap it in an
object and include a `summary`.

Text fields may contain inline HTML (`<span class="mono">`, `<b>`, `<a>`); the
template escapes by default and only passes through the fields marked **HTML**
below. Never put untrusted third-party text in an HTML field.

---

## `meta.json`

Drives the Overview page and the browser title.

```json
{
  "name": "Project",
  "tagline": "one sentence: what it is and what it is for",
  "oneLiner": "what it does, in one line",
  "type": "Web full-stack / monorepo / CLI / library / service mesh",
  "shape": "Cargo workspace + pnpm workspace; packages/* is an empty declaration",
  "repoState": "branch X · HEAD abc1234 · 47 migrations applied",
  "stack": ["Rust 2024", "Actix Web", "React 19"],
  "archPoints": ["<b>HTML allowed</b> — 4-6 bullets that reframe the reader's model"],
  "stats": [{"value": "273", "label": "HTTP endpoints", "src": "mechanically extracted"}],
  "keyEntries": [{"path": "src/bootstrap/routes.rs", "line": 8, "role": "what it is", "why": "why read it first"}],
  "surface": [{"area": "HTTP REST endpoints", "count": "273", "note": "151 admin / 105 user / 9 internal / 8 public"}],
  "caveats": ["<b>HTML allowed</b> — what this report did NOT verify"]
}
```

`stats` should be numbers you extracted, not impressions. `caveats` is where you
state scope limits honestly (no runtime probing, docs not trusted, etc.).

---

## `architecture.json`

```json
{
  "summary": "HTML allowed — the layering, in 2-3 sentences",
  "layers": [{"name": "api", "path": "src/api", "role": "what this layer owns",
              "types": "UniResponse, AppError, ReqCtx"}],
  "decisions": [{"title": "short name", "text": "HTML allowed — the decision and its consequence",
                 "src": "src/bootstrap/routes.rs", "line": 8}],
  "engines": [{"engine": "Jeopardy", "mode": "family=jeopardy", "model": "tables involved",
               "flow": "the core loop in one sentence", "files": ["src/.../submission_service.rs"]}],
  "modules": [ /* optional: copy of modules.json's modules, rendered as a dependency table */ ]
}
```

- `layers` renders both a stacked diagram and a table. Keep it to the real
  layering — do not force MVC onto a project that is not MVC.
- `engines` is for projects with variants (multiple engines, modes, drivers,
  adapters). Omit it entirely if the project has one behaviour.
- `decisions` is the highest-value field: architectural choices a newcomer would
  otherwise reverse-engineer painfully.

---

## `modules.json`

```json
{
  "summary": "HTML allowed — how modules relate (direct calls? traits? events?)",
  "modules": [{
    "name": "identity",
    "path": "src/modules/identity",
    "responsibility": "what it owns, in one line",
    "entry": "src/modules/identity/mod.rs:12",
    "keyFiles": [{"path": "src/modules/identity/auth/mod.rs", "role": "login / register"}],
    "keySymbols": [{"name": "user_login", "kind": "fn", "role": "argon2 verify + issue JWT"}],
    "upstream": ["infrastructure", "core"],
    "downstream": ["bootstrap", "event"],
    "routes": ["/api/users/*"],
    "lifecycle": "when it runs / how it is initialized",
    "notes": "anything surprising"
  }],
  "largestFiles": [{"path": "src/.../training.rs", "lines": 1318, "why": "all handlers in one file",
                    "risk": "cannot be read in one pass"}],
  "coupling": [{"module": "common", "coupledWith": "awd", "kind": "circular|god|shared",
                "evidence": "src/common/team_service.rs:11", "impact": "what it blocks"}],
  "conventions": {"responseEnvelope": "UniResponse — always HTTP 200, code in body",
                  "reqCtx": "ReqCtx injects db/config/... and panics if absent"},
  "quirks": ["<b>HTML allowed</b> — verified oddities worth knowing"],
  "notes": ["unconfirmed items, prefixed 未确认"]
}
```

`upstream`/`downstream` must be the *actual* dependency direction you observed in
imports and call sites, not the intended design.

---

## `endpoints.json` (bare array)

Emitted by the extractor **you write for this project** — see
`references/extractor-recipes.md` for the method and the traps. Required keys per item:

| key | meaning |
|---|---|
| `method`, `path` | final HTTP method and fully-resolved path (all prefixes concatenated) |
| `handler` | handler function name |
| `file`, `line` | where the route is declared |
| `module` | grouping label |
| `auth` | `public` / `user` / `super-admin` / `internal-token` / `query-ticket` / your own |
| `summary` | handler doc comment with the redundant `METHOD path` prefix trimmed |
| `middleware` | middleware chain, from `--middleware` |
| `mounts` | every prefix this endpoint is reachable from |
| `alsoAt` | other paths the *same handler* is registered at (duplicate surface) |
| `id` | stable slug used for deep links (`#api::<id>`) |

The renderer's prefix tree, filters and search all derive from these fields.

---

## `flows.json`

```json
{
  "summary": "HTML allowed — what these flows cover",
  "flows": [{
    "id": "flow-login",
    "title": "Player login (POST /api/users/session)",
    "kind": "auth|core|admin|background",
    "summary": "the whole flow in one sentence",
    "steps": [{"n": 1, "what": "what happens at this step", "source": "src/.../auth.rs:19"}],
    "notes": ["gotchas discovered while tracing"]
  }]
}
```

Prioritise: authentication, the primary business operation, data creation, data
read, background work. Every step needs a source line — a step without one is
guesswork, and this page is where readers jump into the code.

---

## `database.json`

```json
{
  "engine": "PostgreSQL 17",
  "orm": "SeaORM",
  "ormVersion": "1.1.20",
  "migrationTool": "src/sql/migrate.sh",
  "migrationCount": 47,
  "initPath": [{"step": "start infra", "cmd": "make infra-up"}],
  "generation": {"entities": "scripts/gen_entities.py", "tsTypes": "scripts/gen_web_types.py",
                 "cli": "sea-orm-cli", "cliVersion": "1.1.20"},
  "tables": [{"name": "users", "group": "identity", "purpose": "player accounts",
              "pk": "id uuid", "keyFields": ["username (unique)", "password (argon2id)"],
              "relations": ["event_users.user_id -> users.id (1:N)"],
              "constraints": ["UNIQUE(username)"],
              "source": "migrations/001-initial.sql:1749"}],
  "groups": [{"name": "identity", "desc": "accounts", "tables": ["users"]}],
  "erCore": [{"from": "users", "to": "event_users", "card": "1:N",
              "via": "event_users.user_id", "note": "registration row"}],
  "erLayout": [{"group": "identity", "tables": ["users"], "order": 1}],
  "enums": [{"name": "event_family", "values": ["jeopardy", "awd"],
             "source": "src/entity/enums.rs", "usedBy": "events.family"}],
  "statusFields": [{"table": "event_challenges", "column": "hidden", "values": "true|false",
                    "behavior": "when true the challenge is invisible, unlaunchable, unscorable"}],
  "settingsSystem": {"how": "runtime-editable rows in a settings table", "source": "src/settings.rs:13"},
  "notes": ["unconfirmed"]
}
```

`erLayout` drives the ER diagram: **8 or fewer groups, ~28 or fewer tables total.**
Draw only what a newcomer must understand — a 60-table spider graph is worse than
no diagram. `erCore` edges must reference tables present in `erLayout` (the
renderer skips edges whose endpoints are missing).

Enumerate **all** tables in `tables` even when the diagram is small.

---

## `config.json`

```json
{
  "loader": {
    "how": "read once at startup, fail-fast, no hot reload",
    "pathResolution": "ENV_VAR -> default path",
    "onlyEnvVar": "the one env var the process reads",
    "secrets": "which fields are wrapped so they never reach logs"
  },
  "intro": "HTML allowed",
  "items": [{"section": "server", "key": "listen_port", "rustField": "server.listen_port",
             "required": false, "default": "9090", "purpose": "API listen port",
             "source": "src/config.rs:37"}],
  "dynamicSettings": {"note": "runtime-editable rows", "source": "src/settings.rs:13",
                      "defaults": [{"key": "CACHE_TTL", "type": "Integer", "default": "60",
                                    "purpose": "what it controls"}]},
  "sidecarEnv": {"note": "injected into child processes, not read by the app itself",
                 "worker": [{"name": "INTERNAL_TOKEN", "source": "src/deploy.rs:390",
                             "purpose": "callback bearer token (SECRET, never printed)"}]},
  "notes": ["unconfirmed"]
}
```

Never put a real value in `default` for anything secret — write
`"—（SECRET，值不展示）"`. The renderer's secret scan is a backstop, not the plan.

---

## `auth.json`

```json
{
  "summary": "HTML allowed — the whole authz model in 2 sentences",
  "chain": "<div class=\"lay\">…</div>",
  "mechanisms": [{"name": "player JWT", "how": "HTML allowed — how it is issued and checked",
                  "storage": "Header: Authorization", "scope": "105 endpoints",
                  "source": "src/api/extractor/auth.rs:26"}],
  "matrix": [{"auth": "super-admin", "count": 151, "meaning": "requires admin JWT",
              "examples": ["POST /api/admin/events"]}],
  "publicEndpoints": [{"method": "POST", "path": "/api/users/session",
                       "handler": "user_login", "file": "src/identity/auth.rs", "line": 19}],
  "internal": "<div class=\"note\">HTML — how service-to-service auth works</div>",
  "authorization": [{"title": "no RBAC table", "text": "HTML — how access is actually decided",
                     "src": "src/security/jwt.rs"}],
  "notes": ["unconfirmed"]
}
```

`chain` and `internal` are the only raw-HTML fields here — they hold hand-built
diagrams. Keep them to `<div class="lay">`, `<div class="laygroup">`,
`<div class="layrow">`, `<div class="box">`, `<div class="arw">` and `<div class="note">`.
Counting endpoints per auth level from `endpoints.json` is what makes the matrix
trustworthy.

---

## `frontend.json`

```json
{
  "summary": "HTML allowed",
  "stack": {"framework": "React 19", "router": "TanStack Router", "ui": "Primer",
            "state": "Zustand", "dataFetching": "TanStack Query + axios",
            "build": "Vite", "test": "Vitest", "packageManager": "pnpm"},
  "pages": [{"route": "/service/events/$id", "file": "src/routes/....tsx",
             "component": "EventDetail", "group": "player|admin|auth",
             "apis": ["GET /api/events/{event_id}"], "notes": "30s polling"}],
  "apiClient": {"files": [{"path": "src/api/axios.ts", "role": "the single HTTP pipe"}],
                "authTokenStorage": "where the token lives",
                "interceptors": "what they do",
                "errorEnvelope": "response shape"},
  "stores": [{"path": "src/stores/AuthStore.ts", "role": "only global store",
              "persistedState": "token", "usedBy": "every page"}],
  "sse": [{"hook": "useEventStream", "file": "src/hooks/useEventStream.ts",
           "endpoint": "GET /api/events/{id}/stream", "purpose": "live updates + polling fallback"}],
  "navigation": {"adminMenu": "…", "playerMenu": "…", "roleLogic": "how visibility is decided"},
  "quirks": ["<b>HTML allowed</b> — verified oddities"],
  "notes": ["unconfirmed"]
}
```

Enumerate every page. For each, trace `page → hook/store → api function → HTTP
path`; that trace is the whole point of the page table. If you cannot confirm a
page's endpoints, put `"apis": []` and a note rather than guessing.

---

## `jobs.json`

```json
{
  "summary": "HTML allowed — the async model (queue? cron? table? broker?)",
  "engine": {"how": "how work is claimed and executed", "persistence": "where task rows live",
             "pollInterval": "5s", "wake": "how it is triggered immediately",
             "files": [{"path": "src/scheduler/engine.rs", "role": "claim + retry"}]},
  "tasks": [{"key": "cleanup.instances", "trigger": "cron */30 * * * * *",
             "handler": "CleanupHandler", "dependency": "Docker + instances table",
             "purpose": "what it does", "source": "src/tasks.rs:78"}],
  "lifecycle": [{"what": "startup: handlers registered, duplicate registration fails fast",
                 "source": "src/bootstrap/scheduler.rs:128"}],
  "streams": [{"endpoint": "GET /api/events/{id}/stream", "dir": "SSE",
               "payload": "score/state deltas with sequence numbers",
               "source": "src/events/player.rs:508"}],
  "notes": ["e.g. handlers must be idempotent because claiming and executing are separate"]
}
```

Include one-shot/dynamically-scheduled tasks, not only the recurring ones — a task
list that omits event-lifecycle jobs is misleading.

---

## `deps.json`

```json
{
  "summary": "HTML allowed — the shape of the dependency surface",
  "groups": [{"name": "Backend framework", "desc": "what this group determines",
              "items": [{"name": "actix-web", "version": "4.x",
                         "usage": "what it is ACTUALLY used for here, not what it is",
                         "source": "Cargo.toml"}]}],
  "externalServices": [{"name": "Redis", "form": "container", "usage": "five distinct uses",
                        "required": true, "source": "src/redis.rs"}],
  "notes": ["unconfirmed"]
}
```

Do not paste a lockfile. Include a dependency only if it shapes the architecture,
and explain its concrete role in *this* project.

---

## `deploy.json`

```json
{
  "summary": "HTML allowed",
  "dev": {"flow": "1. install\n2. start infra\n3. migrate\n4. run api + web",
          "notes": "HTML allowed", "entry": "mise run dev",
          "commands": ["mise run dev", "mise run dev:down"]},
  "prod": {"flow": "the real deployment sequence",
           "notes": "HTML allowed", "installer": "scripts/install.sh",
           "home": "/var/lib/app", "compose": "how compose is produced",
           "systemdUnits": ["app.service"], "networks": ["internal bridge"],
           "services": [{"name": "api", "image": "app:${VERSION}", "ports": "none on host",
                         "user": "65532:1000", "security": "cap_drop ALL + read_only",
                         "purpose": "the only business process"}]},
  "ci": {"workflows": [{"path": ".github/workflows/ci.yml", "name": "CI",
                        "triggers": "push / pull_request",
                        "jobs": [{"job": "test", "runsOn": "ubuntu-latest",
                                  "steps": ["the exact commands"], "gated": true}]}],
         "gateCommands": ["the exact commands a developer must pass locally"],
         "notes": ["anything inert or skipped"]},
  "dockerfiles": [{"path": "docker/api/Dockerfile", "purpose": "runtime image",
                   "base": "debian-slim", "notes": "runs non-root"}],
  "notes": ["unconfirmed"]
}
```

Copy the commands **verbatim** from the task runner and CI files. Report CI steps
that do nothing as a finding — a green CI that never ran the integration tests is
exactly what an onboarding engineer needs to know.

---

## `entry.json`

```json
{
  "summary": "HTML allowed — the reading strategy, and why that order",
  "order": [{"path": "Makefile", "why": "what the project can do"},
            {"path": "src/bootstrap.rs", "line": 46, "why": "the real startup sequence"}],
  "groups": [{"title": "Application Entry",
              "items": [{"path": "src/main.rs", "why": "why this file first"}]}]
}
```

Group headings are free text but conventionally: Application Entry, API Entry,
Database Entry, Configuration Entry, Frontend Entry, Worker Entry, Test Entry.
Explain *why each file repays the reader's time*; "it is the entry point" is not a
reason.

---

## `risks.json`

```json
{
  "summary": "HTML allowed — what class of risk this section covers, and its standard of evidence",
  "risks": [{
    "title": "Two fields named hidden with different meanings",
    "severity": "高|中|低",
    "kind": "data model",
    "phenomenon": "HTML allowed — what is true, and the mechanism behind it",
    "sources": ["src/schema/001.sql:1126", "src/schema/001.sql:1279"],
    "impact": "HTML allowed — what it costs someone changing this",
    "advice": "HTML allowed — what to do"
  }]
}
```

Severity is about **cost to understand and change**, not production incident
risk — say so in `summary` so nobody misreads it. Every risk needs a real
mechanism; "this file is large" is only a risk if you also say why it blocks work.

Anything you could not confirm goes in a `notes` array on its findings file; the
renderer aggregates all of them into the "未确认事项" list at the bottom of the
Risks page. That aggregation is deliberate: scattered uncertainty is invisible.

---

## Subagent briefs

Copy these into the subagent prompts and adjust the project paths. The rules block
matters more than the schema block — subagents left to their own judgement will
read the README and summarise it.

**Common rules block:**

```
You are analyzing the repository at <ABS_PATH> (a <one-line description>).

HARD RULES:
- READ ONLY. Create or modify exactly one file: <output path>. Nothing else.
- Base every conclusion on source you actually read. Cite `path/to/file.ext:LINE`
  for every important claim. Verify each cited path exists.
- If something cannot be confirmed from source, write the exact string 未确认
  (plus a short reason). Never guess, never infer from the README alone.
- Never reproduce secret values (tokens, passwords, keys, connection strings).
  Names and purposes only.
- Do not stop at the top level. Open the files.
- Output valid UTF-8 JSON at exactly <output path>, matching this shape: <schema>
- Verify it parses before finishing: python3 -c "import json;json.load(open('<path>'))"
```

**Sweep-specific focus:**

- *frontend*: the router and every page route; the API client (base URL, token
  storage, interceptors, error envelope); state stores; realtime transports;
  build/test/lint tooling; per-page endpoint trace. Count the pages and confirm
  coverage explicitly.
- *infra*: every workspace member and binary; how each process starts; dev and
  production topology; the installer or IaC; CI workflows with exact commands;
  image builds; the scheduler; external services. Extract the production compose
  or manifests, but never copy credentials.
- *database*: the migration tool's rules, the full table inventory with
  purpose/PK/FK/constraints, the core entities worth diagramming, enums, and the
  status fields that drive behaviour.
- *modules*: per-module responsibility, entry, key files and symbols,
  upstream/downstream, the core request flows, the largest files, and coupling
  that is real (circular imports, god modules, near-duplicate code).
