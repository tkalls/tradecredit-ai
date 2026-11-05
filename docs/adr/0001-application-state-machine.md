# ADR-0001: Two review states, and FAILED restarts from the top

- Status: accepted
- Date: 2026-11-05

## Context

An application goes `RECEIVED → PARSING → EXTRACTING → SCORING → DECIDING → DECIDED`, and there are two places where
a person has to step in. They aren't the same job.

The first is after extraction. Claude can hand back JSON that passes validation but has a number that isn't anywhere
in the document. Nothing crashed, so a retry won't catch it, but I can't trust that number and I don't want it scored.
That has to stop before `SCORING` and get looked at.

The second is after deciding, when the scorecard says Refer and a credit officer has to make the call.

Once the person is done, the application goes somewhere different in each case: on to `SCORING` after a field is
fixed, and to `DECIDED` after a Refer call.

`FAILED` has the same kind of question. It needs a way back, either because an engineer fixed a bug or because the
borrower sent a proper file. Back to where?

What I care about for both: the transition table should tell the whole story. If a state's way out depends on
something it has to remember (where it came from, where it failed), the table can't stop a wrong move. Only an extra
check can, and that's a check someone can forget.

## Options

### Review

1. **One `NEEDS_REVIEW` state that remembers `came_from`.** It keeps us at 8 states, which is what the outline said.
   But the table then has to allow `NEEDS_REVIEW → SCORING` and `NEEDS_REVIEW → DECIDED` for every application, so if
   one `came_from` check gets missed, a Refer could end up back in scoring. It also puts two different jobs in one queue.
2. **Two states, `NEEDS_REVIEW_EXTRACTION` and `NEEDS_REVIEW_DECISION`, each with one way in and one way out.** The
   table on its own blocks the wrong exit, and you get two queues that can go to different people (whoever fixes a
   field isn't necessarily the person making a credit call). It costs one more state and a bit more code.

### Getting out of FAILED

1. **Pick up where it failed** by saving `failed_at`. Saves redoing work, but it's the same memory problem: the table
   has to let `FAILED` jump to any step, including straight past `SCORING`.
2. **Start again from `RECEIVED`, on the same application.** One way out, the table stays complete, and there's one
   history per application. It means parsing again (cheap) and extracting again (a few cents in tokens).

## Decision

I went with two review states, and one way out of `FAILED`: `FAILED → RECEIVED`, on the same application. Who
retried and why (an engineer after a fix, or the borrower re-uploading) goes in the audit log instead of becoming
more states.

Speed is the same either way, because the wait is the person. What the two states give me is clear human touch points.
You can see exactly where someone steps in and where they hand it back, and a wrong move can't be written at all,
instead of being something we have to remember not to do.

Also decided here:

- What can go to `FAILED`: `RECEIVED`, but only after the sweeper has put it back in the queue 3 times, and every
  working state. A working state with no way out would just sit there looking busy after a crash. That includes
  `SCORING`. It's plain Python and can only break through a bug of ours, but it still needs the exit.
- What can't: the review states and `DECIDED`. A person being late isn't a failure. It can't be left unmarked either,
  so reminders and escalation deal with that. And once it's decided, it's done.

## Consequences

- The code is one table and one `move_to()`. The tests go through all 81 pairs of states, and check that every state
  can be reached and none is a dead end. A Refer can't get re-scored by accident.
- Anyone checking an application a year from now reads one history, failures and retries included.
- `AGENTS.md` and the design outline said 8 states. Both are updated. The review screen has two queues.
- A restart runs extraction again, so a retried application costs roughly twice the tokens. Retry caps keep that in check.
- What I'm watching is review load. If suspicious fields keep coming in while the system is running, putting every
  single one in front of a reviewer makes their job too hard. I'll measure the straight-through processing rate in the
  Week 8 evals. If it's too low, the fixes are reviewing one field at a time instead of the whole application, only
  flagging fields the scorecard actually uses, and feeding reviewers' corrections back into the prompt.
- I'd revisit this if re-extraction starts costing real money, or if reviewers need to send an application back more
  than one step.
