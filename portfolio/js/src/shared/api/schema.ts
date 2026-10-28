import type { components, paths } from "./generated/schema";

export type ApiPaths = keyof paths;
export type Schemas = components["schemas"];
