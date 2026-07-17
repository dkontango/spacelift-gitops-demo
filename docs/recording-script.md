# Recording Script — Spacelift GitOps Demo

Target length **~6–8 minutes**. Screen recording + narration. Each scene has a
one-line goal, what to show, and a narration cue. `⏸ CUT POINT` marks a clean
place to stop if a run is slow — record scenes as separate clips and stitch.

Before recording, dry-run the whole thing once (buckets created + destroyed) so
every run is warm and fast.

---

## Scene 0 — Intro & architecture (45s)

**Show:** the architecture diagram (README or a slide).
**Say:** "Spacelift orchestrates infrastructure-as-code with Git as the source
of truth. I'll show the full GitOps loop — branch, PR, preview, merge, deploy —
with OpenTofu against AWS. Two things I want to highlight: policy-as-code
guardrails, and keyless credentials — there are no AWS keys stored anywhere.
Our code lives in a self-hosted Forgejo, mirrored to GitHub, which is the VCS
Spacelift drives for the pull-request flow."

⏸ CUT POINT

## Scene 1 — The stacks & keyless creds (45s)

**Show:** the two stacks in Spacelift (dev, prod); open the dev stack → its
attached **AWS Cloud Integration (OIDC)**.
**Say:** "Two stacks, dev and prod, both OpenTofu. Notice the AWS integration is
OIDC — Spacelift assumes an IAM role at run time via STS. No access keys in the
stack, in a context, or in a vault. This is also the answer to the classic
'no valid credential sources' error — I've written that up separately."

⏸ CUT POINT

## Scene 2 — Branch + open a PR (60s)

**Show:** a terminal: branch off `main`, edit `stacks/dev/main.tf` (add a tag or
a second bucket), push; open the PR on GitHub.
**Say:** "I branch off main, make a change in the dev environment, and open a
pull request. This is where GitOps starts — the change is proposed, not yet
applied."

```bash
git checkout -b add-logs-bucket
# edit stacks/dev/main.tf
git commit -am "dev: add logs bucket"
git push -u origin add-logs-bucket
# open PR on GitHub
```

## Scene 3 — Spacelift previews the PR (60s)

**Show:** the PR's checks; the Spacelift **proposed run**; open it → the plan.
**Say:** "Spacelift automatically runs a plan against the pull request and posts
it back as a status check. Reviewers see exactly what will change before
anything is applied — a clean, auditable preview tied to the PR."

⏸ CUT POINT

## Scene 4 — Policy blocks a bad change (75s) — the bonus

**Show:** push a second commit that flips a bucket to `public = true`; the PR
re-runs; the **Plan policy DENIES** it with the message.
**Say:** "Now watch the guardrail. I try to make a bucket public. Our Plan
policy — Open Policy Agent, written in Rego — inspects the plan and denies it
right in the PR. The run fails with a clear reason. This is policy-as-code:
the rule lives in the repo, it's unit-tested, and it stops the mistake before
merge, not after." (Revert that commit to proceed.)

⏸ CUT POINT

## Scene 5 — Approve, merge, deploy (75s)

**Show:** approve + merge the (reverted-to-safe) PR; Spacelift's **tracked run**
on `main`; the apply; the bucket appearing in the AWS console.
**Say:** "I approve and merge. On merge to main, Spacelift runs a tracked run
and deploys. Here's the apply, and here's the bucket live in AWS — created with
temporary OIDC credentials. Git merged, infra changed, fully traceable."

## Scene 6 — Approval policy gates prod (60s) — the bonus

**Show:** trigger/promote a change on the **prod** stack; the run pauses on
**Unconfirmed / awaiting approval**; approve it; it proceeds.
**Say:** "Production is different. Our Approval policy requires a human
approval before prod applies — the run waits here. I approve, and only now does
it deploy. Same code as dev, stronger guardrail — that's how you promote safely."

⏸ CUT POINT

## Scene 7 — Forgejo via Raw Git (capability contrast) (45s)

**Show:** the Forgejo Raw Git stack; click **Sync**, then **Trigger**.
**Say:** "Spacelift can also point at our self-hosted Forgejo directly, through
Raw Git. But I want to be precise: Raw Git is a one-way connection — I sync and
trigger manually, there are no pull-request previews or merge-triggered deploys.
So for the full GitOps loop you saw earlier, you want a first-class VCS
integration like GitHub. Same code, different capability tier — good to know
when you're choosing how to connect."

⏸ CUT POINT

## Scene 8 — The next tier: drift & dependencies (45s)

**Show:** a slide or the docs; optionally the (greyed/paid) drift settings.
**Say:** "Two capabilities that complete the story on higher tiers: drift
detection, which catches out-of-band changes and reconciles them so Git stays
the source of truth; and stack dependencies, to promote changes dev-to-prod
with outputs flowing between stacks. The code for both ships in this repo."

## Scene 9 — Close (30s)

**Say:** "So: Git-driven previews on every PR, policy-as-code guardrails that
block mistakes and gate production, keyless OIDC credentials, and a clear path
to drift detection and multi-environment promotion as you scale. That's the
value Spacelift brings to a GitOps workflow."

---

### Pre-flight checklist

- [ ] Both stacks green, AWS integration attached to each.
- [ ] All three policies attached; prod stack labeled `production`.
- [ ] A safe baseline applied (private bucket exists) so diffs are small.
- [ ] Feature branch and the "make public" commit prepared/rehearsed.
- [ ] AWS console open to S3 in the right region.
- [ ] Recorder scoped to the browser + terminal; secrets not on screen.
