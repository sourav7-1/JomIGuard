# UX reference: government land service portals

Studied on 2026-11-20, read-only (no login, no forms submitted, no data entered):
land.gov.bd (ভূমি তথ্য বাতায়ন), dlrms.land.gov.bd (ভূমি রেকর্ড ও ম্যাপ / খতিয়ান অনুসন্ধান),
mutation.land.gov.bd (মিউটেশন), portal.ldtax.gov.bd (ভূমি উন্নয়ন কর).

Goal: reuse the *patterns* Bangladeshi citizens already know. We do not copy the look, the
emblem, the colours or the wording, and JomiGuard Sentinel is not a government service.

## What citizens already know

**Services as a tile grid.** The land.gov.bd home is a "ভূমি সংক্রান্ত সেবা" grid of 11 large
tiles: মিউটেশন, ভূমি উন্নয়ন কর, ভূমি রেকর্ড ও ম্যাপ, অধিগ্রহণ, ইজারা, and others. Each tile is an
icon plus a short Bangla name, with a coloured strip on top. One click opens a separate site
per service. The home page has a hotline number (১৬১২২) as large as the hero, a small FAQ
(সচরাচর জিজ্ঞাসা) and a বাং/EN toggle.

**Location picker in a fixed order.** The dlrms "সার্ভে খতিয়ানের তথ্য" search is a row of six
list columns: বিভাগ → জেলা → উপজেলা/থানা → খতিয়ানের ধরন → মৌজা → খতিয়ানের তালিকা. Each
column fills after the previous pick. The মৌজা and খতিয়ান columns have a type-to-filter box.
Search by দাগ নং or owner name is hidden behind an "অধিকতর অনুসন্ধান" button, and the
hint for it is a red scrolling text.

**Tabs for related tasks.** One row of tabs: সার্ভে খতিয়ান · নামজারি খতিয়ান · মৌজা ম্যাপ ·
আবেদনের অবস্থা · নির্দেশিকা. The selected tab is a solid filled block.

**Numbered steps for each service.** Every service explains itself as ধাপ ১ … ধাপ ৬ (search →
add to cart → fill form → pay → office prepares → received by post), so citizens expect to
see where they are in a process.

**Application status is a separate lookup.** "আবেদনের সর্বশেষ অবস্থা দেখুন" asks for an
application number + mobile number + an arithmetic captcha. The mutation site puts a bar
under its hero: বিভাগ + আবেদন নম্বর → খুঁজুন.

**Help everywhere.** A floating live-chat button, the hotline, user manuals (PDF), an FAQ
accordion with "আরো", and "নির্দেশিকা" as a menu item.

**Language.** বাং / EN pill toggle in the header bar.

## What is confusing there (do better)

- **Too many tiles of equal weight.** 11 tiles with no hint which one a buyer needs; the
  citizen has to know that "ভূমি রেকর্ড ও ম্যাপ" means "get a khatian".
- **The six-column picker does not fit a phone.** At desktop width it is a six-column table
  of empty boxes until you click. Empty columns look broken, and nothing says "start here".
- **Key instructions as scrolling red text.** "খতিয়ানের উপর ডাবল ক্লিক করুন", and dag/name
  search hidden behind another button.
- **Status lookup hides progress.** It needs a number you may have lost, and it shows one
  status word instead of a timeline of what happened and what comes next.
- **Every service is a different site.** Each has its own header and layout, so a citizen
  re-learns navigation per service.
- **Heavy hero carousels** push the actual task below the fold.
- **Mobile not verified.** The browser tool could not narrow its window below 1536px, so the
  mobile layouts were not checked. The six-column picker cannot fit a phone as built.

## What JomiGuard Sentinel takes from this

| Pattern | Our version |
|---|---|
| Service tile grid | "সেবাসমূহ": 6 tiles, each with an icon, a one-line "what it does for you" and a start button. Fewer, clearer, ordered by the buying journey. |
| বিভাগ → জেলা → উপজেলা → মৌজা | The same order, but as stacked dropdowns that only show the next step after a pick (one column on phones), with a type-to-filter মৌজা field and visible খতিয়ান নং / দাগ নং fields. No double-click. |
| ধাপ ১…ধাপ ৫ | Each case is a step tracker with a status per step and "এরপর কী করবেন" on the current step. |
| আবেদনের অবস্থা | The case page *is* the status page; no separate lookup number. |
| নির্দেশিকা / সচরাচর জিজ্ঞাসা | A short "কীভাবে ব্যবহার করবেন" box per service plus one FAQ page, written as plain answers. |
| Official services | Where the citizen must use a government service (certified khatian, mutation, LD tax), we say so and link to the real site. We do not imitate it. |

## Identity rules for our UI

- **Brand:** JomiGuard Sentinel's own name, shield mark and palette. No government emblem or
  shapla, no national flag in the header, no "গণপ্রজাতন্ত্রী বাংলাদেশ সরকার", no ministry or
  directorate names as our own, and no land.gov.bd logos.
- **Colour:** the government portals use green and white with red accents. We move away from
  green as the primary colour.
- **Independence note:** a visible note, "JomiGuard Sentinel একটি স্বাধীন প্রকল্প, এটি কোনো
  সরকারি সেবা নয়।"
