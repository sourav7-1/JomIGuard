import { test } from "node:test";
import assert from "node:assert/strict";
import { currentStep, groupByPlot, riskBadge, stepNote, type JourneyStep } from "./journey.ts";

const step = (n: number, key: string, status: JourneyStep["status"], note_bn = ""): JourneyStep =>
  ({ n, key, phase: n <= 5 ? "before" : n <= 7 ? "during" : "after", status, note_bn });

test("low risk is shown as incomplete whenever something could not be checked", () => {
  assert.equal(riskBadge("low", false), "incomplete");
  assert.equal(riskBadge("low", true), "low");
  assert.equal(riskBadge("high", false), "high");
  assert.equal(riskBadge(null, false), "unknown");
});

test("the open panel is the first step that needs the user", () => {
  const steps = [step(1, "location", "done"), step(2, "documents", "waiting"), step(3, "paper", "action"), step(4, "ground", "locked")];
  assert.equal(currentStep(steps), 3);
  assert.equal(currentStep([step(1, "location", "done"), step(2, "documents", "waiting")]), 2);
  assert.equal(currentStep([step(1, "location", "done")]), 1);
});

test("step notes: Bangla from the API, English from the map", () => {
  const s = step(4, "ground", "locked", "আগে ধাপ ১-এ প্লটের সীমানা আঁকুন");
  assert.equal(stepNote(s, false), "আগে ধাপ ১-এ প্লটের সীমানা আঁকুন");
  assert.match(stepNote(s, true), /plot outline/);
});

test("dashboard groups cases per plot, newest first, keeping every case", () => {
  const c = (id: string, mouza: string, dag_no: string, updated_at: string) => ({ id, district: "ভোলা", mouza, dag_no, summary: { updated_at } });
  const groups = groupByPlot([c("a", "চরফ্যাশন", "১২৩", "2026-01-01"), c("b", "চরফ্যাশন ", "123", "2026-03-01"), c("c", "অন্য", "1", "2026-02-01")]);
  assert.deepEqual(groups.map((g) => g.map((x) => x.id)), [["b", "a"], ["c"]]);
});
