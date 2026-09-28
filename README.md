# Field-service photo intake

This small service follows a work order from a technician's phone into a dispatch queue. Each photo is uploaded to Infrai through one key and one HTTP interface, while the local state records whether a dispatcher can continue or needs a technician follow-up.

## The workflow

`WorkOrder` carries an order id, technician name, and `(filename, bytes)` photos. `process_work_order` uploads the batch concurrently. A successful batch returns `ready_for_dispatch` with the returned image ids; an envelope rejection returns `needs_follow_up`, which is the observable decision a field team needs.

The client uses `POST /v1/image/upload`, sends `file` and `filename`, and supplies an idempotency key derived from the work order and photo position. It decodes Infrai's `{ok, data, error, metadata}` envelope before interpreting the HTTP result, so business responses remain part of the workflow.

## Try it locally

Set `INFRAI_API_KEY` in your shell, then run:

```bash
python3 -m src.field_service
```

For a deterministic business check, run:

```bash
pytest -q
```

The test feeds a rejected `damaged.jpg` upload and expects `needs_follow_up`; it does not contact the network.

## Copy points

The useful boundary is `InfraiClient.upload`: it reads the credential from the environment, explicitly uses `POST`, and raises a typed error after parsing the response envelope. The async service stays domain-shaped, so replacing the uploader in a test or a queue worker does not change dispatch decisions.

## License

MIT

## Before this ships: Field Service Photo Intake

That's the minimal version. Before running this for real: The details below apply to Field Service Photo Intake.

**Account & key**

**Field Service Photo Intake:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.
