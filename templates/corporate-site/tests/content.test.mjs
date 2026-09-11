import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const site = JSON.parse(readFileSync(new URL("../src/content/site.json", import.meta.url)));
test("public content has required renderable collections", () => {
  assert.equal(site.format, "corporate-site.visual.v1");
  assert.ok(site.brand.name.length > 0);
  for (const key of ["navy", "blue", "cyan"]) assert.match(site.brand[key], /^#[a-f0-9]{6}$/i);
  assert.ok(site.services.length > 0); assert.ok(site.faq.length > 0);
  assert.equal(new Set(site.plans.map(p => p.id)).size, site.plans.length);
});
test("public configuration contains no private factory contract", () => {
  const text = JSON.stringify(site);
  for (const field of ["work_order_id", "manifest_hash", "authorization", "source_id"]) assert.ok(!text.includes(field));
});
