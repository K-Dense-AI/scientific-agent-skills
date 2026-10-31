# Quoting on Fictiv: the full workflow

This covers everything from a CAD file to a priced quote that is ready for checkout. For the exact labels and layout, see `ui-map.md`. For process and material facts, see `capabilities.md`. For anything that goes wrong, see `troubleshooting.md`.

## Contents
1. Gather requirements first
2. Pre-flight the files
3. Create the quote and upload
4. Classify end use (Prototype / Commercial)
5. Configure each part
   - 5.1 Process and material
   - 5.2 Quantity and quantity tiers
   - 5.3 Finish, masking
   - 5.4 Threads
   - 5.5 Drawing, tolerances, inspections, certificates
   - 5.6 Bulk configuration
6. Review DFM feedback
7. Pick lead time and region
8. Instant price vs. manual quote ("Request quote")
9. Share, forward, download, organize
10. Report the quote back to the user

---

## 1. Gather requirements first

A Fictiv quote is only as good as its configuration. Before you touch the UI, make sure you know the following. Ask the user for anything that is missing, and don't invent specs, because the wrong material or finish produces a real, paid-for wrong part.

| Need | Why it matters | Sensible default if the user explicitly says "you choose" |
|---|---|---|
| Files (paths) and which part is which | Upload | — |
| Process | Changes the materials, price and lead time | CNC for metal or tight fits; 3DP for plastic prototypes and complex organic shapes |
| Material (exact grade) | Price and properties | 6061-T6 aluminum (CNC), Nylon 12 SLS or PA 12 MJF (3DP) |
| Finish and color | Adds cost and days | As machined / as printed |
| Quantity (and whether to compare tiers) | Price breaks | — |
| Threads (size per hole) | Tapped holes are only made if specified | None |
| Tolerances tighter than ISO 2768-m, GD&T, cosmetic reqs | Needs a PDF drawing, and usually a manual quote | ISO 2768-m |
| Inspection or certs (CoC, material cert, CMM, FAI) | Adds cost and days | Standard inspection (free) |
| Prototype vs. Commercial end use | Required; affects tariffs | — (ask; it is a legal declaration) |
| Deadline / need-by date, budget | Choosing the lead-time tier and region | Standard tier |
| Domestic only? ("USA only") | Tariffs, ITAR-adjacent concerns, customer requirements | No |
| Ship-to address (US or Canada) | Tax, shipping, delivery date | — |
| Export classification | Fictiv accepts only EAR99 / 9E991 self-serve; **never ITAR** | — (ask if the part is defense/aerospace-related) |

## 2. Pre-flight the files

Run the checker before uploading:

```bash
python3 <skill>/scripts/check_cad_file.py part1.step part2.sldprt --process cnc
```

It flags likely problems; it is not a CAD kernel or export-control classifier. It inspects STEP text and STL edges, but not native CAD geometry or PDF text. Unknown STEP units stay unitless in its output, and its approximate vertex box can miss curved extrema. A clean result does not certify manufacturability. It flags:
- unsupported formats (IGES, F3D, DXF, assemblies, a drawing on its own)
- mesh files for non-3DP processes
- multi-body or surface-only STEP files (CNC pins/inserts and functional 3DP bodies require manual eligibility review)
- unknown STEP units and small unitless STL dimensions (inch STEP boxes are converted to mm)
- non-watertight STL
- oversize parts
- ITAR text markings

Fix blocking items before uploading. For example, ask the user to export STEP or to split bodies. If the user can't fix the file, explain the consequence (e.g. "this will go to manual review").

## 3. Create the quote and upload

1. Go to `https://app.fictiv.com/pages/quotes/upload`. For an existing quote, open it and use "Select files or drag and drop here to upload" to add parts.
2. **Click the process card** (e.g. "CNC Machining"). Confirm the URL gains `?process=cnc` and the upload pane is active.
3. If a units toggle (mm/in) is shown, set it *before* uploading. This matters most for STL and other unitless mesh files. STEP carries its own units.
4. `find` the `input[type=file]` and upload the file paths to it. You can upload several files at once. When prompted, enable auto-attachment and verify every CAD/PDF pairing; similar names can pair, while duplicates/mismatches may fail. For CNC, drawing reconciliation can populate configuration automatically.
5. The app creates the quote and navigates to `/pages/quotes/<id>`. Record the quote ID and name. If a "Upload complete!" tour appears, click "No, I've got this".
6. Wait for "Analyzing parts (n/N)" to finish. Each row goes "Analyzing geometry…" → "Configuring part…" → a **Configure** button. Poll `quote_state.js` until `analyzing` is false.
7. **Verify the size.** Open the part and read the bounding box in the viewer's bottom right (e.g. `60.00 x 40.00 x 15.00 mm`). Compare it with what the user expects, or with `check_cad_file.py`. A factor of 25.4 means the units are wrong: delete the part and re-upload with the right units.

## 4. Classify end use

The **"Required: Are these parts for prototype or commercial use?"** banner blocks all pricing until answered:
- **Prototype:** "exclusively for development, testing, product evaluation or quality control".
- **Commercial:** "incorporate these components into products that are sold for commercial use".

Ask the user. This is a customs and tariff declaration, so don't guess. Click the card. Afterwards a small dropdown at the top right of the lead-time banner lets you change it.

## 5. Configure each part

Click **Configure** in the row. This opens the part modal on the Configuration tab.

### 5.1 Process and material
- The Process select is pre-set from the card you chose. You can change it per part. Options: CNC, 3D Printing, Urethane Casting, Sheet Metal ("Instant/manual quote") and Injection Molding, Compression Molding, Die Casting ("Quote available within 48 hours").
- **Material:** click the field, type a distinctive fragment (`6061`, `17-4`, `PEEK`, `Nylon 12`, `Accura 25`), then press Enter. Check the field text afterwards. To list everything, open the dropdown and run `list_dropdown_options.js`. The full lists captured in Sep 2026 are in `capabilities.md`. "Custom Materials" and "Other" exist but force a manual quote.
- Set **Quantity**, then click **Apply configuration**. The panel collapses into a summary with a per-unit price (e.g. `$234.80/ea`). The price here reflects the default lead-time tier.
- To change the process or material later, click **Edit** next to the summary, change it, then click **Save**. Finishes that are not valid for the new material may drop off.

### 5.2 Quantity and quantity tiers
- The quantity box sits in the modal footer and in the table row.
- Multi-quantity quoting applies to non-tooling CNC, 3DP and sheet-metal parts. Click the **multi-quantity icon** next to the box to open "Savings by quantity". It has default tiers of 1x, 2x and 5x, with editable quantities and "Add a quantity tier". Click **Save & update prices**, or "Update quantity tier for all parts". The table then shows "3 quantities available". Pick the active tier with its radio.
- Use tiers whenever the user is price-shopping ("how much for 10 vs 50?"). This costs nothing and avoids re-quoting.
- The base 1x quantity is edited in the main field, not the popover. Choosing a tier changes the base quantity. "Update quantity tier for all parts" applies its multiplier to each part, not one absolute quantity, and may trigger manual quoting.
- RFQ (manual) parts allow up to 5 tiers, each priced by an estimator. "Apply these quantity tiers for all parts" copies the requested quantities. See the [August 2026 multi-quantity guide](https://www.fictiv.com/help/getting-a-quote/how-to-use-the-multi-quantity-quote-feature).

### 5.3 Finish and masking
- Click **Add finish**. The menu only lists finishes valid for the material. For 6061 these were: Anodize per MIL-PRF-8625 Type II; Type III; Type III w/ PTFE; Chem Film (Alodine™); ENP (Electroless Nickel Plating); Media Blasting; Nickel Plating; Powder Coating; Vibratory Tumble.
- Pick one. The dialog shows the **lead-time impact and new unit price** (Type II black anodize: "+ 2 days, $286.00/ea"). Choose the **Color** (Type II options: Natural, Black, Blue, Gold, Red, all "Sealed"), then click **Add requirement**.
- You can stack several finishes. Fictiv orders them by production logic. Remove one with × and edit with ✏️.
- **Masking:** "Add masking". Masking of threads or bores usually needs a drawing callout and can trigger review.
- Tell the user the price and day deltas when you add a finish. They often didn't realize anodizing adds days.

### 5.4 Threads (CNC)
- If holes are detected, the Threads tab appears and the Configuration panel shows "0/N threads configured · Configure holes".
- On the **Threads** tab, set the thread for each hole group (A1, A2…) from the dropdown. The list only contains standard threads that fit the modeled diameter, each with a max tap depth.
- **Unthreaded holes stay plain holes.** If the user says "M4 tapped holes" and the modeled holes don't offer M4, the CAD hole is the wrong size. Model tap-drill holes (M4 → 3.3 mm, 1/4-20 → 0.201 in) or attach a drawing.
- Review thread requirements before requesting an exact quote; the Help Center says thread edits and drawing uploads then lock. The current CNC drawing-reconciliation flow can extract threaded holes from PDFs, so do not assume attaching a drawing disables all thread configuration. Inspect the actual modal and reconcile the final thread requirements.
- Non-standard threads are "produced at risk" and need a drawing.

### 5.5 Drawing, tolerances, inspections, certificates
- **Technical drawing (optional)** has three buttons: **Generate a drawing** (auto 3 views plus iso, ISO 2768-m block, threads and bounding box), **Attach drawing from quote**, or **Upload drawing** (PDF).
- A drawing is *required* for:
  - tolerances tighter than ISO 2768-m, and GD&T
  - custom threads
  - surface-roughness or cosmetic specs
  - masking
  - hardware / inserts
  - CoC, material certs, CMM or FAI
- Current CNC drawing reconciliation can apply detected requirements automatically; unresolved/custom requirements may need manual review. Do not assume every attached drawing requires a human quote. Ordinary 3DP drawing attachment is excluded by the drawing guide, but the quoting-time guide describes an exception for threaded inserts; confirm that workflow with Fictiv.
- **Tolerances** shows "Tight tolerances · N detected" after drawing reconciliation reads the PDF. Orange "unresolved" items must be resolved (hover, then **Resolve**) or they can cause production holds.
- **Inspections:** Standard Inspection Report (included). **Advanced Inspection Report** (CMM, laser or optical) is added via "Add". It needs a bubbled drawing and adds about 3–5 business days.
- **Certificates:** **Certificate of Conformity** ($100 in the reviewed help article) and **Material Certification**, each added via "Add". All requested inspections/certificates need drawing callouts and discussion with the account executive before ordering; confirm price, availability and lead-time impact in the returned quote.
- FAI, custom inspection reports and hardware installation go through "Contact us" / chat with Fictiv.
- Review the final configuration against the drawing, including material, finish,
  threads and tolerances. Fictiv's [precedence rule](https://www.fictiv.com/help/placing-an-order/how-do-i-use-drawings-reconciliation)
  uses the digital configuration when it conflicts with the PDF. Record intended
  deviations and independently reconcile CAD geometry/revision with the drawing;
  automatic reconciliation does not do that check. A revised drawing can change
  the configuration, so repeat this review after revisions.
- Then click **Save and close**.

### 5.6 Bulk configuration
For many parts with the same process and material, tick their row checkboxes and click **Bulk configure parts**. Set the process and material, click **Apply configuration**, add a common finish or inspection if needed, then click **Close**. Threads and some other options must still be set per part.

## 6. Review DFM feedback

- A clean part shows a ✓ next to "Manufacturability feedback".
- A part with issues shows an orange count badge in the table plus **View feedback**. Open it and read every card. Use "Show more" for the full text.
- Common results and what to tell the user are in `troubleshooting.md` §3 (thin walls, fillets added, deep cuts or holes, unreachable volume, EDM, tight-tolerance plastics…).
- Warnings don't block ordering. Instant pricing still appears. But they are Fictiv telling you the part may not come out as modeled. **Always relay DFM warnings to the user before they pay** and ask whether to proceed, revise (**Upload revision**, which keeps the part's history) or ask Fictiv (**Chat with us**).

## 7. Pick lead time and region

Once every part is configured and classified, the banner becomes **"Select regional preference"**:
- **North America** (USA or Mexico) or **Overseas**, each with Fastest, Standard and Cost-effective tiers showing production days and the total part price.
- The **"USA only"** checkbox restricts production to US suppliers, which is useful for tariff avoidance or customer requirements.
- Selecting a tier asks for confirmation. Read the dialog, then click **Continue** if intended.
- **The whole quote ships on the longest part's lead time.** The row shows "Longest lead-time part (+2 day)". To let fast parts ship sooner, move slow parts to another quote with "…" → **Move to…**.
- Production days are **business days**. The daily cutoff time is shown on the checkout banner (8 PM on the day observed; help docs say 3 pm PT), and holidays don't count. "Ship by" and "Est. Delivery" appear in the Summary, and Est. Delivery needs an address.
- Match the tier to the user's need-by date, and say how much each alternative costs. For example: "USA 6-day standard is $520.80; overseas 15-day is $136.74 but ships Oct 19."

## 8. Instant price vs. manual quote

- **Instant:** every row shows a price, the Summary shows the order total, and **Begin checkout** is enabled.
- **Manual ("Please request a quote")** happens when *any* part needs a human. Common triggers:
  - multi-body files
  - custom materials
  - drawings with tight tolerances
  - complex geometry
  - molding or die casting
  - large parts
  - non-standard finishes

  In this state the tiers show `$ --` and the Summary reads "Some of your parts require a human to quote… typically within 2 business hours", with a **Request quote** button.
- **Request quote sends the quote to Fictiv's quoting team.** Proceed when the user has authorized submitting this RFQ; otherwise show the completed configuration and request authorization. Before requesting, consider:
  - Can the trigger be removed? Split the multi-body file, pick a standard material, or move the manual part to its own quote with **Move to…** so the instant parts can be ordered now.
  - Have all quantity tiers been added? A manual quote prices up to 5 tiers at once.
  - Are threads configured? They lock after the request.
- After requesting, Fictiv emails when the quote is ready: CNC in under about 2 hours, molding or die casting in about 24–48 h, custom work in up to 2 business days. Don't resubmit duplicates. Check back on the quote page later.

## 9. Share, forward, download, organize

Share and Forward to purchaser email people or grant access, so ensure the user authorized the recipients and content. Download, rename and organizing actions can proceed within the requested task; ask about destructive deletion if not already explicitly authorized.
- **Share** gives Team workspace or Individual access by email, or "Copy invitation link". Anyone with a link can view and edit the quote, drawings included, so use it carefully.
- **Forward to purchaser** emails the quote to a purchaser, optionally with the PDF, and can invite them to Teams. Useful when the user doesn't pay themselves.
- **Download quote** gives a PDF. On the quote page it excludes shipping (you may be asked for a ZIP for tax). From checkout, after an address is set, it includes shipping.
- **Rename** with the ✏️ next to the quote name. Give it a meaningful name (project or PO) so it's findable later.
- **Move to…** sends parts to another quote or to "+ Create new quote". **Delete** is permanent. **View activity log** shows the audit trail.
- Quotes normally expire **30 days** after issue unless the quote states otherwise (Terms). After that, re-open the quote and let it re-price, or duplicate it via Library.

## 10. Report the quote back to the user

Give a compact summary like this before any checkout step (illustrative values, not current pricing):

```
Quote doe_092826  (https://app.fictiv.com/pages/quotes/668afa9c-…)
Use: Prototype   Region/tier: North America · Standard (6 production days)
Parts:
  1. test_bracket.step — CNC · 6061-T6 · Anodize Type II Black · qty 1 — $520.80 ($520.80/ea)
     DFM: clean
Alternatives: USA fastest 4d $745.84 · USA cost-effective 13d $259.49 · Overseas 8/11/15d $200.01/$150.61/$136.74
Subtotal $520.80 · shipping & tax need an address · Ship by Oct 7, 2026
Open items: none  → ready for checkout when you approve
```

Always list open items: DFM warnings, parts needing a manual quote, missing address, and unanswered spec questions.
