# Troubleshooting Fictiv

Find the symptom, then apply the fix. The entries marked "(seen live)" were reproduced on app.fictiv.com in Sep 2026.

## Contents
1. Login / access / account
2. Upload problems
3. DFM feedback: what each warning means and what to do
4. Configuration and pricing problems
5. Lead time and delivery problems
6. Checkout and payment problems
7. Order and post-order problems
8. Browser-automation problems

---

## 1. Login / access / account

| Symptom | Cause | Fix |
|---|---|---|
| Redirected to a login page | Session expired | Ask the user to log in themselves, or use a password-manager credential tool if the environment has one. Never type passwords from chat. |
| Injection molding, urethane, die casting or compression molding is missing; no PO option; no Materials.AI | Personal-email account (Gmail and similar) | The user verifies a company email (banner prompt, or hello@fictiv.com) |
| Checklist says "Verify my email address" | Email is unverified | The user clicks the link in the verification email |
| Can't see a colleague's quote or order | Not shared to your workspace | The colleague shares it via Share → Team workspace |

## 2. Upload problems

Run `scripts/check_cad_file.py` first for format and heuristic STEP/STL checks. Native CAD geometry, PDF contents, functional multi-body eligibility and actual manufacturability require separate review.

| Symptom | Cause | Fix |
|---|---|---|
| Upload zone greyed out, nothing happens on file select (seen live) | No process card selected (the URL has no `?process=`) | Click the process **card** text, not the radio input, then upload again |
| File picked but nothing happens | Ad blocker, or a corporate firewall blocking uploads | Disable the ad blocker for app.fictiv.com and refresh; try another network |
| File rejected by type | IGES, F3D, DXF, native PSM/PWD, drawing-only, assembly | Export STEP (one part per file); attach the PDF to its part |
| Mesh rejected for CNC, urethane or IM | Mesh is 3DP-only | Upload STEP or native CAD |
| Multi-body file loses instant pricing or is rejected | Multiple solids need review | Split separate parts. CNC modeled-in pins/inserts and functional 3DP interlinked components have documented exceptions; separate floating 3DP bodies are unacceptable. A manual quote is not proof that an unsupported file can be manufactured. |
| "Not watertight" / non-manifold | Holes in the mesh (surface modelers) | Repair (Netfabb, Meshmixer) or re-export as a solid |
| SolidWorks part rejected | Multiple configurations | Save a single-configuration copy, or export STEP |
| Part 25.4× too big or small | Units mismatch (unitless mesh, or wrong mm/in toggle) | Delete the part and re-upload with the correct units; confirm the bounding box in the viewer |
| Part larger than the process envelope | Too big | Pick a bigger-envelope technology, split the part, or contact sales for the large-part program |
| Stuck on "Analyzing geometry…" for more than about 3 minutes | Heavy file or backend delay | Reload the quote page. If still stuck, delete the row and re-upload a lighter STEP. |
| Quote and files vanished after upload | ITAR language detected, so the quote is auto-deleted | Don't re-upload. Fictiv doesn't accept ITAR. |

## 3. DFM feedback: meaning and response

In every case, tell the user what Fictiv said, then offer three paths: **proceed as is**, **fix the CAD and click "Upload revision"**, or **ask Fictiv via "Chat with us"**. Warnings don't block ordering, but they're Fictiv's heads-up that the result may differ from the model.

| Warning (Fictiv's wording) | Meaning | Typical fix |
|---|---|---|
| **Thin walls detected** (seen live): "areas on this model that fall below our minimum thickness (0.5mm for metals), and they may not hold up…" | Walls too thin (metal under 0.5 mm, plastic under 1 mm) | Thicken the walls. Or accept the risk of breakage and deflection. |
| **Fillets: Added (Metals)** (seen live): "Fillets will be added in all sharp internal edges… may also be eligible for EDM (requiring extra lead time and cost)" | Sharp internal corners can't be cut with round tools | Add internal radii of at least 0.8 mm (bigger for deep pockets), or accept tool-radius fillets. If sharp corners are essential, EDM costs more. |
| Fillets to be increased | Radii smaller than practical tools | Optional: enlarge the radii to save cost |
| Depth of cut | Pocket deeper than about 10× tool diameter | Shallower pocket, wider pocket, or bigger corner radius |
| Depth of hole | Drilled deeper than about 12× diameter | Shorten or widen the hole |
| Non-standard thread (produced at risk) | No gauge exists for the thread | Switch to a standard thread |
| Warping may occur | Heavy material removal | Rethink the geometry, add ribs, or choose another process |
| Not optimized for CNC machining | Geometry unsuited to CNC | Consider 3DP or casting; ask Fictiv |
| Unreachable volume | A tool can't reach the feature | Redesign, split the part, or ask about 5-axis or EDM |
| EDM may limit lead time options | Feature needs EDM | Redesign if a fast or domestic lead time matters |
| Gear hobbing may limit lead time options | Hobbing is overseas-only | Accept overseas, or redesign |
| Manual deburring may be necessary | Chamfers unreachable by tools | Remove the chamfers or accept |
| Thin stock not available for chosen material | Part thinner than available stock | Change material or thickness |
| Tight tolerance plastics | Tolerance under about ±0.1 mm on plastic | Loosen it, or use PEEK |
| Non-matching drawing and CAD model / Material mismatch | The drawing disagrees with the config or model | Fix whichever is wrong; model and drawing must agree |
| Part will be reworked from McMaster part number | Fictiv will modify a stock part | Usually fine; tell the user |
| "Please request a quote to receive manufacturability feedback" (seen live) | The part is on the manual-quote path | DFM comes from the quoting team after Request quote |

**Injection-molding DFM reports:** open the Manufacturability feedback tab, click "Show DFM topics", annotate each slide marked "Approval required" or "Revision required", then click **Notify Fictiv**. Confirm with the user before notifying.

## 4. Configuration and pricing problems

| Symptom | Cause | Fix |
|---|---|---|
| No prices at all, banner "Required: Are these parts for prototype or commercial use?" (seen live) | End use not declared | Ask the user and click Prototype or Commercial |
| "Configure parts to receive lead times"; Request quote disabled (seen live) | At least one row still shows **Configure** | Configure every part, or move or delete the unconfigured part |
| Every available tier shows `$ --`; Summary says "Some of your parts require a human to quote" (seen live) | At least one part needs manual pricing (multi-body, custom material, drawing callouts, complex geometry) | Remove the trigger, or split the manual part into its own quote with **Move to…** so the rest can be bought now, or click **Request quote** (after user OK; about 2 business hours) |
| Configuration panel price differs from the table price (seen live: $286/ea in panel, $520.80 in table) | The panel price uses a default tier; the table uses the selected lead-time tier | Trust the table and Summary after choosing the tier |
| Material or finish missing from the dropdown | Not offered for that process, or the list is virtualized | Run `list_dropdown_options.js`; choose "Custom Materials / Other" (manual quote) or ask Materials.AI |
| Finish disappeared after changing material | Finish not valid for the new material | Re-add a valid finish |
| Can't select the thread size the user wants (seen live: an 8 mm hole offers M9, 3/8-16…) | The modeled hole diameter doesn't match that thread's tap drill | Remodel the hole at tap-drill size, or attach a drawing |
| Threads tab missing | No compatible holes detected, process is not CNC, or configuration/UI differs | Review modeled tap-drill sizes and final thread requirements; current CNC drawing reconciliation can extract threaded holes from PDFs. Use a drawing for custom threads. |
| Threads locked | An exact or manual quote was already requested | Duplicate or re-upload the part to change them, or ask Fictiv via chat |
| Quote stuck "in review" | Manual quoting in progress | CNC takes under about 2 business hours; IM, die casting and compression 24–48 h; custom up to 2 business days. Follow up via chat or the account manager. Don't re-request. |
| Price much higher than expected | Tight lead time, exotic material, many setups, thin walls or deep pockets, finish, low quantity | Show the user the cheaper tiers, overseas options and quantity breaks; suggest DFM changes |
| Expired quote (over 30 days) | Validity lapsed | Reopen it to let it re-price, or start a new quote from Library |

## 5. Lead time and delivery problems

| Symptom | Cause | Fix |
|---|---|---|
| Ship date later than the tier's day count | Past the daily cutoff, holidays, or the slowest part or finish drives it ("Longest lead-time part (+2 day)") | Order before the cutoff; move slow parts to a separate quote; drop finishes or inspections |
| Est. Delivery says "Address required" | No address | Add the shipping address |
| Overseas holiday delays | Chinese New Year, Golden Week | Switch to North America or "USA only" |
| Need a hard date | — | Tell Fictiv in chat; Teams accounts have the Lead Time Optimizer |

## 6. Checkout and payment problems

| Symptom | Cause | Fix |
|---|---|---|
| "No shipping options available" (seen live) | No address selected | Add or select a US or Canada address |
| Address rejected | Non-US/CA country, or invalid phone or ZIP | Use a valid US/CA address and full phone number; international orders go via sales@fictiv.com |
| Place order disabled | Missing address, shipping choice or payment | Complete all three sections |
| Card declined | Issuer decline, billing ZIP mismatch, card limit, or a 3-D Secure prompt awaiting the user | The user checks the card details and ZIP, approves any bank prompt, tries another card, or uses PO. Never retry repeatedly. |
| PO tab only shows "Create and Apply for Payment Terms" (seen live) | Terms not approved yet | The user applies (about 2 business days) and pays by card meanwhile; ar@fictiv.com |
| Taxed despite being exempt | Exemption not enabled, or the checkbox not ticked this order | Enable at My Account and tick at checkout each time |
| Tariff charges unexpected | Overseas production of metal parts; Commercial classification | Consider USA-only or North America tiers; check the Prototype classification is accurate |

## 7. Order and post-order problems

| Symptom | Fix |
|---|---|
| Need to cancel or change | Contact the program manager or hello@fictiv.com immediately (window: minutes to hours). ECOs cost fees and days. |
| Parts out of spec, wrong finish, missing threads | Contact the program manager immediately with photos and measurements and obtain RMA instructions; standard Terms include 72-hour warranty/return deadlines and exclusions. Fictiv determines repair, remake or refund eligibility (orders-library-teams.md §5). |
| Customs hold | Read the Customs Information tab and displayed deadline. For DDP, complete descriptions/end use; Fictiv handles import documents. For US EXW, the customer handles HTS/CBP registration/POA through the carrier. Canada requires its own import documentation. |
| Can't find an order | Search uses contiguous substrings (order name, part name, PO#); check Team workspaces |
| Need certs or reports | Order detail → "Inspection report data" / "View inspection". Certs only exist if they were added before ordering. |

## 8. Browser-automation problems

| Symptom | Fix |
|---|---|
| Clicks land in the wrong place | Use `find` → `ref` clicks. The viewport can be very wide, so coordinates from a scaled screenshot drift. |
| Dropdown shows only a few options | It's virtualized: run `list_dropdown_options.js` or type to filter |
| Selected option didn't stick | Type the text, wait about 1 s, press Enter, then re-read the field. For the Process field in edit mode, reload the quote URL to reset if needed. |
| Unexpected "Are you sure you want to change lead times?" dialog | You clicked a tier radio. Cancel unless intended. |
| JS result is `{}` | You returned a Promise. Use `await (async()=>{…})()` |
| JS result truncated or "[BLOCKED: Cookie/query string data]" | Return compact JSON; avoid returning full URLs with query strings (use `location.pathname`) |
| Modal content not in `get_page_text` | Modals render in portals; read `.ant-modal-content` via JS, or slice `document.body.innerText` after a known heading |
| Tour or onboarding popups ("Upload complete!", "Improved DFM visualizations!", "Sounds good") | Dismiss them ("No, I've got this", "Sounds good", ×) |
| Changes lost | Part-modal edits need Apply configuration / Save, then Save and close. Reading a URL mid-edit discards them. |
