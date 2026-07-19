# Guide Site — Deployment & Documentation

The onboarding guide (`site/`) is published **two ways**, both driven from the
same source of truth (Forgejo, mirrored to GitHub):

| Target | URL | How |
|--------|-----|-----|
| **GitHub Pages** | https://dkontango.github.io/spacelift-gitops-demo/ | GitHub Actions workflow ([`.github/workflows/pages.yml`](../.github/workflows/pages.yml)) publishes `site/` on every push to `main`. Requires the repo to be **public**. HTTPS. |
| **Spacelift → S3** | the `website_endpoint` output of the `guide-site` stack | OpenTofu ([`stacks/guide-site/`](../stacks/guide-site)) provisions an S3 static-website bucket and uploads `site/`, deployed **by Spacelift itself**. HTTP (S3 website endpoint). |

Having both is intentional: the S3 route proves "the guide is deployed by the
GitOps pipeline it documents"; GitHub Pages gives a clean HTTPS URL now that the
repo is public.

---

## How the site is built

`site/` contains hand-authored HTML generated from the Markdown guides by
[`site/build.py`](../site/build.py) (a dependency-free Markdown → HTML converter
with a shared template, nav sidebar, code styling, and warning callouts).

To rebuild after editing the source docs:
```bash
python3 site/build.py       # regenerates site/*.html from docs/*.md + AGENTS.md
```
Source pages:
- `index.html` ← hand-written landing (in `build.py`)
- `by-hand.html` ← `docs/onboarding-by-hand.md`
- `with-ai.html` ← `docs/onboarding-with-ai.md`
- `agents.html` ← `AGENTS.md`
- `troubleshooting.html` ← `docs/troubleshooting-aws-credentials.md`

---

## GitHub Pages setup (what was done)

1. **Repo made public** (`gh api -X PATCH repos/<owner>/<repo> -f private=false`)
   — required for Pages on the free tier. A full secret scan of history + tree +
   screenshots was run first and came back clean (no keys/tokens/passwords).
2. **Pages enabled with the Actions build type**
   (`gh api -X POST repos/<owner>/<repo>/pages -f build_type=workflow`).
3. **The workflow** uploads `site/` as the Pages artifact and deploys it. It runs
   on pushes touching `site/**` (and can be run manually via `workflow_dispatch`).

Because Forgejo push-mirrors to GitHub, a push to Forgejo propagates to GitHub,
which triggers the Pages workflow — so the public site updates from the on-prem
canonical repo automatically.

---

## Spacelift → S3 setup (what was done)

1. `stacks/guide-site/` OpenTofu: an `aws_s3_bucket` + website configuration +
   a **public-read** bucket policy + `aws_s3_object` for each file in `site/`
   (content-types set by extension; `build.py` excluded from upload).
2. A Spacelift stack **`guide-site`** points at `stacks/guide-site` with the
   **AmazonS3FullAccess** integration (`aws-orbit-labs-role`) attached — the
   least-privilege role is scoped to `spacelift-gitops-demo-*` buckets and would
   deny the `spacelift-guide-site-*` bucket, so the FullAccess role is used here.
3. Triggering the stack plans + applies; the `website_endpoint` output is the
   live URL.

> **Note on the public-access policy:** a static-website bucket is legitimately
> public-read. The `plan-block-public-s3` guardrail is deliberately **not**
> attached to the `guide-site` stack — the guardrail protects *data* buckets;
> a website bucket is the sanctioned exception. That distinction (block public
> data buckets, allow public website buckets) is itself a good policy-design talking point.
