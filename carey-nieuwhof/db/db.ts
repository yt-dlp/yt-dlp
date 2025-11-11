import { config as loadEnv } from "dotenv";
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { schema } from "./schemas/index.js";

ensureDatabaseEnv();

const connectionString =
  process.env.POSTGRES_URL ?? process.env.DATABASE_URL ?? "";

if (!connectionString) {
  throw new Error(
    "POSTGRES_URL env variable is required to initialize the database client.",
  );
}

const maxPoolSize = Number(process.env.POSTGRES_POOL_MAX ?? 5);

const client = postgres(connectionString, {
  max: Number.isFinite(maxPoolSize) ? maxPoolSize : undefined,
  prepare: false,
});

export const db = drizzle(client, { schema });

export type Database = typeof db;

export async function closeDatabaseConnections(options?: {
  timeoutSeconds?: number;
}) {
  await client.end({ timeout: options?.timeoutSeconds ?? 5 });
}

export { client as connection };

function ensureDatabaseEnv() {
  if (process.env.POSTGRES_URL ?? process.env.DATABASE_URL) {
    return;
  }

  const moduleDir = dirname(fileURLToPath(import.meta.url));
  const projectRoot = resolve(moduleDir, "..");
  const envFiles = [".env.local", ".env"];

  for (const file of envFiles) {
    const candidate = resolve(projectRoot, file);
    if (existsSync(candidate)) {
      loadEnv({ path: candidate });
      if (process.env.POSTGRES_URL ?? process.env.DATABASE_URL) {
        return;
      }
    }
  }
}
