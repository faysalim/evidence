# Domain: CMS / content platform

Authors write content; a published surface serves it. The gap between those two is where every
defect in this domain lives: **what an author previews is not what a reader gets**, and the product
reports success on the authoring side regardless.

## Do the thing

> Create content with every field type the schema allows, including one required field left empty
> and one embedded reference. Preview it. Publish it. Then fetch the **public** URL as an
> unauthenticated reader, from a cold cache, and compare it to the preview. Then unpublish it and
> fetch again. **`Published` is this domain's HTTP 200**: the status says the author's intent, not
> the reader's reality, and a stale CDN or a missing permission makes them different without
> anything turning red.

## Scope map

| Family | In this domain | Agent | Notes |
|---|---|---|---|
| 1 Acquisition | docs, sign-up, starter templates | N/A | |
| 2 Primary product | author → publish → public read | own ×2 | split: authoring and validation vs the published read path |
| 3 Control plane | content model/schema, roles, workflow states, localisation setup | own | schema change is the dangerous operation here |
| 4 Deployment | if self-hosted: media storage, CDN, build hooks, preview environment | own | |
| 5 Entitlement | seats, API call limits, bandwidth | →3 | |
| 6 Secondary | media library, versioning, scheduled publish, redirects, search | own ×2 | scheduling and redirects are where silent breakage lives |
| 7 Telemetry | content analytics | →12 | |
| 8 Security | **draft and unpublished content reachable without auth**, API tokens, tenant isolation | own | the embargo leak is the headline risk |
| 9 Documentation | the API contract, the publish semantics, the cache behaviour | own | |
| 10 State under fault | publish mid-build, CDN stale, media upload interrupted, schema change with live content | own ×2 | split: cache/build faults vs schema migration over existing content |
| 11 Upgrade | schema migration, plugin/extension versions, media URL changes | own | |
| 12 Experience | can an author tell what a reader will see | lead | |

**Usual set: 2×2,3,4,6×2,8,9,10×2,11 own + 5→3, 7→12, 12→lead = 12 agents.**

## Failure catalogue

- **Draft or embargoed content readable without authentication.** Via a predictable URL, the API, a
  sitemap, a search index or a preview token that never expires. This is the finding that ends
  careers and it is usually `critical`.
- **Preview and published differ.** Different renderer, different data source, or preview reading
  draft while published reads a cache.
- **Unpublish does not reach the reader.** Still served from CDN, still in the search index, still
  in the feed. "Removed" that is still readable is the same class as the leak above.
- **Required-field validation enforced in the editor and not in the API.** The API becomes the way
  to create invalid content, and the published surface breaks on it.
- **Schema change over existing content.** Removing or retyping a field with live documents either
  loses data or serves nulls to a renderer that cannot handle them.
- **Scheduled publish fires in the wrong timezone**, or not at all after a restart.
- **Media URL changes on re-upload**, breaking every existing reference.
- **Localisation fallback silently serves the wrong language** rather than reporting a gap.
- **Redirects lost on publish**, producing 404s for previously indexed URLs.
- **Rich-text sanitisation gap** — author-supplied HTML executing on the public surface.

## Defect classes to look for by name

| Class | What makes it this class |
|---|---|
| **Unpublished content exposure** | Draft, scheduled or unpublished content readable by an unauthenticated reader |
| **Preview/published divergence** | What the author approved is not what is served |
| **Unpublish incomplete** | Content removed in the CMS and still reachable on some surface |
| **Validation asymmetry** | Editor enforces what the API does not |
| **Schema migration data loss** | A content-model change that drops or corrupts existing field values |
| **Reference breakage** | Media or cross-content links broken by a rename, re-upload or delete |
| **Injection via authored content** | Author-supplied markup or script reaching the reader unsanitised |

## Evidence and severity

Evidence in this domain is **always fetched as the reader, unauthenticated, from a cold cache** —
never from the authoring session. An authenticated fetch bypasses exactly the permission and cache
layers under test, and a warm cache hides staleness. State the cache state with the result; a result
that does not say whether the cache was cold is not reproducible.

`shared/principles.md` §3: **the `Published` status is the product reporting on itself.** The oracle
is the public URL.

Severity: **unpublished-content exposure is `critical`** and inherits any embargo or regulatory
consequence on top. Unpublish-incomplete is `critical` where the content was removed for legal or
privacy reasons — ask why it was unpublished before grading it. Schema-migration data loss is
`critical`. Preview divergence is `major` unless it misleads an approval, which makes it worse.

For a coverage number, the denominator is **field types × publish states**, not pages: the defects
cluster in the unusual field type in the unusual state, and a per-page count hides that.

## Experience

The authoring question: **can an author tell, before publishing, exactly what a reader will see?**
If preview is approximate, that must be stated in the product, not discovered after a publish.

The reader question nobody tests: **what does a reader see for content that is mid-publish?** A
partial render is worse than a 404, and it is the state a build-hook CMS spends real seconds in.

Time to first success is **content visible on the public URL**, not content saved. Measure it
through the publish pipeline, cold, because that is the number an evaluator experiences.

## Domain gotchas

- **Preview tokens are credentials.** Check expiry and scope; a permanent preview link is public
  access with extra steps.
- **The search index and the sitemap are separate surfaces** with their own publish lifecycles, and
  both are routinely forgotten on unpublish.
- **Headless CMS API responses are cached independently of the page**, so an API read can be stale
  when the page is fresh and vice versa.
- **Never test publish semantics on a schema you did not create**, and create every field type: the
  defect is always in the type nobody used.
- **Clean up published content, media, preview tokens and invited authors** from minute one — a
  test article left published is live content on the user's real site.
