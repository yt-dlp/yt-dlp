import * as youtube from "./youtube.js";

export const schema = {
  ...youtube,
};

export type AppSchema = typeof schema;

export { youtube };

export * from "./youtube.js";
