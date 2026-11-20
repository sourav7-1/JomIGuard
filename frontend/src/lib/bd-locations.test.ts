// Run: npm test  (node's built-in runner; Node 24 strips the TypeScript types)
import { test } from "node:test";
import assert from "node:assert/strict";
import { divisionOf, divisions, norm } from "./bd-locations.ts";

test("8 divisions and 64 districts, no duplicates", () => {
  assert.equal(divisions.length, 8);
  const districts = divisions.flatMap((d) => d.districts);
  assert.equal(districts.length, 64);
  assert.equal(new Set(districts).size, 64);
  assert.equal(new Set(divisions.map((d) => d.name)).size, 8);
});

test("districts per division", () => {
  const counts = Object.fromEntries(divisions.map((d) => [d.name, d.districts.length]));
  assert.deepEqual(counts, { ঢাকা: 13, চট্টগ্রাম: 11, রাজশাহী: 8, খুলনা: 10, বরিশাল: 6, সিলেট: 4, রংপুর: 8, ময়মনসিংহ: 4 });
});

test("names are Bangla script only", () => {
  for (const name of [...divisions.map((d) => d.name), ...divisions.flatMap((d) => d.districts)]) {
    assert.match(name, /^[ঀ-৿‌‍ ]+$/, name);
  }
});

test("division lookup and digit-insensitive matching", () => {
  assert.equal(divisionOf("ভোলা"), "বরিশাল");
  assert.equal(divisionOf("গাজীপুর"), "ঢাকা");
  assert.equal(divisionOf("নেই"), undefined);
  assert.equal(norm(" ৪১৭ "), "417");
  assert.equal(norm("305/1"), norm("৩০৫/১"));
});
