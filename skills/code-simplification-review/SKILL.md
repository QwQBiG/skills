---
name: code-simplification-review
description: Review existing code for refactoring opportunities. Trace callers and state changes to find redundant bookkeeping, misplaced responsibilities, and APIs that force callers to coordinate multiple steps.
---

# Code simplification review

When asked to find simplifications, inspect the code read-only and report findings in the conversation. When asked to implement a change, work within the requested scope and verify the result through the original entry point.

## Trace the maintenance cost

Start with the requested revision or module. Follow a real caller through a state change. Who writes the value, who reads it, and who else has to act when it changes? On a follow-up review, check earlier decisions and intervening changes. If a branch looks redundant, look for the test or commit that explains why it exists.

When several callers must invoke the same two methods in order, identify which component has enough information to complete the operation. Would moving it there let every caller drop a step? Consider a change across modules when it removes that obligation. Check where the cost would move. For example, deriving a frequently read count by scanning a collection makes each read more expensive.

Before merging two values, check whether any supported operation can make them diverge. In a CI system, a branch view shows the latest commit, while a build retry checks out the commit recorded for that run. Advance the branch, then retry the old build. The commit it checks out tells you whether the proposed change preserves the retry contract.

## Report findings a maintainer can verify

Identify the scope, including the commit and any uncommitted changes reviewed. Lead with the finding that would remove the most maintenance work. For each finding, cite the code and its caller, explain what someone has to keep in sync today, and name the behavior that would verify the change. Omit cosmetic rewrites. A review can end with no findings.

For an internal cleanup, identify the behavior callers rely on. If a redesign changes a public API, data format, or call order, explain who would need to adapt and how they could migrate. For a suspected bug, give the trigger and say whether you reproduced it. A constructed example can demonstrate a failure mode. Claims about affected callers need evidence from actual use.

Distinguish checks you ran from checks you recommend. When implementing a finding, exercise the edge case that justified the original design.
