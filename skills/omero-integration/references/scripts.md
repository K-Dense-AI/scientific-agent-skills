# Bundled Helpers and OMERO.server Scripts

The local files in this skill's `scripts/` directory are client-side safety
helpers. They are not OMERO.server scripts and are never uploaded
automatically.

## Shared Safety Model

Every bundled executable:

- uses `argparse`;
- supports `--help` without OMERO installed;
- imports `omero` only after argument parsing and only for `--execute`;
- reads only named `OMERO_*` variables;
- never loads `.env`;
- never accepts or prints a password/session key;
- defaults to local validation or dry-run output;
- applies hard limits;
- refuses unsafe output collisions/symlinks;
- closes remote connections in `finally`.

Remote helpers require `--execute`. That flag authorizes a read-only
connection, not broader scope or mutation.

## Local Endpoint Validation

```bash
python -B scripts/validate_config.py
python -B scripts/validate_config.py --require-auth --json
```

By default it performs only local syntax checks. `--resolve-host` performs DNS
resolution but does not connect to an OMERO port.

Output reports which named variables are present and the authentication mode.
It never displays credential values.

Examples of failures:

- host contains `http://`, a path, whitespace, or shell syntax;
- port is not in `1..65535`;
- `OMERO_SECURE` is not a recognized boolean;
- only one of `OMERO_USER`/`OMERO_PASSWORD` is present;
- `--require-auth` is used without either a session key or complete password
  authentication.

## Read-Only Inventory

Dry run:

```bash
python -B scripts/inventory.py \
  --object-type Image \
  --limit 50 \
  --page-size 25
```

Execute after reviewing endpoint/group/scope:

```bash
python -B scripts/inventory.py \
  --object-type Image \
  --limit 50 \
  --page-size 25 \
  --group-id 42 \
  --execute \
  --output ./image-inventory.json
```

Properties:

- allowlisted object types only;
- overall cap at 1000 and page cap at 200;
- stable `obj.id` ordering request;
- one optional explicit group, never cross-group `-1`;
- object names redacted unless `--include-names`;
- JSON output written atomically with owner-only permissions;
- existing output refused unless `--overwrite`.

`limit_reached` means the requested cap was filled; it does not assert that
more server rows exist.

## Annotation and ROI Export

Dry run:

```bash
python -B scripts/export_image_metadata.py \
  --image-id 101 \
  --image-id 102 \
  --max-annotations-per-image 100 \
  --max-rois-per-image 100 \
  --max-shapes-per-roi 500 \
  --output ./selected-image-metadata.json
```

Execute:

```bash
python -B scripts/export_image_metadata.py \
  --image-id 101 \
  --image-id 102 \
  --group-id 42 \
  --execute \
  --output ./selected-image-metadata.json
```

Default redactions:

- annotation values
- owner names
- FileAnnotation filenames
- ROI/shape labels
- mask bytes

Optional inclusion flags are independent. The helper never retrieves pixels or
FileAnnotation bytes. It uses the currently documented `IRoi.findByImage`
pattern and records that `IRoi` is deprecated.

Because `findByImage` has no page argument, the ROI caps bound serialization
but may not bound server-side assembly. Do not run it on a known extreme image
without reviewing the ROI count or using a site-approved paginated API.

## Import/Export Planner

The planner is always local and has no `--execute`.

Import scan plan:

```bash
python -B scripts/plan_transfer.py import \
  --target Dataset:id:42 \
  --max-files 100 \
  --scan-depth 4 \
  ./explicit-input
```

It walks only explicit paths, does not follow directory symlinks, caps depth
and file count, and proposes `omero import -f` plus a future scoped import
command. It does not invoke either.

Per-image export plan:

```bash
python -B scripts/plan_transfer.py export \
  --format ome-tiff \
  --output-dir ./reviewed-existing-directory \
  Image:101 Image:102
```

It accepts explicit `Image:<id>` selectors only, proposes one output per image,
and reports collisions. Dataset iteration is intentionally excluded because
the official export mode is experimental and too easy to broaden.

Global `--output` and `--overwrite` arguments must precede the subcommand:

```bash
python -B scripts/plan_transfer.py \
  --output ./transfer-plan.json \
  import ./explicit-input
```

No proposed command includes `-w`, `--password`, `-k`, or a session value.

## Running Local Tests

No real OMERO server is needed:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  python -B -m unittest discover \
  -s skills/omero-integration/tests \
  -p "test_*.py"
```

The tests use temporary directories and fake gateway objects.

## OMERO.server Script Model

OMERO.server scripts are Python plugins registered with the Script Service.
Clients can launch them and receive typed outputs. Inputs often include an
explicit data type, object IDs, thresholds, or options.

A minimal structure:

```python
import omero
import omero.scripts as scripts
from omero.gateway import BlitzGateway
from omero.rtypes import rlong, rstring


def main():
    client = scripts.client(
        "Bounded_Image_Summary.py",
        "Returns IDs for an explicit bounded image list.",
        scripts.List(
            "Image_IDs",
            optional=False,
            description="Explicit image IDs (maximum enforced by script)",
        ).ofType(rlong(0)),
        namespaces=[omero.constants.namespaces.NSDYNAMIC],
        version="1.0",
    )

    try:
        inputs = client.getInputs(unwrap=True)
        image_ids = list(inputs["Image_IDs"])
        if not 1 <= len(image_ids) <= 25:
            raise ValueError("Image_IDs must contain 1..25 IDs")

        conn = BlitzGateway(client_obj=client)
        found = []
        for image_id in image_ids:
            image = conn.getObject("Image", image_id)
            if image is not None:
                found.append(image.getId())

        client.setOutput("Message", rstring(f"Found {len(found)} images"))
    finally:
        client.closeSession()


if __name__ == "__main__":
    main()
```

The script session is supplied by OMERO. Do not read a password or create a
second login inside a server script.

## Server-Script Safety

Even a server script that only reads can be expensive. It must enforce:

- maximum ID count;
- per-container child cap;
- plane/tile/byte limits;
- fixed group context;
- no cross-group fallback;
- no user-controlled HQL/code strings;
- bounded output size;
- `client.closeSession()` in `finally`.

For writes, additionally require an explicit “save” input or other reviewed
gate and document every created/linked object. A client-side confirmation is
not enough if the server script itself accepts unbounded inputs.

Do not use Python `eval()` or `exec()` for parameters. Do not interpolate
parameter text into HQL, filesystem paths, commands, or table conditions.

## Upload and Launch

Uploading registers executable code and is a mutation:

```bash
omero script upload ./Bounded_Image_Summary.py
omero script list
```

Before upload:

1. review source and dependencies;
2. validate against the target OMERO.py/server pairing;
3. confirm destination script path/category;
4. confirm administrator authorization;
5. record returned script ID/version.

Launching is also a remote operation:

```bash
omero script launch <SCRIPT_ID> Image_IDs=101,102
```

Use an already prompted session. Confirm the exact script ID, version, group,
input IDs, expected writes, and resource limits. Never launch based only on a
script display name.

## Outputs and Temporary Files

Server scripts may return strings, objects, images, or FileAnnotations. For a
file output:

- use a server-side temporary directory designed for scripts;
- generate a safe filename independent of user text;
- cap bytes;
- classify content before attaching;
- remove local temporary files in `finally`;
- close any table or raw store before closing the script session.

Do not place server paths, credentials, session IDs, or stack traces in client
outputs.

## Script Review Checklist

- Client helper or server plugin clearly identified
- Dry run and execution separated
- Credentials absent from arguments/output
- Object/group/file scope explicit
- Hard bounds at every expansion
- Output path safe and collision-aware
- Lazy optional imports for local helpers
- Stateful resources closed
- `IRoi`/other deprecated service dependencies documented
- No real-server test performed without explicit authorization
