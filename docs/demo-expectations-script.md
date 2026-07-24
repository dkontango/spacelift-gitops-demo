# Demo expectations — what to show, and how (Spacelift GUI)

This is the click-by-click script for the parts of the Spacelift demo that must be
**shown in the Spacelift console**, not just committed to the repo. It exists
because two things were missing on the first pass:

1. **The Approval step wasn't visible.** An `approval-require-prod.rego` lived in
   the repo, but it had never been *created and attached in Spacelift*, so no
   approval gate ever appeared in the dashboard.
2. **Blocking vs non-blocking wasn't demonstrated in the GUI.** The workflow was
   driven mostly via git/API; the console is where a reviewer needs to *see* a
   run get held, blocked, approved, or denied.

Everything below was done live in the GUI on `dkontango.app.us.spacelift.io`.
Screenshots of each step are in [`docs/approval-demo/`](approval-demo/).

---

## What the demo is expected to show, end to end

| Beat | Where it shows | Blocking? |
|------|----------------|-----------|
| Push / PR triggers a Spacelift run | GitHub PR checks + Runs list | — |
| **Plan policy** denies a public S3 bucket | Run page: "denied by plan policy" | **Blocking** (run FAILS) |
| Plan policy **warns** on bucket delete | Run page: warning, run continues | Non-blocking |
| **Approval policy** holds a production run | Run page: "Pending approval", Approve/Reject | **Blocking** (stack held) |
| Reviewer **Approves** in the GUI | Run proceeds to apply | — |
| Reviewer **Rejects** in the GUI | Run is stopped | **Blocking** (run rejected) |
| Non-production stack | Run auto-approves, flows straight through | Non-blocking |

"Blocking" here has two distinct meanings that both must be shown:
- **Policy-blocking** — the outcome blocks the run (a Plan `deny`, an Approval
  `reject`, or an Approval gate that's still `undecided`).
- **Stack-blocking** — a tracked run holds the stack so no other tracked run can
  start until it finishes. Spacelift shows this as the banner *"This run is
  blocking the stack."*

---

## Part 1 — Create the Approval policy (GUI)

> Screenshot: [`01-policies-two.png`](approval-demo/01-policies-two.png),
> [`02-approval-policy-body.png`](approval-demo/02-approval-policy-body.png)

1. **Enforce Guardrails → Policies → Create policy.**
2. Name `approval-require-prod`; **Type = Approval policy**; Space `root`; Continue.
3. Paste the Rego body (this is the exact logic; Rego V1):

   ```rego
   package spacelift

   # Non-production: no manual approval required.
   approve if { not is_production }

   # Production: needs at least one approval and no rejections.
   approve if {
     input.stack.labels[_] == "production"
     count(input.reviews.current.approvals) >= 1
     count(input.reviews.current.rejections) == 0
   }

   # A single rejection stops the run outright.
   reject if { count(input.reviews.current.rejections) > 0 }

   is_production if { "production" in input.stack.labels }
   ```
4. **Create policy.** Policies list now shows **2 of 2** (Plan + Approval).

> The console reminds you: *"Approval policies only take effect once attached to a
> Stack or Module."* That attachment is Part 2 — and skipping it is exactly why
> the approval step was invisible the first time.

## Part 2 — Attach it to a stack + mark the stack production (GUI)

> Screenshot: [`03-stack-labels-production.png`](approval-demo/03-stack-labels-production.png),
> [`04-policy-attached-usedby.png`](approval-demo/04-policy-attached-usedby.png)

Two labels do the work — Spacelift's own "magic label" mechanism:

1. On the **stack** (Stacks → the stack → Settings → Stack details → Labels): add
   `production`. This is the value the policy's `is_production` checks.
2. On the **policy** (Policies → `approval-require-prod` → ⋯ Policy actions →
   Edit details → Labels): add `autoattach:production`. A policy labeled
   `autoattach:X` attaches to **every stack labeled `X`**.

   > Direction matters: `autoattach:<label>` goes on the **policy**, and the
   > matching plain `<label>` goes on the **stack**. (Putting
   > `autoattach:<policy-name>` on the stack does nothing — that was the first
   > wrong turn.)
3. Confirm on the policy's **Used by** tab: it now shows **1** — the stack.

## Part 3 — Show the approval gate hold the run (GUI)

> Screenshot: [`05-run-pending-approval.png`](approval-demo/05-run-pending-approval.png)

1. On the stack, click **Trigger** to start a tracked run.
2. When it finishes planning, the run stops at **Pending approval**. The run page
   shows, live:
   - Banner: **"This run is blocking the stack. … no other blocking run … can
     start until this run is completed."** ← stack-blocking.
   - **"Approval policies evaluated to UNDECIDED"** with a **Note** box and
     **Approve** / **Reject** buttons.
   - **"Policy approval-require-prod evaluated to Undecided"** — naming the exact
     policy doing the gating.
   - Keyboard shortcuts: `Ctrl+Alt+A` Approve, `Ctrl+Alt+Q` Reject.

## Part 4 — Approve, and show it proceed (GUI)

> Screenshot: [`06-run-approved-proceeds.png`](approval-demo/06-run-approved-proceeds.png)

1. (Optional) type an approval note.
2. Click **Approve**. The gate resolves — the run leaves Pending approval and
   moves to **Initializing → Planning → (confirm) → Applying**. The screenshot
   shows OpenTofu initializing right after approval.

**To show the reject path instead:** click **Reject** on a held run. The
Approval policy's `reject if { count(rejections) > 0 }` rule fires and the run is
**stopped** — the change never applies. (Reject is destructive to the run, so do
it on a throwaway trigger, not the one you intend to ship.)

## Part 5 — Show the non-blocking contrast

The same policy proves non-blocking by its first rule, `approve if { not
is_production }`:

- A stack **without** the `production` label auto-approves — runs flow straight
  through with **no** approval gate (non-blocking). The stack's own run history
  before the `production` label was added shows exactly this: tracked runs that
  applied without ever pausing for approval.
- Add the `production` label and the very next run is held (Part 3). Removing it
  returns the stack to auto-approve.

Contrast this with the **Plan policy** (`plan-block-public-s3`), which shows the
other axis of blocking:
- `deny` → the run **fails** (blocking) — the public-bucket PR goes red.
- `warn` (bucket delete) → the run **continues** with a warning (non-blocking).

---

## One-line summary for the narration

> "Guardrails come in two flavors here. A **Plan policy** *blocks* a bad change —
> the public-bucket PR fails in preview. An **Approval policy** *holds* a
> production change — the run pauses at 'Pending approval' and blocks the stack
> until a human clicks Approve (or Reject). Non-production stacks skip the gate
> and flow straight through. All of it is visible and driven right here in the
> Spacelift console."
