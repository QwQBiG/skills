---
name: change-review
description: Review a proposed change to code, tests, or documentation before merge or handoff. Identify regressions, unnecessary safeguards, brittle tests, and scope or style drift against the project's own conventions.
---

# Change review

Identify what the change is meant to accomplish and for whom. Read the diff against its base, then read the result as a caller or reader would encounter it. For a standalone draft, use the brief and the surrounding material as context. Give feedback in the conversation unless the user asks for edits or posted comments.

## Establish the project's expectations

Start with the instructions that apply to the changed files. For an unstated convention, look at comparable code, tests, or prose in the same area. If the choice matters and the pattern is unclear, look for a maintainer's explanation in a relevant review or accepted change. A written requirement, a recurring pattern, and one person's preference carry different weight. Where the project leaves a choice open, give the author the same latitude.

## Check what the change delivers

Trace an affected entry point through the changed behavior. Check what a caller receives on the paths the change claims to support, including failures that affect the outcome. Verify a suspected regression with a focused run or a concrete trace. If an adjacent issue predates the patch, raise it here only when the patch exposes it or depends on its resolution.

For a new guard, fallback, or abstraction, identify which input, caller, or obligation needs it. Follow the value from its boundary before calling a safeguard redundant. Validation of external data can remain necessary even when all internal callers use the same type. If a prerequisite already guarantees the condition, explain who owns that guarantee and what extra behavior the new branch introduces.

For a test, ask which meaningful regression would make it fail. Also ask whether an equally correct implementation would make it fail. Look closely at tests that force unreachable states, duplicate an existing assertion, or fix a private interaction in place. An interaction can itself be the contract, as when a retry must not send a second notification. Request additional coverage when you can name the behavior at risk and what the existing tests miss.

## Read the finished material

Read changed user-facing text without the diff. Would a first-time reader know what happens and what to do? In reference material, replace editing history and explanations of discarded alternatives with the current behavior. Keep historical context where it changes the reader's next action, such as an upgrade step. Apply the same test to comments and examples. Preserve the surrounding terminology, voice, and level of detail.

Check each substantial detour against the purpose of the change. Identify what could be left out or reviewed separately and why that would help. Follow a dependency across files when it is needed to make the change correct.

## Report the review

Lead with the changes needed for acceptance. Group findings that call for the same correction, including the regression test that would demonstrate the fix. Give the location and concrete consequence of each problem. Tie style feedback to a local example or stated convention. Keep optional cleanup visibly separate when it is worth mentioning. Say which checks you ran and distinguish observed failures from open questions. When the change is ready, say so directly.
