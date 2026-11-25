import { test } from "node:test";
import assert from "node:assert/strict";
import { activeNav } from "./nav.ts";

test("app routes highlight the right item (no more 'services' on /cases and /find)", () => {
  for (const p of ["/dashboard", "/cases", "/cases/abc", "/cases/abc/timeline", "/escrow/1", "/guardian"]) {
    assert.equal(activeNav(p, true), "cases", p);
  }
  for (const p of ["/find", "/upload", "/upload/abc"]) assert.equal(activeNav(p, true), "new", p);
  assert.equal(activeNav("/profile", true), "account");
});

test("info pages: own item when signed out, the help menu when signed in", () => {
  assert.equal(activeNav("/how-it-works", false), "how");
  assert.equal(activeNav("/docs", false), "docs");
  assert.equal(activeNav("/demo", true), "help");
  assert.equal(activeNav("/help", true), "help");
  assert.equal(activeNav("/", false), "home");
  assert.equal(activeNav("/", true), null);
  assert.equal(activeNav("/casesx", true), null); // prefix must end at a path segment
});
