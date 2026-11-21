# Independent architecture atlas review

Review the atlas against the supplied repository revision or working tree. Your reader is a maintainer tracing a real request or diagnosing a failure for the first time. Give specific, evidence-backed findings and the smallest correction that would make the atlas trustworthy.

## Walk the system

1. Record the revision, relevant local changes, atlas inputs and published outputs you reviewed. Establish the artifact's promised scope and any audience or scenario the requester explicitly named.
2. Start at real entry points. Inspect launch configuration, public APIs, route registrations, schedulers, CLI dispatch or build targets as appropriate. Identify what runs by default, what is optional and what the caller or host supplies.
3. Select a core user journey. Trace it forward from trigger to observable result, then trace a durable effect back to its caller. For each boundary, verify who initiates it, what travels across it, which implementation receives it and what the caller learns on return. Follow indirect calls through registration or injection. Record unresolved dispatch explicitly.
4. Stop at each durable change or external side effect. Identify the transaction, ownership or authorization check, deduplication key and the moment a receipt, acknowledgement or user-visible result becomes true. Trace one meaningful interruption between two such moments. Describe how another attempt discovers what already happened.
5. Follow alternate entry paths and recovery where they change the outcome. Examples include another input modality, a direct command, an expired state pointer, a disabled dependency, a lost lease or an ambiguous external response. Choose cases supported by this system.
6. Compare these traces with the diagrams, catalog and narrative. Inspect arrow direction, branches, conditions, payloads, return paths, source targets and stated guarantees. Read representative tests to determine which boundaries use fixtures, fakes or real infrastructure. Treat imports, names and test titles as leads requiring inspection.
7. Where an interactive artifact is available, exercise the published artifact. Follow a scenario through its last step, switch views, inspect several links, and check one source location after navigation. Record the browser, artifact and exact controls exercised. When dynamic execution is unavailable, describe the remaining uncertainty.

## Report

Prioritize errors that could lead a maintainer to the wrong process, data owner, recovery action or verification claim. Separate factual contradictions from omissions and optional expansions. A compact overview may legitimately collapse steps if it preserves ownership, payload and completion semantics.

For each finding give:

- **Impact and classification.** Name the journey or decision affected. Explain what a reader could conclude incorrectly.
- **Atlas evidence.** Cite the view, node, edge or catalog row and its source location.
- **Implementation evidence.** Cite repository-relative paths and stable symbols or configuration keys for both sides of the handoff. Include the test assertion, recorded command or observed result where available.
- **Correction and verification.** Specify the edge, statement or source link to change, and a concrete check that would establish the correction.

Close with the verification boundary. Distinguish source inspection, test definitions read, checks actually executed and live observations. Name any material uncertainty and the evidence needed to resolve it. If there are no material findings, identify the journeys sampled and the limits of that conclusion.
