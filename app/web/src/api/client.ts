import type { components } from "./schema";

export type VideoMeta = components["schemas"]["VideoMeta"];
export type Recipe = components["schemas"]["Recipe"];
export type Trim = components["schemas"]["Trim"];
export type Segment = components["schemas"]["Segment"];
export type Crop = components["schemas"]["Crop"];
export type Scale = components["schemas"]["Scale"];
export type Bitrate = components["schemas"]["Bitrate"];
export type Audio = components["schemas"]["Audio"];
export type FrameCapture = components["schemas"]["FrameCapture"];

export type ValidateRequest = components["schemas"]["ValidateRequest"];
export type ValidateResponse = components["schemas"]["ValidateResponse"];
export type PlanResponse = components["schemas"]["PlanResponse"];

export type PresetItem = {
  key: string;
  label: string;
  recipe_patch: RecipePatch;
};
export type RecipePatch = Partial<Recipe> & Record<string, unknown>;

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${text}`);
  }
  return (await res.json()) as T;
}

export function plan(body: ValidateRequest): Promise<PlanResponse> {
  return jsonFetch<PlanResponse>("/api/plan", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function validateRecipe(
  body: ValidateRequest,
): Promise<ValidateResponse> {
  return jsonFetch<ValidateResponse>("/api/recipe/validate", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function presets(): Promise<PresetItem[]> {
  const res = await fetch("/api/presets", { method: "GET" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${text}`);
  }
  return (await res.json()) as PresetItem[];
}
