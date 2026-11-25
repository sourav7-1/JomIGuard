# UX restructure: one plot, one journey

Status: plan (Phase 1). Nothing is built yet. Phase 2 starts after "go".
Audit date: 2026-11-25. Audited as `judge` on localhost:3000, at desktop width (window 1536px) and at 390px (iframe). The Chrome window could not be shrunk, so the 390px checks ran inside a 390px iframe on the same origin.

## Why

A first-time user should always know three things: where they are, what this page is for, and what comes next. Today the app is a set of equal-weight services. It should be one journey for one plot:

| Phase | Step | Name |
|---|---|---|
| Before buying (কেনার আগে) | 1 | জমি চিহ্নিত (location + plot outline) |
| | 2 | কাগজ জমা |
| | 3 | কাগজ যাচাই (findings) |
| | 4 | মাটি যাচাই (satellite) |
| | 5 | রিপোর্ট ও সিদ্ধান্ত |
| While buying (কেনার সময়) | 6 | বিক্রেতা যাচাই |
| | 7 | বায়না এসক্রো |
| After buying (কেনার পরে) | 8 | প্রবাসী গার্ডিয়ান |

## 1. Current site map

| Route | What it does | How you reach it | Problems |
|---|---|---|---|
| `/` | Hero, judge banner, 6 service tiles, sample cases, government links | Logo, "সেবাসমূহ" nav item | Logged-in users still land here (b). The service grid is duplicated on `/dashboard` (b). Tiles have equal weight instead of a journey (c). |
| `/dashboard` | Welcome, "আমার কেস (২৪)", service grid, "সব পাতা" grid | After login, "ড্যাশবোর্ড" nav item | The service grid is a copy of the home grid. The "সব পাতা" grid repeats the nav. Junk cases appear ("savar · দাগ —", English mouza "birulia") along with repeated বিরুলিয়া ৪১৭ / বলিয়ারপুর ৪১৭ copies. Cards show no risk level, progress or next action (g). |
| `/cases` | Flat list of all 24 cases | "সব কেস দেখুন →" | Same list as the dashboard. Active nav item is "সেবাসমূহ" (f). |
| `/find` | Search by division → district → mouza → khatian → dag | Service tiles | Active nav item is "সেবাসমূহ" (f). Overlaps with `/upload` step 1 (both ask for district and mouza). |
| `/upload` | "ধাপ ১ • নতুন যাচাই": district and mouza form that creates a case | "নতুন যাচাই শুরু করুন" buttons, `/find` | A second entry point for the same job as `/find`. Its "ধাপ ১" step numbering is not the journey's numbering. |
| `/upload/[landId]` | Upload documents, sample sets, read progress | After `/upload`, from the case page | Fine. It becomes journey step 2. |
| `/cases/[id]` | Case page, 9,784px tall at 390px (6,943px on desktop) | Case cards, demo | See (d) and (e) below. Active nav item is "সেবাসমূহ" (f). |
| `/cases/[id]/timeline` | Ownership timeline | "এই কেসের টাইমলাইন দেখুন →", home tile "মালিকানার ইতিহাস" | The home and dashboard tile links to **one fixed demo case's** timeline (c). |
| `/cases/[id]/deeds` | Previous deeds and fingerprints | Case page section "আগের দলিল ও প্রমাণ" | The same content is also inlined on the case page. |
| `/escrow` | Static explainer (3 steps) | Service tile | No deal list and no action except "জমির কাগজ যাচাই করুন". A real deal starts only from a case. |
| `/escrow/[id]` | Escrow deal | Case page "বায়না escrow শুরু করুন" | Fine. It becomes journey step 7. |
| `/guardian` | Watched khatians, monthly check | Service tile | Card "দাগ ৩০৫ · বাকেরগঞ্জ" appears twice. Status text ("কোনো পরিবর্তন নেই", "কপি অপরিবর্তিত") and digits stay Bangla in EN mode. |
| `/chat` | Title, a disclaimer and one link | Nav "জমি সহকারী AI" | **Dead page:** no input box, no button. There is no chat API: `lib/api.ts` has no chat call and `backend/app/agent/` holds only prompts (h). |
| `/profile` | "ক্রেতার পরিচয় যাচাই": a mock identity provider flow | Nav "পরিচয় যাচাই" | The nav calls it a profile, but the page is the buyer identity step (i). It is not linked from the journey. |
| `/demo` | Demo packs, satellite plots, prepared cases | Nav "নমুনা ডেটা" | Prepared case `3122299c…` is linked twice. |
| `/how-it-works`, `/docs`, `/help` | Info pages | Nav | Fine. In the new navigation they move under the "সাহায্য ▾" menu. |
| `/login`, `/offline`, `/verify/[token]`, `/dev/components` | Utility pages | Direct links | `/dev/components` is a dev-only page; it stays out of the nav. |

### Confirmed problems

**a) Top nav.** Eight equal items mix app pages and info pages: ড্যাশবোর্ড · সেবাসমূহ · নমুনা ডেটা · কীভাবে কাজ করে · ডকস · সাহায্য · জমি সহকারী AI · পরিচয় যাচাই. The header also has a second "ড্যাশবোর্ড" button. The mobile bottom bar has 5 items: ড্যাশবোর্ড সেবা নমুনা কীভাবে সাহায্য.

**b) Home and dashboard.** Both show the same service grid, and a logged-in user opening `/` sees the marketing page.

**c) Services instead of a journey.** Services are 6 equal tiles. "মালিকানার ইতিহাস" opens one fixed demo case's timeline instead of the user's own case.

**d) Case page.** It has 8 h2 sections plus 4 h3 sections, with these duplicates:
- "এখন কী করবেন" (top) and "এখন আপনার কাজ" (below findings) show the same 3 actions.
- "আংশিক যাচাই" repeats one line 9 times ("এই যাচাইয়ের জন্য বিক্রয় দলিল দরকার, যা কেসে নেই।").
- "নিজে মিলিয়ে নিন" is empty here ("আলাদা করে মিলিয়ে দেখার তথ্য নেই").
- "আবার যাচাই করুন" appears twice.
- The deed archive is both inlined and on its own page.
- The source panel lists each document twice (summary table and tabs).

**e) Safety bug (confirmed).** Case `36eb3095-fef4-4222-991c-e393e273d884` has 4 documents, and 2 of them are "পড়া যায়নি" (2-deed.png, 3-mutation.png). The assessment is stale ("তথ্য বদলেছে — আবার যাচাই করুন"), and 10 of 13 checks did not run. The verdict box still shows **"কম ঝুঁকি · কাগজে বড় কোনো অমিল পাওয়া যায়নি"**.

The headline is chosen in the backend:
- `backend/app/services/risk.py` sets `HEADLINES_BN["low"]` whenever no rule is bad or warn. It ignores coverage.
- `risk.py` never sees unread documents, because failed documents are not in the `LandCase`.
- The case-view API (`backend/app/api/lands.py`) knows both `assessment_stale` and each document's status.

The tracker also shows step 4 (satellite) and step 5 (report: "PDF নেওয়া যায়") as done while step 3 is not, so the steps are out of order.

**f) Wrong active nav item.** `/cases`, `/cases/*`, `/find`, `/upload`, `/escrow` and `/guardian` all highlight "সেবাসমূহ", because `/` is the fallback match.

**g) Dashboard cards.**
- 24 cases are listed, including:
  - junk: mouza "savar" with no dag, and "birulia" in Latin script;
  - repeats of the same mouza and dag: বিরুলিয়া ৪১৭ ×4+ and বলিয়ারপুর ৪১৭ ×2.
- `isListedLand` (`frontend/src/lib/bd-locations.ts`) only hides cases with no district or with `??` in the name, so these pass.
- The cards show no risk level, progress, last-updated time or next action.

**h) /chat is dead.** See the table above.

**i) "পরিচয় যাচাই / Profile".** The page is the buyer identity check, so it belongs to journey step 6 and the account menu.

### j) Other findings

1. **The word "নিরাপদ" is visible on the case page.** The backend disclaimer `DISCLAIMER_BN` says "এই app কখনো জমি নিরাপদ বলে না". `risk.py` deliberately allows this negation (`ALLOWED_PHRASES`), but the hard rule says no "নিরাপদ" in UI copy. **Question for you:** reword it (for example "এই app জমি নিয়ে কোনো নিশ্চয়তা দেয় না") or keep it? Rewording is a backend text change plus its test.
2. **Satellite runs without a finished paper check.** The satellite panel lets you run the satellite check while documents are unread. There is no gating message.
3. **Mixed digits and raw values on the case page.**
   - "মালিক 1" and "দাগ 1" (ASCII), and "হিসাবকৃত: 6.0000000" (7 decimals).
   - The English word "Fingerprint" in Bangla mode.
   - "father" shown raw as the পিং/জং value.
4. **Page height at 390px.**
   - The case page is 9,784px tall, and the editable field panel (about 40 "ঠিক আছে / বদলান" pairs) is always open.
   - `/how-it-works` is 8,012px and `/docs` is 7,322px.
   - No route has horizontal page overflow. The docs TOC and the case table scroll inside their own boxes, which is intended.
5. **EN toggle coverage.** All frontend text switches. These stay Bangla in EN mode:
   - backend `*_bn` text (actions, findings, headline);
   - place names (expected);
   - guardian card status and digits;
   - mixed card lines like "বিরুলিয়া · dag ৪১৭" (Bangla digits in an English label).
6. **Many primary buttons.** The home page has 7 accent buttons (one per tile plus "গাইড শুরু করুন"), and the dashboard has 7.
7. **Logged-in home header.** The header shows both "ড্যাশবোর্ড" (button) and "বের হন", and the judge banner duplicates the guide button.
8. **Duplicate links and cards.** `/demo` links prepared case `3122299c…` twice, and `/guardian` shows card ৩০৫ twice.

Before screenshots (local, not committed):
- dashboard: `C:\Users\soura\AppData\Local\Temp\claude-chrome-screenshots-jzjToP\screenshot-1795621906679-0.jpg`
- case verdict with the safety bug: `C:\Users\soura\AppData\Local\Temp\claude-chrome-screenshots-jzjToP\screenshot-1795621909121-1.jpg`

## 2. New information architecture

```
Public (logged out)                         App (logged in)
/               Home (journey explainer)    /dashboard      আমার কেস          <- / redirects here
/how-it-works   কীভাবে কাজ করে               /find           নতুন যাচাই (step 1 entry)
/demo           নমুনা ডেটা                   /upload/[id]    step 2 (also inside the case page)
/docs           ডকস                          /cases/[id]     the journey, steps 1-8 (#step-N)
/help           প্রশ্নোত্তর                   /escrow/[id]    step 7 detail
/login          প্রবেশ করুন                   /guardian       step 8 overview (all watched plots)
                                            /profile        ক্রেতার পরিচয় যাচাই (account menu, step 6)
                                            /chat           "শীঘ্রই আসছে" (out of the nav)
Redirects: /cases -> /dashboard; /upload -> /find; /escrow -> /dashboard (explainer text moves into step 7)
Kept as deep links: /cases/[id]/timeline, /cases/[id]/deeds (also shown as step-3 sub-tabs)
```

### Navigation

**Logged out** (desktop header):
`[logo]  Home · কীভাবে কাজ করে · নমুনা ডেটা · ডকস        [EN] [theme] [প্রবেশ করুন]`

**Logged in** (desktop header):
`[logo]  আমার কেস · নতুন যাচাই · সাহায্য ▾          [EN] [theme] [judge ▾]`
- সাহায্য ▾ contains: কীভাবে কাজ করে · প্রশ্নোত্তর · ডকস · নমুনা ডেটা
- judge ▾ contains: ক্রেতার পরিচয় যাচাই · পাবলিক হোম · বের হন

**Mobile bottom bar (logged in):** `আমার কেস · নতুন যাচাই · সাহায্য · অ্যাকাউন্ট`. সাহায্য and অ্যাকাউন্ট open a bottom sheet built on the existing Modal.

**Active item rules** (one function, unit-tested):

| Path | Active item |
|---|---|
| `/dashboard`, `/cases*`, `/escrow*`, `/guardian` | আমার কেস |
| `/find`, `/upload*` | নতুন যাচাই |
| `/how-it-works`, `/help`, `/docs`, `/demo` | সাহায্য |
| `/profile` | account |
| `/` | Home (logged out only) |

The logged-in "/" redirect happens client-side in `AuthGuard` (cookies cannot be read in the prerendered layout). `?public=1` shows the home page anyway, and the account menu links to it.

## 3. Wireframes

Every page starts with the same three lines: a title, one line saying what the page is for, and the primary action (at most one "নতুন যাচাই শুরু করুন" per page).

### Home `/` (public)
```
[independence note bar]
HEADER (logged-out nav)
┌──────────────────────────────────────────────────────────┐
│ কাগজ যাচাই, মাটি যাচাই, তারপর কিনুন                          │
│ এক প্লট ধরে ৮ ধাপে: কেনার আগে, কেনার সময়, কেনার পরে।           │
│ [ প্রবেশ করে যাচাই শুরু করুন ]   নমুনা দেখুন →                 │
└──────────────────────────────────────────────────────────┘
JOURNEY TIMELINE (horizontal on desktop, vertical on mobile)
 কেনার আগে ───────────────────────── কেনার সময় ──────── কেনার পরে
 ①জমি চিহ্নিত ②কাগজ জমা ③কাগজ যাচাই ④মাটি যাচাই ⑤রিপোর্ট │ ⑥বিক্রেতা ⑦বায়না │ ⑧গার্ডিয়ান
 (each step: icon, one line; no buttons)
BHOLA EXAMPLE (existing BholaPreview: paper says "নাল", satellite shows water)
সরকারি সেবা লাগলে (existing official links, compact)
FOOTER
```
Removed: the 6-tile ServiceGrid, the "কীভাবে?" buttons, and the judge banner. The guide is reachable from সাহায্য and the "?" button.

### Dashboard `/dashboard` "আমার কেস"
```
আমার কেস
আপনার প্রতিটি জমির যাচাই কোথায় আছে আর এরপর কী করবেন।      [ নতুন যাচাই শুরু করুন ]
┌ case card ─────────────────────────┐ ┌ case card ───────────┐
│ বিরুলিয়া · দাগ ৪১৭       [মাঝারি ঝুঁকি] │ │ ...                   │
│ সাভার, ঢাকা                         │ │                       │
│ ■■■□□ ৩/৫ কেনার আগে                  │ │                       │
│ এরপর: ২টি কাগজ পড়া যায়নি, আবার upload │ │                       │
│ হালনাগাদ: ২৫/১১/২০২৬            →    │ │                       │
└────────────────────────────────────┘ └───────────────────────┘
(no risk yet -> grey "যাচাই হয়নি" badge; unread/stale -> "অসম্পূর্ণ" badge, never "কম ঝুঁকি")
Empty state: "এখনো কোনো কেস নেই" + [ নতুন যাচাই শুরু করুন ] + "নমুনা দিয়ে দেখুন →"
নজরদারিতে থাকা জমি (only if guardian has entries): compact list -> /guardian
```
- Data comes from `getLands` plus each case's case-view (risk, document statuses, stale flag, geometry, satellite, escrow). If that is too many calls, see the open question below.
- Junk filter: `isListedLand` is extended to also hide cases with no dag, or a mouza with no Bangla letters. Nothing is deleted. `demo_reset` skips the same cases.

### New check `/find` (journey step 1 entry)
```
নতুন যাচাই
জমির ঠিকানা দিন; আগে কেস থাকলে সেটি খুলবে, না থাকলে নতুন কেস হবে।
[বিভাগ][জেলা][উপজেলা][মৌজা*][খতিয়ান][দাগ]   [ খুঁজুন ]
Results: existing cases -> open; none -> [ এই ঠিকানায় নতুন কেস শুরু করুন ] -> /cases/[id]#step-2
```
`/upload` (the duplicate district form) redirects here.

### Case page `/cases/[id]` (the journey)
```
বিরুলিয়া · দাগ ৪১৭ · সাভার, ঢাকা                [ঝুঁকির ব্যাজ / অসম্পূর্ণ]
এই জমির যাচাই ধাপে ধাপে; এখন যে ধাপে আছেন সেটি খোলা।
┌ STICKY STEPPER ───────────────────────────────────────────────────────┐
│ কেনার আগে: ①✓ ②! ③… ④🔒 ⑤🔒 │ কেনার সময়: ⑥○ ⑦○ │ কেনার পরে: ⑧○              │
└────────────────────────────────────────────────────────────────────────┘
  (mobile: horizontally scrollable chips; status = done ✓ / needs action ! /
   waiting … / needs an earlier step 🔒 / not started ○)
┌ এখন কী করবেন (one box, max 3, from next_actions + document/stale state) ┐
│ 1. ২টি কাগজ পড়া যায়নি: আবার upload করুন   [ধাপ ২ খুলুন]                  │
│ 2. ...                                                                │
└───────────────────────────────────────────────────────────────────────┘
STEP PANEL (one at a time; URL #step-1 … #step-8; default = first step that needs action)
```
The stepper, "এখন কী করবেন" box and gating messages are built in the frontend from the case-view. The "যা মেলানো যায়নি" text in step 3 comes from the API.

**Step panels:**

1. **জমি চিহ্নিত.** Location fields (read-only, with an edit link) and the plot map (existing PlotMap: draw and save the outline).
2. **কাগজ জমা.** Document list with status, upload (existing UploadFlow pieces), and sample sets. Unread documents show "পড়া যায়নি" with Retry/Remove.
3. **কাগজ যাচাই.**
   - Sub-tabs: ফলাফল · মালিকানার ইতিহাস · আগের দলিল.
   - The ফলাফল tab shows the verdict, then যা মেলেনি, then যা মিলেছে, then "যা মেলানো যায়নি". The "যা মেলানো যায়নি" list merges আংশিক যাচাই and নিজে মিলিয়ে নিন and drops repeated lines.
   - Each finding has a source button that opens the existing Modal with the DocumentFieldsPanel.
   - The editable field panel is collapsed by default.
   - Gate: if any document is unread, show "২টি কাগজ পড়া যায়নি, তাই সব পরীক্ষা চালানো যায়নি" plus [ধাপ ২ খুলুন], above any result.
4. **মাটি যাচাই.** The existing SatellitePanel. Gate: no outline shows "আগে ধাপ ১-এ প্লটের সীমানা আঁকুন" plus [ধাপ ১ খুলুন].
5. **রিপোর্ট ও সিদ্ধান্ত.** Risk summary (same rules as step 3), "যা এই অ্যাপ বলে না" (the existing limits text), and [PDF রিপোর্ট]. Gate: before an assessment exists, show "আগে ধাপ ৩ শেষ করুন".
6. **বিক্রেতা যাচাই.** The existing SellerIdentityPanel, plus a link "নিজের (ক্রেতার) পরিচয় যাচাই" to `/profile`.
7. **বায়না এসক্রো.** The 3-step explainer moved from `/escrow`, then [বায়না escrow শুরু করুন] or the existing deal status with a link to `/escrow/[id]`.
8. **প্রবাসী গার্ডিয়ান.** "এই জমি নজরদারিতে রাখুন" or the latest check status, with a link to `/guardian`.

### `/chat`
```
জমি সহকারী AI — শীঘ্রই আসছে
এই সহকারী এখনো চালু হয়নি। ততক্ষণ নিচের পাতাগুলো দেখুন।
[ কীভাবে কাজ করে ]  প্রশ্নোত্তর →
```
It is removed from every nav.

### `/profile`, renamed "ক্রেতার পরিচয় যাচাই"
```
ক্রেতার পরিচয় যাচাই
বায়না ও এসক্রোর আগে আপনার (ক্রেতার) পরিচয় যাচাই; শুধু ফলাফল রাখা হয়।
[existing IdentityFlow]
```
Reached from the account menu and from journey step 6.

### `/guardian`, `/escrow/[id]`, `/how-it-works`, `/docs`, `/help`, `/demo`
- **All six:** they get the standard header lines (title, purpose, primary action).
- **`/guardian`:** duplicate cards are deduplicated by land id, with a "← আমার কেস" link.
- **`/escrow/[id]`:** gets a "← কেসে ফিরুন" link to `/cases/[id]#step-7`.
- **`/demo`:** the duplicate prepared-case link is removed.
- **`/help`:** the page title becomes "প্রশ্নোত্তর" to match the menu.

## 4. Safety fix (e) design

The rule: never show a no-mismatch summary when any document is unread or missing, or when the assessment is stale.

- **Backend.** In the case-view response (`backend/app/api/lands.py`), when the assessment's risk level is `low` and the case has unread or failed documents, `assessment_stale`, or skipped checks:
  - the headline becomes an "incomplete" headline, for example "সব কাগজ মেলানো যায়নি: ২টি কাগজ পড়া যায়নি";
  - a new `incomplete_reasons_bn: list[str]` lists what could not be checked.
  - The risk level stays as the rules computed it. The UI shows an "অসম্পূর্ণ" badge instead of "কম ঝুঁকি".
- **Same rule in `risk.py`.** A `low` result with skipped checks gets a coverage-aware headline, so the PDF report and `sample_sets` also stop saying "বড় কোনো অমিল পাওয়া যায়নি" on partial coverage.
- **Backend tests:**
  - **Scenario:** a case with one failed document must not return the low headline; a stale assessment must not either.
  - **Unit:** in `risk`, low risk plus skipped checks gives the incomplete headline.
  - The existing `forbidden_words_in` checks keep passing.
- **Frontend.** The dashboard badge and the stepper use the same "incomplete" state, through one small pure function with a unit test (`npm test`).

## 5. Files to change

Frontend (`frontend/src/`):
- `components/Header.tsx`, `components/AuthControls.tsx` (becomes the account menu), `components/JourneyRail.tsx` (mobile bar), new `lib/nav.ts` (items plus active-route function) and `lib/nav.test.ts`
- `components/AuthGuard.tsx`: redirect a logged-in `/` to `/dashboard`, honouring `?public=1`
- `app/page.tsx`: hero, journey timeline, Bhola, links. New `components/JourneyTimeline.tsx`. `ServiceGrid.tsx` and `services.ts` are kept only for `/help` steps or removed if unused.
- `app/dashboard/page.tsx`: case cards. New `components/CaseCard.tsx`. `lib/bd-locations.ts` (junk filter) and its test.
- `app/cases/[id]/CaseDetailClient.tsx`: split into the stepper and step panels. New `components/case/JourneyStepper.tsx`, `components/case/NextActions.tsx`, `lib/journey.ts` (step statuses, gating, incomplete state) and `lib/journey.test.ts`. `CaseTracker.tsx` is replaced. `CaseHeader.tsx`, `SatellitePanel.tsx` and `SellerIdentityPanel.tsx` get small prop changes for gating.
- `app/cases/page.tsx`, `app/upload/page.tsx`, `app/escrow/page.tsx`: become redirects. The escrow explainer moves into step 7.
- `app/chat/page.tsx`: "শীঘ্রই আসছে". `app/profile/page.tsx`: rename and purpose line.
- `app/find/page.tsx`, `app/guardian/page.tsx` (`GuardianDashboard.tsx` dedup), `app/escrow/[id]/EscrowDealClient.tsx` (back link), `app/demo/page.tsx` (dedup), `app/help/page.tsx` (title)
- `components/HelpButton.tsx` and `components/GuidedTour.tsx`: update route matchers and tour stops to the new layout
- `lib/strings.ts`, `lib/strings-en.ts`: new copy in Bangla and English

Backend (`backend/`):
- `app/services/risk.py`: coverage-aware low headline
- `app/api/lands.py`: incomplete state on case-view (unread documents, stale)
- `app/schemas/…` (case-view schema): `incomplete_reasons_bn`
- `app/scripts/demo_reset.py`: skip junk cases with the same rule as the frontend filter
- tests: `tests/unit/test_risk*.py`, plus a scenario test for case-view with a failed document

## 6. Open questions (need your answer with "go")

1. **Disclaimer wording.** Reword the backend disclaimer that contains "নিরাপদ" (see j-1)? I recommend yes.
2. **Repeated cases** with the same mouza and dag (বিরুলিয়া ৪১৭ ×4) have a district, so the junk rule keeps them. Should the dashboard show only the newest per mouza and dag, with an "আরো N টি" link? I recommend yes; nothing is deleted.
3. **Dashboard data.** The progress and risk badge need each case's case-view, which is one request per card (about 15 cards). That is acceptable for now. A `GET /lands?summary=1` backend field would be faster. Should I add it?
4. **Redirects.** Is it OK that `/cases`, `/upload` and `/escrow` become redirects (to `/dashboard`, `/find` and `/dashboard`)? Old links keep working.
