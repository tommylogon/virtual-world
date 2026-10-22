---
type: task
status: todo
area: characters
priority: high
horizon: next
effort: L
wiki: "[[Character Pursuits]]"
related: [task-813, task-714]
---

# task-896: Complete the obligation offer and response loop

**Filed:** 2026-10-21
**Related:** task-813, task-714

<!-- deps:start -->
**Related:** [[task-813-mosiac-obligations-the-missing-letter-s-data]], [[task-714-character-mind-panel-connect-memories-motives-and-current-pursuits]]
<!-- deps:end -->

## What

Complete the obligation exchange from offer through response and fulfillment. A human author must be able to create an offer in the browser, and an agent must be able to offer an obligation to another agent through an explicit in-world action. The recipient owns the offered record on its Player. Keep obligations as character-private mind data; do not add mission or obligation graph nodes.

## Why

Task 813 added the record, display, and response handler, but the offer helper has no production caller. The Mind panel displays existing obligations without creating or answering them. An agent can see obligation text in its MOSIAC context, but the prompt does not instruct it how to decide or respond. A person cannot use the feature end to end without manually seeding character data.

## How

1. Keep Player.obligations as the persisted source of truth and reuse the existing goal, action, name-resolution, and serialization systems.
2. Add a Mind-panel authoring flow for a human editor to create and revise an offer, including its request, recipient, issuer, due condition, reward, and any fulfillment criteria supported by existing goal resolution.
3. Add a discoverable targeted in-world offer action. The issuing character addresses a recipient character; the offer is recorded on the recipient's Player with the issuer's stable node ID. Do not turn arbitrary speech into an accepted obligation.
4. Give the recipient visible Accept, Decline, and Counteroffer or Clarify choices. Human-controlled recipients use the Mind panel or command surface. Agent prompts must describe pending offers and the available responses, and agents must decide from their character's context rather than auto-accept.
5. Give every offer a stable unique ID independent of its charge text. Keep legacy records readable, resolving legacy issuer names without losing their displayed provenance.
6. Define and enforce the lifecycle, including unanswered expiry versus accepted-but-overdue, refusal, revision, completion, and abandonment. Reconcile the linked goal and obligation so a reached goal completes its obligation exactly once. If fulfillment cannot be derived from existing goal conditions, keep completion explicit and show that clearly in the UI.
7. Record offer, response, revision, and resolution in the event stream. Add authored scenario content with two agent characters to exercise an agent-to-agent offer and response in the browser.

## Browser UI and intended live verification

Intended UI home: Character Inspector > Mind tab for authoring and responding; the live character interaction and event stream for agent-to-agent offers.

Current availability: Not complete end to end. Mind currently displays obligations only. The response command exists, but offer_obligation has no production caller and there is no browser offer or response control.

Live steps when available:
1. Load the authored obligation-exchange scenario. Select the recipient in the character inspector, open Mind, and create an offer with an issuer, request, and deadline.
   - expected: The recipient Mind panel shows the offer as offered, with its issuer and terms.
   - observed: Pending implementation.
2. Run the scene so Agent A uses the in-world offer action to address Agent B. Inspect the event stream and Agent B's Mind panel.
   - expected: The stream records the offer, and only Agent B receives an offered obligation linked to Agent A.
   - observed: Pending implementation.
3. As the recipient, decline one offer and accept a separate offer. Complete the authored fulfillment goal for the accepted offer.
   - expected: Decline creates no goal. Accept creates one linked goal. Completing it resolves the obligation once, and the panels and event stream agree.
   - observed: Pending implementation.
4. Counter or revise an offer, let one unanswered offer expire, and let one accepted offer pass its due condition. Save, reload, and inspect both characters.
   - expected: Lifecycle outcomes remain distinct and visible; issuer identity, terms, statuses, and goal links survive reload without duplicate offers.
   - observed: Pending implementation.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Use the authored two-agent scenario to offer, decline, accept, and complete a mission in the browser.
   - expected: The recipient sees the offer and chooses a response; the linked goal and final obligation state are visible in the UI and event stream.
   - observed: Pending implementation.
2. Repeat the same charge from a second issuer and submit the same acceptance twice.
   - expected: Distinct offers remain distinct, and repeated acceptance creates no duplicate goal or history transition.
   - observed: Pending implementation.
3. Run targeted tests for offer routing, recipient ownership, lifecycle transitions, goal synchronization, serialization, and agent prompt/action wiring.
   - expected: The tests prove the mechanism and that Agent A cannot write directly into Agent B's state without using the offer action.
   - observed: Pending implementation.

## Acceptance

- [ ] A human can create, revise, accept, decline, and inspect an obligation through the browser without editing raw character data.
- [ ] An agent can explicitly offer an obligation to another agent in-world; the recipient owns the offered record and the issuer is identified by stable node ID.
- [ ] Agent prompts expose the offer and response choices, and the recipient chooses whether to accept, decline, clarify, or counteroffer.
- [ ] Unique offer identity prevents same-text requests from different issuers from overwriting each other; repeated responses are idempotent.
- [ ] The obligation-to-goal relationship has defined lifecycle semantics for acceptance, deadlines, completion, and abandonment.
- [ ] Event history and scenario save/load preserve offer provenance, terms, responses, and resolution.
- [ ] Authored two-agent scenario content exercises the complete exchange in the browser.
- [ ] No mission or obligation graph node is introduced.

## Files

- `engine/goals.py`
- `engine/action_verbs.py`
- `engine/action_tiers.py`
- `routes/action_handlers.py`
- `routes/player_ops.py`
- `player.py`
- `engine/serialization.py`
- `engine/mosiac.py`
- `static/js/inspector/mind-view.ts`
- `static/js/agent/prompt-builder/character-state.ts`
- `data or scenario fixture for the authored two-agent exchange`
- `tests/test_goals.py`
- `tests for agent action and prompt wiring`
