# Narration Script — `workflow.mp4`

A 24-second, 6-frame storyboard of the GitOps workflow with a live policy block,
driven from Forgejo through the GitHub mirror into Spacelift. Each frame is ~4s.
The `frames/` folder holds the source PNGs; `workflow.mp4` is the stitched movie.
Read the narration below over each frame (pause the video on a frame while you
talk, or re-time the frames to your pace).

Everything shown is **real and verified live** — the account is `dkontango`
(us.spacelift.io), the AWS account is `193456333226`, and the policy genuinely
failed then passed a Spacelift run.

---

## Frame 01 — Title / architecture
`frames/01-title-architecture.png`

> "Here's the pipeline. Our canonical source of truth is a self-hosted **Forgejo**
> on-prem. Forgejo **push-mirrors** to GitHub, which is the VCS **Spacelift**
> watches. Spacelift runs **OpenTofu** and evaluates **OPA policies**, and
> authenticates to **AWS** with **keyless OIDC** — no static credentials stored
> anywhere. The key point: I only ever push to Forgejo; everything downstream is
> automatic."

## Frame 02 — Policy attached to the stack
`frames/02-policy-attached-to-stack.png`

> "First, the guardrail. On the sandbox stack I've attached one **Plan policy**,
> `plan-block-public-s3`. Plan policies run against the OpenTofu plan on every
> proposed run — before anything is applied. This is policy-as-code: the rule
> lives in the repo, it's version-controlled and unit-tested, and it's attached
> here declaratively."

## Frame 03 — The policy body (Rego)
`frames/03-policy-body-rego.png`

> "This is the policy itself, written in **Rego**. It inspects the plan's
> resource changes and **denies** any change that disables an S3 bucket's
> public-access-block — in other words, any change that would make a bucket
> public. It also warns on bucket deletion. Simple, readable, and it returns a
> clear message the developer will see."

## Frame 04 — The bad PR, blocked on GitHub
`frames/04-github-pr-checks-policy-fail.png`

> "Now the workflow. I pushed a branch to **Forgejo** that flips the bucket
> public; the mirror carried it to GitHub, and I opened this pull request.
> Spacelift previewed it as a status check. Look at the checks:
> **one failing, one successful.** The stack that has the policy attached —
> `spacelift-gitops-demo-sandbox` — **failed** the check and blocked the merge.
> The other stack, without the policy, planned fine. Same code, same PR — the
> guardrail is the difference."

## Frame 05 — The policy denial, in Spacelift
`frames/05-policy-denies-public-bucket.png`

> "Here's *why* it failed, in Spacelift. The run is FAILED, and the policy
> message says it plainly: **'S3 public access is not allowed:
> aws_s3_bucket_public_access_block.orbit_storage disables public-access-block
> protections. Set make_public = false.'** The log reads *'Denied by policy …
> Failing the run as per plan policy.'* The risky change was caught in the
> preview, before merge — exactly where you want it."

## Frame 06 — Fixed PR passes
`frames/06-github-pr-checks-pass-after-fix.png`

> "I pushed the fix to Forgejo — keep the bucket private — the mirror propagated
> it, Spacelift re-ran the PR, and now **the check passes**. The developer got
> immediate, specific feedback, corrected the change, and the PR is green and
> mergeable. On merge to the default branch, Spacelift deploys — keylessly, via
> OIDC. That's the full GitOps loop with a policy guardrail doing its job."

---

## Optional closing (no frame)

> "To recap the value: Git is the single source of truth — on-prem Forgejo,
> mirrored to GitHub. Spacelift previews every PR, policy-as-code blocks risky
> changes before they merge, and credentials are keyless. And this whole thing
> was set up by directing an AI agent — which introduced its own pitfalls, and
> those are worth talking about too."

## Re-timing the movie

The frames are 4s each. To change pacing, re-encode from `frames/`:

```bash
cd docs/recording
ffmpeg -y -framerate 1/6 -pattern_type glob -i "frames/*.png" \
  -c:v libx264 -r 30 -pix_fmt yuv420p \
  -vf "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x0b1020" \
  workflow.mp4
```
(`1/6` = 6 seconds per frame; adjust to taste.)
