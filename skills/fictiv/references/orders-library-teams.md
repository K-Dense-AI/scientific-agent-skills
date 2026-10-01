# After the order: tracking, documents, changes, returns, reorders, Library, Teams, account

The order-detail pages here come from Fictiv's Help Center (Sep 2026). The test account had no orders, so these screens weren't seen live. Match on the label text and adapt if the UI differs.

## Contents
1. Order lifecycle
2. Finding and tracking orders
3. Documents: receipts, invoices, inspection reports, photos
4. Changing or cancelling an order
5. Quality problems, returns and remakes
6. Reordering
7. Parts Library and revisions
8. Mold Library (tooling)
9. Teams and workspaces
10. Account settings
11. Contacts: who to ask for what

---

## 1. Order lifecycle

1. **Production Assignment:** "smart sourcing" picks a manufacturing partner. There is no bidding.
2. **Manufacturing.**
3. **Partner Inspection:** at least ISO 2768-m with hand metrology, plus drawing callouts. The partner uploads photos.
4. **Quality Review:** Fictiv QC reviews photos and data remotely.
5. **Packing & Shipping:** a tracking number is posted.

Lead time counts business days from the order date. Orders placed after the daily cutoff start the next business day. Holidays (US, plus Chinese holidays for overseas production) are excluded.

## 2. Finding and tracking orders

- Go to **Orders** (`/orders`). The **Search** box matches order name, part name or PO number.
  - Search terms must be **contiguous substrings**: "1010_back" matches, "1010 back plate" may not.
  - Colleagues' orders only appear if they've been shared into a Teams workspace.
- **View order detail** shows the stage tracker, estimated ship and delivery dates, and your program manager. After shipment it shows the carrier and tracking number, with a **Track Shipment** tab.
- To report status to the user, open the order detail and give: current stage, ship-by date, tracking number and carrier, and any hold or message from Fictiv. `get_page_text` is usually enough.

## 3. Documents

On the order detail page:
- **Download Order confirmation:** the receipt, with part specs, unit and total cost and payment.
- **Invoice:** PO orders are invoiced by AR after the last line ships.
- **Inspection report data** (top of the order): the standard inspection report, CoC and material certs if ordered, and high-resolution photos. Per part there is **View inspection** or "Part Status → View Quality Docs".
- Drawings (under the part name), the 3D viewer, DFM feedback and thread callouts.

Downloading saves a file to the user's machine, so ask first and say which file(s).

## 4. Changing or cancelling an order

- **Terms of Service:** orders can't be cancelled once placed.
- **In practice:**
  - An afternoon order placed before the cutoff gets about a 5–10 minute window.
  - An evening or early-morning order can be cancelled by contacting Fictiv before about 10 am PT.
  - Once production starts, cancellation is difficult and may carry fees.
- **How:** contact the **program manager** named on the order, or hello@fictiv.com, *immediately*. Say the order number and what you want.
- **Design, material or quantity changes** usually mean cancel and re-order. There is an **ECO** (engineering change order) process, usually with fees and lead-time impact. Fictiv doesn't guarantee to honor CAD or PDF updates sent after ordering.
- **Address or shipping method** can be changed before the ship date via the PM or hello@fictiv.com.

Sending these messages is outward-facing, so draft the message and get the user's OK before sending.

## 5. Quality problems, returns, remakes

- **Report non-conformances within 72 hours of delivery.** After that, all sales are deemed final.
- **What counts:** anything measurable that misses the requirements given at order time. Examples: a dimension out of tolerance, missing threads, wrong color, sink, a wrong finish.
- **Not covered:** requirements that were never specified. Examples: a tolerance tighter than ISO 2768-m with no drawing, or threads not configured.
- **How to report:** contact the order's program manager with the order number, part, photos, measurements vs. requirements, and quantity affected. Fictiv then offers **rework** (ship parts back) or **remanufacture**. Fictiv pays if the fault is theirs.
- Help the user by assembling the evidence (photos, measurements, the relevant drawing callout or config line from the order) into a clear, factual message.

## 6. Reordering

- **From an order:** Orders → the order → **Reorder**, and optionally pick parts. You get a fully configured quote ready to check out. To change anything (quantity, finish, lead time), click **Unlock quote**. This re-prices at current rates and may re-run DFM.
- **From the Library:** tick parts, then **Add to quote** (a new or existing quote). This uses the latest revision by default. Or open the part and "Add to quote" on a specific revision.
- **From the new-quote page:** "+ New quote from Parts Library".
- Then continue with the normal quote review and checkout, approval gate included.

## 7. Parts Library and revisions

- `/library/parts`. It fills automatically with purchased parts and is empty until the first order.
  - Search by part number, file name, order name, mold name or PO. Filter by purchase date or purchaser.
- **Part details** has an editable part number (defaults to the filename), a description, and tabs **Purchased Revisions**, **Active Quotes** and **Part Activity**. An orange icon means the part wasn't bought on the platform, so its requirements may be incomplete.
- **New revision:** in a quote, open the row's "…" menu and choose **Upload part revision**. On upload, duplicate detection offers "Use existing revision from Library", "Upload as a new revision" or "Track as a new part number". **View revision history** shows prior revisions.
- **Share part** adds the part to workspaces. Sharing an order shares all its parts.

## 8. Mold Library (tooling)

- Library → **Molds** tab → **Reorder parts** or **Request modification**.
  - Add notes under "Reorder requirements".
  - Change material, color, finish or drawing under "Modify part".
  - For family molds, "Exclude from production" leaves a cavity's part out.
- There's no instant checkout. A Fictiv team member follows up within 1–3 business days by email.
- Only one active reorder or modification per mold at a time. Molds still being built can't be reordered.
- Customer-owned molds are stored free for 2 years after the last order, then $500/year or scrapped with approval.

## 9. Teams and workspaces

- **Fictiv Teams** is a company account. A user can belong to only one. It unlocks team workspaces, PO terms, Preferred Pricing, the Lead Time Optimizer, Spend Analytics and Punchout.
- **Workspaces:**
  - Create one with "Create a workspace" in the left nav, or with "+ Create a new team".
  - "Add team members" is for existing Teams users only.
  - A quote or order lives in one workspace at a time. Add it with **Share → Team workspace → Add to workspace**, or with "Add to…" on an order.
  - Everything in a workspace is visible to its members, and any member can check out a team quote.
  - A workspace that contains quotes or orders can't be deleted.
- **Lead Time Optimizer** (Teams accounts): the blue "Optimize lead time" banner. Enter a target date and it proposes removing secondary processes or certs, updating threads, drawing or quantity. Exit with "Save and exit Lead Time Optimizer".
- **Punchout** (Ariba, Coupa, Dynamics 365) is set up with the account team. From inside the P2P system, "Send to Punchout" moves a *fully configured instant* quote into the requisition cart. Manual or RFQ quotes can't go through Punchout.
- Inviting people ("Invite to Fictiv", workspace invites) sends emails, so confirm first.

## 10. Account settings (`/pages/my-account`)

- Name and phone (Edit), email (verified date), password (Edit). "Delete this account" is irreversible: never do it without an explicit, unambiguous request, and even then have the user click it.
- **Financial permissions:** "Pay with PO · Apply for payment terms", and "Tax-exempt (reseller) · Get Tax-exempt permissions".
- **Payment methods:** saved cards (via Stripe) and "Add new card". The user enters the card; see checkout-and-payment.md §4.
- **Personal vs. company email:**
  - A personal email (Gmail and similar) only gets CNC, 3D printing and sheet metal.
  - A **verified company email** unlocks injection molding, urethane casting, die casting, compression molding, PO terms, Teams and Materials.AI.
  - If those options are missing, that's why.

## 11. Contacts: who to ask for what

| Need | Contact |
|---|---|
| Quote, DFM, material or process question on a specific part | **Chat with us** in the part viewer (Manufacturability feedback tab), or the "Contact us" link in the configuration panel |
| Pricing, FAI, certs, special tolerances, large parts, international | Your **account manager** (on the home page and quote page: name, email, phone, "Book a meeting"), or sales@fictiv.com |
| Order changes, cancellation, RMA / quality issue | The **program manager** on the order, or hello@fictiv.com |
| General help, tracking | help@fictiv.com |
| PO / credit terms / invoices | ar@fictiv.com |
| Export-controlled (non-EAR99) projects | Fictiv's off-platform Export-Controlled Project Request Form. Never upload ITAR data. |
| NDA | fictiv.com/contact-us (NDA form) |
| Phone | (415) 580-2509 |

Any email, chat message, meeting booking or form you send on the user's behalf needs their OK on the actual content first.
