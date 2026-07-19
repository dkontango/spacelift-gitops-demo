# End-to-end live proof

A blow-by-blow of running the whole pipeline **live**, from a push to the on-prem
Forgejo repo all the way to a real S3 bucket in AWS, with the OPA guardrail
blocking a bad change in between. Every link was verified with hard evidence
(GitHub check states, the Spacelift run log, and `aws s3api` against the account).

## The chain, link by link

| # | Link | How it was proven | Result |
|---|------|-------------------|--------|
| 1 | **Forgejo → GitHub mirror** | Pushed a commit (`e728b7a`) to Forgejo **only**, then polled GitHub for the branch | Appeared on GitHub in **~5 s** (push-mirror, `sync_on_commit`) |
| 2 | **GitHub PR → Spacelift preview** | Opened PR #3; watched the commit's check-runs | Two checks posted: `spacelift/…-sandbox` and `spacelift/prime-apollo-45` |
| 3 | **OPA Plan policy DENY** | The PR flips the sandbox bucket public (`make_public=true`) | `…-sandbox` = **FAILURE** ("denied by plan policy: S3 public access is not allowed"); `prime-apollo-45` (no policy) = **success** |
| 4 | **Fix → pass → merge** | Pushed `make_public=false` to Forgejo → mirror → re-preview | `…-sandbox` check flipped **SUCCESS**; PR #3 merged |
| 5 | **Merge → tracked run → APPLY** | Merged a policy-permitted change (PR #4); the tracked run applied | Run **FINISHED**: `aws_s3_bucket.orbit_storage: Creation complete [id=orbit-storage-fc1735c38fa6eda4761e997d64]` |
| 6 | **Real AWS resource** | `aws s3api list-buckets` against account `…` | Bucket **`orbit-storage-fc1735c38fa6eda4761e997d64`** exists live |

The failing-then-passing contrast on the **same PR** is the headline: the
policy-bearing stack blocks the public-bucket change, the stack without the
policy does not.

## Details worth calling out

- **Checks API, not the legacy status API.** Spacelift posts PR results as GitHub
  **check-runs**, not commit *statuses*. Polling `/commits/<sha>/status` shows
  `pending` forever; poll `/commits/<sha>/check-runs` instead.

- **Push policy ignored a no-op merge.** PR #3 flipped the bucket public *and*
  back to private, so the squash-merge netted to **zero** file changes. Spacelift
  correctly reported *"the last commit was ignored because no files in the project
  root were affected"* and ran nothing — honest and correct. To demonstrate the
  apply leg we merged a **non-empty** change (a keeper bump, PR #4).

- **Tracked runs serialize per stack.** The sandbox stack had stale UNCONFIRMED
  tracked runs from an earlier session (autodeploy is off, so they sat at the
  Confirm gate). New runs queue behind them ("Blocked by … UNCONFIRMED"). Draining
  the backlog let the real apply proceed. This is a genuine operational detail:
  with autodeploy off, un-confirmed runs hold the queue.

- **Keyless throughout.** The apply used the AWS cloud integration (OIDC /
  AssumeRole) attached to the stack — no static keys in Spacelift. That the bucket
  was created is also proof the `no valid credential sources` issue is resolved on
  this stack (the integration is attached *to the stack*, not just the account).

## Reproduce

```bash
# push a policy-violating change from the canonical repo
git checkout -b demo/e2e-policy-block
sed -i 's/make_public.*default = false.*/make_public default = true/' stacks/sandbox/variables.tf
git commit -am "flip bucket public (expect DENY)"
git push forgejo demo/e2e-policy-block          # mirrors to GitHub
gh pr create --base main --head demo/e2e-policy-block

# watch the check go red (Checks API)
gh api repos/<owner>/<repo>/commits/<sha>/check-runs \
  --jq '.check_runs[] | .name + "=" + (.conclusion // "running")'

# push the fix, watch it pass, merge, and the tracked run applies
```

See [`docs/troubleshooting-case-study.md`](troubleshooting-case-study.md) for the
`no valid credential sources` error reproduced and resolved, and
[`docs/recording/`](recording/) for the 17-step movie of this whole flow.
