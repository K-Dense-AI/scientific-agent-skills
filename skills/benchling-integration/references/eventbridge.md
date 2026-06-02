# Benchling Events via AWS EventBridge

Real-time integrations that react to Benchling changes (entity registration, inventory transfers, workflow updates, and more).

**Official docs:**
- [Getting Started with Events](https://docs.benchling.com/docs/events-getting-started)
- [Events Reference (payloads and event types)](https://docs.benchling.com/docs/events-reference)
- [Events FAQs](https://docs.benchling.com/docs/events-faqs)
- [List Events API](https://benchling.com/api/reference#/Events/listEvents)

**Delivery methods:** Benchling supports **Webhooks** (recommended for new apps) and **AWS EventBridge** (customer-owned event bus). EventBridge payloads are **hydrated** (full v2 API objects in `detail`); webhooks use thinner payloads. See the getting-started guide for trade-offs.

---

## Setup checklist

1. **Tenant admin** enables Developer Platform access and opens [Event Subscriptions](https://your-tenant.benchling.com/event-subscriptions) (Feature settings → Developer Console → Events).
2. Create a subscription with:
   - AWS account ID and region
   - Event bus name (e.g. `benchling-integrations`)
   - Event types to receive (see [Events Reference](https://docs.benchling.com/docs/events-reference))
3. **Immediately** associate the partner event source with a new EventBridge bus in AWS (within ~12 days or the source expires).
4. Create EventBridge rules with `detail-type` / `detail` filters and targets (Lambda, SQS, SNS, CloudWatch Logs).
5. Grant invoke permissions (`AWS::Lambda::Permission`, queue policies, etc.).
6. Validate with a CloudWatch Logs rule on the bus `source`, then trigger a test action in Benchling.

Subscription statuses: `Pending` (needs bus association), `Active`, `Expired` (resubscribe in Benchling).

---

## EventBridge event envelope

All EventBridge deliveries share this top-level shape. The resource body lives under `detail` under a key that varies by event (for example `entry`, `assayRun`, `dnaSequence`).

```json
{
  "version": "0",
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "detail-type": "v2.dnaSequence.created",
  "source": "aws.partner/benchling.com/your-tenant/your-subscription-name",
  "account": "123456789012",
  "time": "2025-10-20T14:30:00.000000+00:00",
  "region": "us-west-2",
  "resources": [],
  "detail": {
    "id": "evt_abc123",
    "eventType": "v2.dnaSequence.created",
    "createdAt": "2025-10-20T14:30:00.000000+00:00",
    "deprecated": false,
    "excludedProperties": [],
    "schema": {
      "id": "ts_abc123",
      "name": "Plasmid"
    },
    "dnaSequence": {
      "id": "seq_xyz789",
      "name": "My Plasmid",
      "apiURL": "https://your-tenant.benchling.com/api/v2/dna-sequences/seq_xyz789"
    }
  }
}
```

**Naming:** `detail-type` and `detail.eventType` follow `<version>.<resource>.<action>` (for example `v2.request.created`, `v2.workflowTask.updated.status`).

**Do not treat payloads as authoritative.** Events may arrive late or out of order. Re-fetch objects with the SDK/API when you need current state.

**Oversized events (>256 KB):** Dropped fields appear in `detail.excludedProperties`. Use `apiURL` on the resource object to fetch the full record.

---

## Minimal EventBridge rule (CloudFormation)

Route `v2.request.created` events for a specific request schema to a Lambda:

```yaml
AWSTemplateFormatVersion: "2010-09-09"
Transform: AWS::Serverless-2016-10-31
Description: Benchling request.created → Lambda

Parameters:
  BenchlingEventBusName:
    Type: String
    Description: Partner event bus name from Benchling subscription

Resources:
  RequestCreatedRule:
    Type: AWS::Events::Rule
    Properties:
      Name: benchling-request-created
      EventBusName: !Ref BenchlingEventBusName
      State: ENABLED
      EventPattern:
        detail-type:
          - v2.request.created
        detail:
          schema:
            name:
              - Validated Request
      Targets:
        - Id: HandleRequestCreated
          Arn: !GetAtt HandleEventLambda.Arn

  HandleEventLambda:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.handler
      Runtime: python3.12
      CodeUri: src/
      Timeout: 30

  AllowEventBridgeInvoke:
    Type: AWS::Lambda::Permission
    Properties:
      Action: lambda:InvokeFunction
      FunctionName: !Ref HandleEventLambda
      Principal: events.amazonaws.com
      SourceArn: !GetAtt RequestCreatedRule.Arn
```

**Other filter examples** (from Benchling docs):

```json
{
  "detail-type": ["v2.assayRun.updated"],
  "detail": {
    "updates": ["my_field"]
  }
}
```

```json
{
  "detail-type": ["v2.entity.registered"],
  "detail": {
    "entity": {
      "schema": {
        "id": ["ts_MySchemaId"]
      }
    }
  }
}
```

---

## Lambda handler skeleton (Python)

```python
import json
import logging
import os

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Optional: re-fetch via SDK when payload may be stale or truncated
# from benchling_sdk.benchling import Benchling
# from benchling_sdk.auth.api_key_auth import ApiKeyAuth
#
# benchling = Benchling(
#     url=os.environ["BENCHLING_TENANT_URL"],
#     auth_method=ApiKeyAuth(os.environ["BENCHLING_API_KEY"]),
# )


def handler(event, context):
    """Process a single Benchling EventBridge delivery."""
    detail_type = event.get("detail-type")
    detail = event.get("detail") or {}

    logger.info(
        "benchling_event",
        extra={
            "detail_type": detail_type,
            "event_id": detail.get("id"),
            "benchling_event_type": detail.get("eventType"),
        },
    )

    if detail.get("deprecated"):
        logger.warning("deprecated_event_type: %s", detail_type)

    if detail.get("excludedProperties"):
        logger.warning(
            "truncated_payload excluded=%s", detail.get("excludedProperties")
        )

    if detail_type == "v2.dnaSequence.created":
        sequence = detail.get("dnaSequence") or {}
        sequence_id = sequence.get("id")
        if not sequence_id:
            raise ValueError("missing dnaSequence.id in event detail")
        # Prefer API lookup for authoritative data:
        # seq = benchling.dna_sequences.get_by_id(sequence_id)
        return {"status": "ok", "sequence_id": sequence_id}

    if detail_type == "v2.workflowTask.updated.status":
        task = detail.get("workflowTask") or {}
        return {"status": "ok", "task_id": task.get("id")}

    logger.info("no_handler_for_detail_type: %s", detail_type)
    return {"status": "ignored", "detail_type": detail_type}
```

For serverless timeouts: SDK `wait_for_task` defaults to 600s — keep Lambda timeouts and EventBridge retry/DLQ settings aligned with expected processing time.

---

## Validation steps

1. **Subscription active:** In Benchling, subscription status is `Active` (not `Pending` or `Expired`).
2. **Partner source associated:** In AWS EventBridge → Partner event sources, source is associated with your bus.
3. **Log all events:** Add a catch-all rule targeting a CloudWatch log group, filtering on your bus `source` (shown in Benchling subscription UI).
4. **Trigger a test event:** Create or update an object matching your rule filter (for example register a DNA sequence).
5. **Inspect logs:** Confirm `detail-type`, `detail.id`, and resource IDs match expectations.
6. **Re-fetch check:** Call the SDK/API for the resource ID and confirm it matches your integration logic.

---

## Recovering missed events

Benchling does **not** replay EventBridge deliveries. After an outage:

1. Get the affected time window from Benchling support.
2. List historical events with the [List Events API](https://benchling.com/api/reference#/Events/listEvents) (retained ~2 weeks).
3. Re-route recovered events through your own infrastructure.

SDK example (ISO 8601 timestamp; see API reference for filters):

```python
events = benchling.events.list(
    created_atgte="2025-10-20T00:00:00+00:00",
    event_types="v2.dnaSequence.created",
)

for page in events:
    for evt in page:
        print(evt.event_type, evt.id)
```

---

## EventBridge vs Webhooks

| | EventBridge | Webhooks |
|---|-------------|----------|
| Setup | Benchling console + AWS bus/rules | Benchling App configuration |
| Payload | Hydrated v2 API objects | Thin IDs + metadata |
| Filtering | EventBridge `EventPattern` | App code |
| Permissions | Not permissioned at delivery | Inherited from app |

For new Benchling Apps, Benchling recommends **webhooks** unless you already standardize on EventBridge in AWS. See [Getting Started with Webhooks](https://docs.benchling.com/docs/getting-started-with-webhooks).
