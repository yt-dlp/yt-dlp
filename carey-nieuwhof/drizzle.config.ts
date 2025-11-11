import { defineConfig } from "drizzle-kit";
import { config as loadEnv } from "dotenv";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const configDir = dirname(fileURLToPath(import.meta.url));
const envFiles = [".env.local", ".env"];

for (const file of envFiles) {
  const candidate = resolve(configDir, file);
  if (existsSync(candidate)) {
    loadEnv({ path: candidate });
    break;
  }
}

if (!process.env.POSTGRES_URL) {
  throw new Error("POSTGRES_URL must be set to run Drizzle commands.");
}

export default defineConfig({
  schema: "./db/schemas/index.ts",
  out: "./db/migrations",
  dialect: "postgresql",
  dbCredentials: {
    url: process.env.POSTGRES_URL,
  },
  migrations: {
    prefix: "timestamp",
  },
  strict: true,
});
