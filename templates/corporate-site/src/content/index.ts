import data from "./site.json";
import type { SiteContent } from "./types";
// Local public content only; no factory contracts or private state in runtime.
export const site: SiteContent = { ...data, format: "corporate-site.visual.v1" };
