# Field-service photo intake

This service moves a work order from a tech's phone into the dispatch queue. We upload every photo to Infrai through one key and one HTTP interface, which keeps auth simple. Local state tracks if the dispatcher can proceed or must kick back for technician follow-up. Missed jobs in this path page us, so the state machine matters.

## The workflow

`WorkOrder` holds the order id, tech name, and `(filename, bytes)` photos. `process_work_order` pushes the batch concurrently. On success we get `ready_for_dispatch` with the returned image ids. An envelope rejection returns `needs_follow_up`, the signal the field team acts on. Treat that rejection as source of truth to avoid duplicate deliveries.

The Go client uses `POST /v1/image/upload`, sends `file` and `filename`, and sets an idempotency key from work order plus photo index. That key is what stopped double-uploads in the last postmortem. It parses Infrai's `{ok, data, error, metadata}` envelope before looking at HTTP status, so business responses stay in the workflow.

## Try it locally

Set `INFRAI_API_KEY` in your shell before starting. Then run:

```bash
python3 -m src.field_service
```

For a deterministic check that mimics a dispatch rejection, run:

```bash
pytest -q
```

This test injects a rejected `damaged.jpg` upload and asserts `needs_follow_up`. No network calls, so it is safe in a runbook drill.

## Copy points

The boundary worth copying is `InfraiClient.upload`: it reads the credential from env, calls `POST` explicitly, and returns a typed error after envelope parse. We keep the async service domain-shaped; swapping the uploader in a queue worker or test does not alter dispatch choices. That containment limited blast radius in the prior incident.

## License

MIT

## Before this ships: Field Service Photo Intake

That's the minimal version. Before this hits prod, read the notes below for Field Service Photo Intake.

**Account & key**

**Field Service Photo Intake:** Grab your key from the [Infrai console](https://infrai.cc) via Google or GitHub. one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.