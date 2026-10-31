# Fictiv web app: UI map and browser-automation notes

Retained from an authenticated September 2026 app snapshot; not revalidated in an authenticated session during the 2026-09-30 public-documentation review. Browser URLs below are UI routes, not REST endpoints or a supported API contract. Fictiv ships UI changes often, so treat labels as hints rather than guarantees. If something has moved, use `find`/`read_page` with the label text rather than fixed coordinates.

## Contents
1. URL routes
2. Global layout
3. New-quote page (process picker + upload)
4. Quote page
5. Part modal (Configuration / Threads / Manufacturability feedback)
6. Checkout page
7. Account, Library, Orders
8. Automation techniques that work (and ones that don't)

---

## 1. URL routes

| Page | URL |
|---|---|
| Home / dashboard | `https://app.fictiv.com/home` |
| Quotes list | `/pages/quotes` |
| New quote (process picker + upload) | `/pages/quotes/upload` (adds `?process=cnc` once a process card is clicked) |
| Quote detail | `/pages/quotes/<quoteId>` |
| Part modal, config tab | `/pages/quotes/<quoteId>/part/<partId>/configuration` |
| Part modal, threads tab | `/pages/quotes/<quoteId>/part/<partId>/threads` |
| Part modal, DFM tab | `/pages/quotes/<quoteId>/part/<partId>/feedback` |
| Checkout for a quote | `/pages/orders/quote/<quoteId>` |
| Orders list | `/orders` |
| Parts Library | `/library/parts` (tabs: Parts, Molds) |
| My Account | `/pages/my-account` |
| Help Center | `https://www.fictiv.com/help` (`/help-center` and the old `help.fictiv.com` article links redirect here) |
| DFM tool Atlas | `https://atlas.fictiv.com` (separate app; public upload/login page observed in documentation extraction) |

The recorded quote/part IDs were UUIDs. Verify navigation in the current session before relying on these deep links; an HTTP 200 or login redirect does not validate an authenticated route. Re-opening a quote URL throws away unsaved edits in an open part modal, which is a clean way to back out of a half-finished edit.

## 2. Global layout

- **Left nav:** Home, Library, *My workspace* → Quotes, Orders, *Team workspaces* → (teams), "Create a workspace".
- **Top right:** "Invite to Fictiv", "Learn about TEAMS", and an avatar menu with **My Account**, **Help & Resources**, **Log out** (shows the signed-in email).
- **Home page cards:** "Start a new quote", "View your Library", a **dedicated account manager** card (name, email, phone, "Book a meeting"), an onboarding checklist, and "Helpful resources" (FAQ, capabilities, Materials.AI, Atlas DFM, sample part download, tariff notes).
- **Survey and feedback widgets** ("How would you rate your experience…") show up in page text. Ignore them.

## 3. New-quote page: `/pages/quotes/upload`

**Step 1, "Select a process".** Pick one of the cards:
- *Instant quoting available:* **CNC Machining**, **3D Printing**, **Urethane Casting**, **Sheet Metal**
- *Quote available within 48 hours:* **Injection Molding**, **Compression Molding**, **Die Casting**

Each card shows sub-processes, material count and "As fast as N days". The radio inputs have values `cnc, 3dp, rtv, sheet, im, cmprmold, diecast`.

> ⚠️ **Click the card itself** (its title text or body), not the hidden radio input. Clicking the radio by ref left it unchecked and the upload zone stayed greyed out. After a correct click the URL gains `?process=<value>` and the right pane turns active.

**Step 2, "Upload your files".** Drag-and-drop zone, "Select files or folder to upload", and "See all supported file types" (a modal with "Most Processes" and "3D Printing" tabs).
- The upload control is a hidden `<input type=file multiple>`. **Upload by setting files on that input** (e.g. the browser tool's file-upload action with the input's ref). Don't click the button, because a native file picker is invisible to you.
- Read the current export-control declaration. The [project-submission guide](https://www.fictiv.com/help/getting-a-quote/how-to-submit-an-export-controlled-project) permits EAR99/9E991 self-serve, excludes ITAR, and routes other ECCNs through review; do not generalize old upload-banner wording to every EAR classification.
- "+ New quote from Parts Library" (top right) builds a quote from previously ordered parts.

After an upload the app **creates the quote automatically** and redirects to `/pages/quotes/<id>`. The quote is named `<lastname>_<MMDDYY>`, which you can rename with the pencil icon. A first-time "Upload complete! Next steps…" tour modal may appear. Dismiss it with **"No, I've got this"**.

## 4. Quote page: `/pages/quotes/<quoteId>`

Top to bottom:

1. **Header:** "Save and back", the quote name with a ✏️ rename icon, "Last modified", **View activity log** (a timestamped list of who configured, classified or created what), **Share** and **Delete**.
2. **Banner.** It changes with the quote's state (the `banner` field in `scripts/quote_state.js`):
   - `Required: Are these parts for prototype or commercial use?` shows two cards, **Prototype** and **Commercial**. **Pricing and lead times stay hidden until one is chosen.**
   - `Configure parts to receive lead times` means at least one part is unconfigured.
   - `Determining available lead times` is a transient loading state.
   - `Select regional preference` is the lead-time picker (below). A small Prototype/Commercial dropdown sits at its top right.
3. **Lead-time picker** ("Select regional preference"), shown when every part is configured:
   - **North America** column (with a **"USA only"** checkbox) and **Overseas** column.
   - Each column has three radio tiers: Fastest, Standard, Cost-effective. Radio values: `domesticFastest`, `domesticStandard`, `domesticCostEffective`, `overseasFastest`, `overseasStandard`, `overseasCostEffective`.
   - Example seen: USA 4 days $745.84 / 6 days $520.80 / 13 days $259.49, and overseas 8 days $200.01 / 11 days $150.61 / 15 days $136.74, for a one-off anodized 6061 bracket.
   - **Choosing a tier opens a confirm dialog:** "Are you sure you want to change lead times? … will update the production speeds of all parts…" with Cancel / Continue and a "Don't ask again" checkbox. That is easy to trigger by accident, so read the dialog and press Cancel if it wasn't intended.
   - Prices show `$ --` when any part needs a manual quote.
4. **Toolbar:** "Select files or drag and drop here to upload" (adds parts to *this* quote), **Configure via drawing** (enabled once parts are selected), **Select all**. When rows are checked, it becomes **"N selected (clear)"**, **Bulk configure parts**, **Edit quantity**, **Move to…**, **Download**, **Delete**.
5. **Parts table** (`tr.ant-table-row.fileRow`). Columns: *Name* (thumbnail, "Rev N", file name, orange DFM-count badge, "View feedback" link), *Configuration* (process / material / finish, plus **Configure** or **Edit configuration**), *Production speed / Production details* (e.g. "6 days (USA and Mexico)", "Longest lead-time part (+2 day)"), *Quantity* (number input, a multi-quantity icon, "3 quantities available"), *Price* ("$520.80 / $520.80/ea" or **"Please request a quote"**), *Actions* (the "…" menu: **Move to…, Download, Upload part revision, View revision history, Delete**).
6. **Summary card** (right):
   - Line items: Part production (N parts), Shipping (with a "No tariffs apply" note or tariff info), Tax, Order total, **Ship by** date, **Est. Delivery**, Shipping address ("Add shipping address").
   - Buttons change with state:
     - **Request quote.** Disabled while parts are unconfigured. Enabled when a part needs human quoting. The note reads: "Some of your parts require a human to quote… typically within 2 business hours."
     - **Begin checkout.** Shown when everything is instantly priced.
     - **Download quote** (PDF) and **Forward to purchaser**.
7. **Account manager card:** name, email, phone, "Book a meeting".

**Add shipping address modal:**
- Country (**United States / Canada only**), Name*, Company, Address* (2 lines), City*, State/Province*, ZIP*, Phone*.
- "Set as default shipping address for future orders" (checked by default).
- Buttons: Cancel / **Use this shipping address**.

**Share modal:**
- "Share with a team workspace or individual" with **Team workspace | Individual** tabs.
- Fields: "Create a team workspace", "Add new workspace members" (full email).
- Note: "Access requires a Fictiv account… Invites expire in 5 days".
- "Who has access", **Copy invitation link**, **Add to workspace**.

**Forward quote details to purchasers modal:**
- Email field.
- Checkbox "Join my free Fictiv TEAMS account when sharing…".
- "Include quote PDF with email".
- **Copy invitation link** / **Forward quote**.

## 5. Part modal

Opened by clicking **Configure**, **Edit configuration**, the part name or **View feedback**. It is full-screen, with a 3D viewer on the left (view cube, bounding box like `60.00 x 40.00 x 15.00 mm`, "transparent", "reset camera") and a side panel on the right. The header shows "Rev N", the file name, **View revision history**, plus share, download and close (×) icons.

Tabs: **Configuration**, **Threads** (only when holes are detected), **Manufacturability feedback** (✓ when clean, or a count badge).

### 5a. Configuration tab (side panel, top to bottom)

- **Technical drawing (optional)** — "Use a drawing to assist in configuration, add critical requirements, and specify tolerances tighter than our ISO 2768 medium standard". Buttons:
  - **Generate a drawing** (only after process and material are set)
  - **Attach drawing from quote**
  - **Upload drawing** (.pdf)
- **Process and material** — "Ask Materials.AI" link, **Process** select (with a "<process> capabilities guide" link), **Material** select (a searchable, virtualized list grouped by family; a filter icon appears for 3DP technologies), **Quantity** input plus the multi-quantity icon, and **Apply configuration** (first time) or **Cancel / Save** (when editing via "Edit"). Once applied, the section collapses to "CNC · 6061 Aluminum (T6 / T651 / T6511) · Edit · $234.80/ea".
- **Finish** — defaults to "No finish · As machined - ISO Grade N7: Ra 1.6µm / 63µin".
  - **Add finish** opens a menu of finishes valid for the material.
  - Picking one opens a small dialog showing lead-time and price impact (e.g. "+ 2 days, $286.00/ea"), a **Color** select, and **Cancel / Add requirement**.
  - Added finishes are listed with ✏️ and ×.
- **Masking** — "Add masking".
- **Threaded holes** — "N/M threads configured" and **Configure holes** (jumps to the Threads tab). Shows "None detected" when there are no holes.
- **Tolerances** — "Standard tolerances · Included" and "Tight tolerances · None detected / N detected" (read from an attached drawing).
- **Inspections** — "Standard Inspection Report · Included" and "Advanced Inspection Report (CMM, laser or optical) · Add".
- **Certificates** — "Certificate of Conformity · Add" and "Material Certification · Add".
- A note: "Please chat with us to configure custom requirements… Custom Inspection Reports, First Article Inspection (FAI), or Hardware Installation" with a **Contact us** link.
- **Footer** — Quantity, Total price (or "Pending"), and **Save and close**.

### 5b. Threads tab

- "Specify threaded features".
- An expert tip: custom or non-standard threads need a drawing.
- One card per detected hole group (A1, A2…) showing Type, Diameter and Hole depth, plus a select of *valid* standard threads for that modeled diameter, each with a max tap depth. Example for an 8 mm hole: M9x1.25, M9x1.0, 3/8-16, 3/8-18 UNS, 1/8-28, TRAP M10x2. Default is "No threads specified".
- **Model holes at the tap-drill or minor diameter.** The thread choices depend on the modeled diameter, so a hole modeled at the nominal thread size offers the wrong list.

### 5c. Manufacturability feedback tab

- Clean part: "✓ Your part is ready to go! Our manufacturing analysis did not find any manufacturing issues with your part."
- Part with warnings: "This part has warnings that may impact the outcome of your part." It lists each item as a **Warning** card with a title, a truncated description and "Show more". Some items have "DFM views 1 2 3 4" that highlight geometry in the viewer.
- **Respond to feedback** buttons:
  - **Upload revision**
  - **Chat with us**
  - "Learn more about responding to DFM feedback" (https://www.fictiv.com/help/getting-a-quote/how-do-i-view-and-respond-to-dfm-feedback)
- Manual-quote parts: "Please request a quote to receive manufacturability feedback. You will receive a complete Design for Manufacturing (DFM) analysis from the Fictiv quoting team after you request a quote."

### 5d. Bulk configure panel

Select rows, then click **Bulk configure parts**. This opens "Current configuration (N parts)", a table of the selected parts with dimensions in mm and inches. The side panel has Process, Material and **Apply configuration**, then Finish, Masking, Threaded holes, Inspections and Certificates. The note "Some options cannot be configured for multiple parts at a time" applies (threads, for instance). Close with **Close**. It pre-fills the last-used process and material.

### 5e. Materials.AI modal

"Your AI assistant for material selection". It has sample questions, a free-text box and **Close**. Answers come from an OpenAI-powered assistant and are informational only.

## 6. Checkout page: `/pages/orders/quote/<quoteId>`

- **Cutoff banner:** e.g. "Checkout within 0 minutes to meet our 8PM order cutoff on Monday, Sep 28th. See our holiday schedule." Trust this banner over the help center's "3 pm" statement.
- **1. Where do you want your order to go?** A "Ship to" list of saved addresses and **Add new address** (the same form as above).
- **2. Shipping options.** Shows "No shipping options available" until an address exists. Carrier and service options appear afterwards.
- **3. How would you like to pay for your order?** Two tabs:
  - **Pay with credit card:** "Your saved cards" list and **Add new card**. Add new card opens a modal with **Card | Google Pay** tabs, Card number, Expiration (MM/YY), Security code (CVC), Country and ZIP, plus "Use this credit card". **These fields are Stripe iframes.** Fictiv never stores card data itself, and neither should you. See checkout-and-payment.md.
  - **Pay with PO:** "PO use will require approval from our finance department. Requesting use of PO will create a Teams Account for any future orders…" plus **Create and Apply for Payment Terms**. Once terms are approved this becomes a PO upload and PO-number entry.
- **Import choice:** current public guides also document Fictiv DDP versus customer EXW, requiring a customer carrier account for EXW; Canada must use EXW. Confirm this in the rendered checkout (not mapped by the old state helper).
- **Summary** (right): "Edit quote" link, Part production, Shipping, Tax, **Order total**, **Place order** (disabled until address, shipping and payment are set), Download quote, Forward to purchaser, Ship by.

## 7. Account, Library, Orders

- **My Account** (`/pages/my-account`):
  - Personal information: name and phone, each with Edit, plus "Delete this account".
  - Account settings: email (with verification date), password Edit.
  - **Financial permissions:** "Pay with PO (Purchase Order) · Not enabled · **Apply for payment terms**" and "Tax-exempt (reseller) · Not enabled · **Get Tax-exempt permissions**".
  - **Payment methods:** saved cards, "Add new card", and the note "we use Stripe… Fictiv does not directly process or store your credit card information".
- **Library** (`/library/parts`): tabs **Parts** and **Molds**. It is empty until the first order ("After placing your first order, your purchased parts will appear here…").
- **Orders** (`/orders`): a Search box and "New quote". After ordering, each order has "View order detail" with a stage tracker, tracking number, inspection docs and **Reorder**. See orders-library-teams.md.
- **Quotes list** (`/pages/quotes`): one card per quote showing name, last modified, Workspace ("+ Add Workspace"), **status** (e.g. "Ready to purchase"), Ship by and Subtotal. Buttons: "New quote from Parts Library" and "New quote".

## 8. Automation techniques

**What works well:**
- **Read state with `scripts/quote_state.js`** in the javascript tool on the quote or checkout page. It returns a compact line-per-item digest (full object on `window.__fictivState`) with parts, configs, prices, tiers, summary, button states and open dialogs, which is cheaper and more reliable than screenshots.
- **`find` + `ref` clicks** for buttons, links and tabs. Coordinate clicks are fragile because the viewport can be very wide and panels shift after every save.
- **Searchable selects** (Process, Material, Color, thread size): click the field, **type part of the option text** (e.g. `6061`, `Black`, `3D Printing`), wait about 1 s, then press **Enter**. Then confirm the field shows what you wanted. To see all options, open the field and run `scripts/list_dropdown_options.js`, because the list is virtualized.
- **Tool compatibility:** use only browser operations supported by the active tool. Names such as `javascript_tool`, `get_page_text` and file-input upload are examples from the original host. If arbitrary JS evaluation is unavailable, use semantic text/snapshots and the tool's documented native file-picker flow. Never infer success solely from empty helper output.
- **Reading modal text:** `document.querySelectorAll('.ant-modal-content')`. Part-modal content is also in `document.body.innerText` after the main page text, so slice from a known heading such as "Technical drawing (optional)" or "Process and material".
- **"Show more" in DFM cards:** clicking them via JS (`[...document.querySelectorAll('a,button,span')].filter(e=>e.innerText.trim()==='Show more').forEach(e=>e.click())`) expands the full text. Some cards collapse again, so read immediately.
- **Waiting:** geometry analysis takes about 10–30 s per part ("Analyzing parts (1/2) 62%", "Analyzing geometry…", "Configuring part…"). Poll the page text or `quote_state.js` → `analyzing:false` every 5–10 s rather than sleeping blindly.

**Pitfalls seen:**
- Clicking a process radio by ref doesn't select it. Click the card.
- Pressing Escape and re-selecting inside the part modal sometimes doesn't take. After changing Process, re-read the panel text to confirm, or reload the quote URL to discard.
- Choosing a lead-time radio shows a confirm dialog. Material and process edits in the modal aren't saved until **Apply configuration / Save**, and the modal isn't persisted until **Save and close**.
- `javascript_tool` results over a few KB get truncated. Return compact JSON and slice long text.
- The `javascript_tool` does not await a bare Promise. Write `await (async()=>{...})()` for async snippets.
- Some JS return values containing URLs with query strings get blocked by the tool ("[BLOCKED: Cookie/query string data]"). Return `location.pathname` rather than `location.href`.
- Deleting quotes or parts is permanent. Don't do it without explicit user approval.
