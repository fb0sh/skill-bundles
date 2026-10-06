# Writing a route extractor for any framework

Route registration is the one thing that differs wildly between stacks, which is
why this skill ships the method and not an implementation. Read this, then write a
small script for the project in front of you.

## The method (identical everywhere)

1. **Index the handler declarations.** Every place a route is bound to a handler:
   decorators, attributes, macro annotations, entries in a central routes file, or
   a file-system convention. Record `method`, path fragment, handler symbol, file,
   line, and the handler's doc comment.
2. **Index the mount points.** Where a group of routes is attached to a parent
   router — and recursively, where *that* parent is attached. This is the step
   people skip, and it is the step that makes the difference between a correct
   table and fiction.
3. **Walk the mount graph from the root** (the app/router construction site),
   accumulating prefixes, and emit one row per reachable endpoint.

Then report the acceptance criteria from `SKILL.md`: total + breakdowns, **zero
unreached handlers**, duplicate mounts, and any unresolved/cyclic references.

### Two resolution modes

Most frameworks fall into one of these. Identify which before writing code.

- **Decorator/attribute mode** (FastAPI, Flask, NestJS, Spring, ASP.NET, actix):
  the method and local path live next to the handler, and the prefix comes from an
  enclosing class/controller/scope plus a global prefix. You need both halves.
- **Central-registration mode** (Express, Rails, Django, chi, gin, Phoenix,
  Litestar routers): paths and handlers are wired in one or more router files,
  often by calling a sub-registrar. Prefixes nest through function calls.

Mixed cases are common (Spring's `@RequestMapping` on a class + `@GetMapping` on a
method; Express routers mounted inside routers). Handle both halves.

### Prefer the framework's own dumping

If the framework can dump its own route table, use it — it is mechanical
enumeration by definition, and better than parsing:

| Framework | Command |
|---|---|
| Rails | `rails routes` |
| Django | `django-extensions` `show_urls`, or read `urlpatterns` |
| FastAPI | `app.openapi()` / the generated `/openapi.json` |
| NestJS | Swagger module output, or `app.getHttpServer()._events` router stack |
| Spring Boot | actuator `/actuator/mappings` |
| ASP.NET Core | `dotnet aspnet-codegenerator`, or `EndpointDataSource` dump |
| Express | `app._router.stack`, or `DEBUG=express:router` |
| Laravel | `php artisan route:list` |
| Phoenix | `mix phx.routes` |

Only fall back to source parsing when the app cannot be booted (missing deps, no
database, no credentials). If you do boot it, note in the report that the table
came from runtime introspection, not static reading — that is a stronger claim and
worth stating.

## Family notes

For each family: where declarations live, how prefixes compose, and the trap that
bites.

### Express / Koa / Fastify / Hapi (JS/TS)

- Declared as `app.get('/x', h)`, `router.post('/x', h)`, or Fastify's
  `fastify.route({method, url, handler})`.
- Prefixes compose through `app.use('/base', router)` and nested
  `router.use('/sub', subRouter)`.
- **Trap:** a router file often exports a router whose mount prefix lives in a
  *different* file (the server entry). You must follow the import and find the
  `use()` call, or every path will be missing its prefix. Also watch for route
  arrays and `router.route('/x').get(h).post(h)` chains.

### NestJS

- `@Controller('users')` on the class, `@Get(':id')` on methods; prefix also comes
  from `app.setGlobalPrefix('api')`.
- **Trap:** the global prefix and any `RouterModule.register([{path, module}])`
  entries are outside the controllers entirely. Versioning (`@Version`) adds a
  segment too.

### Next.js / Remix / SvelteKit / Nuxt (file-system routing)

- The path *is* the file path. Route groups `(group)`, dynamic `[id]`, catch-all
  `[...slug]`, and parallel/intercepting segments (`@slot`, `(.)`) each change the
  final URL, and layout files do not create endpoints.
- **Trap:** enumerate route-defining files (`page.tsx`, `route.ts`, `+server.ts`,
  `+page.server.ts`) and *then* translate conventions to URLs; do not assume the
  filesystem maps 1:1. API routes and pages are different sets.

### FastAPI / Flask / Litestar (Python)

- `@app.get("/x")` / `@router.get("/x")` on the handler; prefixes come from
  `APIRouter(prefix="/base")` plus `app.include_router(r, prefix="/api")`.
- **Trap:** the router object is often defined in one module and included in
  another, and `include_router` can stack prefixes (both the router's own and the
  include's). Response models and dependencies (auth) are declared on the same
  decorator — capture `dependencies=[Depends(...)]` and `security=` as auth.

### Django

- `urlpatterns = [path('users/', include('users.urls'))]`, nested through
  `include()`. Views may be functions or class-based (`as_view()`).
- **Trap:** `include()` composes prefixes across files, and DRF routers
  (`DefaultRouter().register('users', ViewSet)`) synthesize a whole family of
  paths, including detail routes with `{pk}`. Enumerate the ViewSet's actions, not
  just the registration line.

### Spring Boot (Java/Kotlin)

- Class-level `@RequestMapping("/users")` (or `@RestController` + method-level
  paths), method-level `@GetMapping("/{id}")`.
- **Trap:** the prefix also comes from `server.servlet.context-path` and any
  `spring.mvc.servlet.path` in properties, plus `@RequestMapping` on interfaces.
  Auth lives in a `SecurityFilterChain` config, not on the handler — resolve it
  separately and join by path pattern.

### Go — chi / gin / echo / net/http

- chi: `r.Route("/users", func(r chi.Router){ r.Get("/{id}", h) })`; gin:
  `g := r.Group("/users"); g.GET("/:id", h)`; net/http 1.22+:
  `mux.HandleFunc("GET /users/{id}", h)`.
- **Trap:** grouping is expressed as nested closures, so a parser that only looks
  for string literals will miss the nesting. Also note chi/gin use `:param` while
  net/http and chi's newer style use `{param}` — record the path verbatim.

### Rails

- `config/routes.rb` DSL: `namespace`, `scope`, `resources`, `member`/`collection`
  blocks, `mount`.
- **Trap:** `resources :users` expands to seven endpoints with different paths and
  verbs; `namespace` adds both a prefix and a module. Use `rails routes` if
  runnable — the DSL is expressive enough that hand-parsing is error-prone.

### Rust — actix-web / axum / rocket

- actix: `#[get("/x")]` attributes plus `web::scope("/base").service(h).configure(cfg)`.
- axum: `Router::new().route("/x", get(h)).nest("/base", sub)`.
- rocket: `#[get("/x")]` plus `mount("/base", routes![...])`.
- **Trap:** modules delegate with a plain call as often as with `.configure(...)` —
  e.g. `crate::module::configure_x(cfg);`. Miss that shape and entire modules
  disappear. Also: a scope/`nest` can be registered at more than one prefix, which
  is how shadow endpoints appear.
- **Note:** a worked actix resolver — including the "same file wins is wrong for
  qualified references" bug and the unbounded-prefix cycle it causes — is the
  origin of the traps section in `SKILL.md`. Those two bugs are worth re-reading
  before you write any resolver: they apply to every framework with nesting.

### ASP.NET Core

- `[Route("api/[controller]")]` / `[HttpGet("{id}")]`, or minimal APIs
  `app.MapGet("/x", h)` and `app.MapGroup("/base")`.
- **Trap:** `[controller]`/`[action]` tokens expand from the class/method name;
  conventional routing (`{controller}/{action}`) has no attribute to read at all.

### Phoenix (Elixir)

- `scope "/api", MyAppWeb do ... end` inside `router.ex`, with
  `resources "/users", UserController` and `get "/x", Controller, :action`.
- **Trap:** the action name is a third element in the tuple and the controller
  module is separate; `pipeline` blocks attach auth per-scope, which is where you
  should read auth from.

## Determining auth per endpoint

Auth is rarely declared on the handler, so resolve it in layers and record the
strongest evidence you have:

1. **On the handler** — decorator/attribute/extractor parameter
   (`@PreAuthorize`, `[Authorize]`, `Depends(require_admin)`, `UserJwtGuard` in the
   signature). Most reliable.
2. **On the group** — a router-level middleware/guard/pipeline, a `scope` block, a
   `@UseGuards` on the controller. Join by prefix.
3. **Global with an exclusion list** — a security config plus a public-paths array.
   Highest false-positive risk; state it as inferred.
4. **Unknown** — emit `public` only when you have positive evidence nothing guards
   it. Otherwise use a label like `unknown` and say so. Reporting a protected
   endpoint as public is the single most damaging error this report can make, so
   when in doubt, say in doubt.

## The same philosophy for data models

Do not hard-code an ORM parser either. Read how the project defines schema and
enumerate from the authoritative artifact:

- **Migrations** (`migrations/*.sql`, `alembic/versions`, `db/migrate`,
  `prisma/schema.prisma`, `*.sql`): the current shape is baseline **plus every
  increment in order**. Reading only the baseline gives stale conclusions — a
  reliable mistake to avoid.
- **Generated models/entities**: often reflect the live database more accurately
  than migrations do, but they are generated — never suggest editing them.
- **Live database**: `information_schema` / `pg_dump --schema-only` is the ground
  truth if you are allowed to connect. If you do, say so in the report.

Cross-check at least two of these. Where they disagree, note it — drift between
schema, generated code and application code is a common and high-value finding.
