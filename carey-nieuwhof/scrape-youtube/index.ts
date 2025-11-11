import { config as loadEnv } from "dotenv";
import { sql } from "drizzle-orm";
import { spawn } from "node:child_process";
import { constants, promises as fsp } from "node:fs";
import * as fs from "node:fs";
import * as path from "node:path";
import { closeDatabaseConnections, db, type Database } from "../db/db.js";
import { videos } from "../db/schemas/index.js";

type RawVideo = Record<string, unknown> & {
  id?: string;
  title?: string;
  timestamp?: number;
  upload_date?: string;
  description?: string;
  duration?: number;
  channel_url?: string;
  webpage_url?: string;
  url?: string;
  is_live?: boolean;
  live_status?: string;
};

type VideoInsert = typeof videos.$inferInsert;

type PersistPayload = {
  channelUrl: string;
  scrapedAt: string;
  videos: RawVideo[];
};

loadLocalEnv();

const CHANNEL_URL =
  process.env.CAREY_NIEUWHOF_CHANNEL ??
  "https://www.youtube.com/@CareyNieuwhof/videos";
const PROGRESS_INTERVAL = Math.max(
  1,
  Number(process.env.CAREY_PROGRESS_INTERVAL ?? 25),
);
const HEARTBEAT_MS = Math.max(
  1000,
  Number(process.env.CAREY_HEARTBEAT_MS ?? 15000),
);
const PLAYLIST_END = parsePositiveInt(process.env.CAREY_MAX_VIDEOS);
const EXTRA_ARGS = splitArgs(process.env.CAREY_YTDLP_EXTRA_ARGS);
const YTDLP_VERBOSE = isTruthy(process.env.CAREY_YTDLP_VERBOSE);

async function main() {
  try {
    const scriptPath = fs.realpathSync(process.argv[1] ?? __filename);
    const scriptDir = path.dirname(scriptPath);

    const ytDlpExecutable = await locateYtDlp(scriptDir);
    console.log(`Using yt-dlp executable at: ${ytDlpExecutable}`);
    console.log(`Scraping channel: ${CHANNEL_URL}`);

    const rawVideos = await scrapeChannel(ytDlpExecutable, CHANNEL_URL);
    if (!rawVideos.length) {
      throw new Error("yt-dlp returned no videos; cannot write videos.json");
    }

    rawVideos.sort((a, b) => getVideoSortKey(b) - getVideoSortKey(a));

    const payload: PersistPayload = {
      channelUrl: CHANNEL_URL,
      scrapedAt: new Date().toISOString(),
      videos: rawVideos,
    };

    console.log(
      `[db] Persisting ${payload.videos.length} video${
        payload.videos.length === 1 ? "" : "s"
      } to cn_youtube.videos...`,
    );
    await persistVideos(payload, db);
  } finally {
    await closeDatabaseConnections().catch((error: unknown) => {
      console.warn(
        `[db] Failed to close database connections: ${(error as Error).message}`,
      );
    });
  }
}

async function scrapeChannel(executable: string, url: string) {
  const args = [
    "--ignore-errors",
    "--no-warnings",
    "--dump-json",
    "--skip-download",
    "--yes-playlist",
  ];

  if (YTDLP_VERBOSE) {
    args.unshift("--verbose");
  }

  if (Number.isFinite(PLAYLIST_END)) {
    args.push("--playlist-end", String(PLAYLIST_END));
  }

  if (EXTRA_ARGS.length > 0) {
    args.push(...EXTRA_ARGS);
  }

  args.push(url);

  console.log(`[yt-dlp] Command: ${shellJoin(executable, args)}`);

  return new Promise<RawVideo[]>((resolve, reject) => {
    const videos: RawVideo[] = [];
    let stdoutBuffer = "";
    let stderrBuffer = "";
    let lastOutput = Date.now();

    const child = spawn(executable, args, {
      cwd: path.dirname(executable),
      stdio: ["ignore", "pipe", "pipe"],
      env: process.env,
    });
    const heartbeat = setInterval(() => {
      const secondsSinceOutput = Math.round((Date.now() - lastOutput) / 1000);
      console.log(
        `[yt-dlp] still running... parsed ${videos.length} entries so far (last output ${secondsSinceOutput}s ago)`,
      );
    }, HEARTBEAT_MS);

    child.stdout?.setEncoding("utf8");
    child.stdout?.on("data", (chunk: string) => {
      lastOutput = Date.now();
      stdoutBuffer += chunk;
      let newlineIndex = stdoutBuffer.indexOf("\n");
      while (newlineIndex !== -1) {
        const line = stdoutBuffer.slice(0, newlineIndex).trim();
        stdoutBuffer = stdoutBuffer.slice(newlineIndex + 1);
        if (line.length > 0) {
          try {
            const parsed = JSON.parse(line) as RawVideo;
            videos.push(parsed);
            maybeLogProgress(videos.length, parsed);
          } catch (error) {
            child.kill();
            reject(
              new Error(
                `Failed to parse yt-dlp output line: ${(error as Error).message}`,
              ),
            );
            return;
          }
        }
        newlineIndex = stdoutBuffer.indexOf("\n");
      }
    });

    child.stderr?.setEncoding("utf8");
    child.stderr?.on("data", (chunk: string) => {
      stderrBuffer += chunk;
      process.stderr.write(chunk);
      lastOutput = Date.now();
    });

    child.on("error", reject);

    child.on("close", (code) => {
      clearInterval(heartbeat);

      const remaining = stdoutBuffer.trim();
      if (remaining.length > 0) {
        try {
          const parsed = JSON.parse(remaining) as RawVideo;
          videos.push(parsed);
          maybeLogProgress(videos.length, parsed);
        } catch (error) {
          reject(
            new Error(
              `Failed to parse trailing yt-dlp output: ${(error as Error).message}`,
            ),
          );
          return;
        }
      }

      if (code !== 0 && videos.length === 0) {
        reject(
          new Error(
            `yt-dlp exited with code ${code}. stderr:\n${stderrBuffer.trim()}`,
          ),
        );
        return;
      }

      if (stderrBuffer.trim().length > 0) {
        console.warn(stderrBuffer.trim());
      }

      resolve(videos);
    });
  });
}

async function persistVideos(payload: PersistPayload, database: Database) {
  const scrapedAt = getScrapedAtDate(payload.scrapedAt);
  const rows = payload.videos
    .map((video) => mapRawVideoToInsert(video, payload.channelUrl, scrapedAt))
    .filter((value): value is VideoInsert => value !== null);

  if (!rows.length) {
    console.warn(
      "[db] No valid video entries were generated; skipping persistence.",
    );
    return;
  }

  const batchSize = parsePositiveInt(process.env.CAREY_DB_BATCH_SIZE) ?? 250;
  let upserted = 0;

  for (let index = 0; index < rows.length; index += batchSize) {
    const batch = rows.slice(index, index + batchSize);
    await database
      .insert(videos)
      .values(batch)
      .onConflictDoUpdate({
        target: videos.id,
        set: {
          channelUrl: sql`excluded.channel_url`,
          videoUrl: sql`excluded.video_url`,
          title: sql`excluded.title`,
          description: sql`excluded.description`,
          durationSeconds: sql`excluded.duration_seconds`,
          publishedTimestamp: sql`excluded.published_timestamp`,
          uploadDate: sql`excluded.upload_date`,
          uploadedAt: sql`excluded.uploaded_at`,
          scrapedAt: sql`excluded.scraped_at`,
          isLive: sql`excluded.is_live`,
          rawData: sql`excluded.raw_data`,
          updatedAt: sql`excluded.updated_at`,
        },
      });
    upserted += batch.length;
    console.log(
      `[db] Upserted ${batch.length} row${
        batch.length === 1 ? "" : "s"
      } (batch ${Math.floor(index / batchSize) + 1})`,
    );
  }

  console.log(
    `[db] Finished syncing ${upserted} row${upserted === 1 ? "" : "s"} into cn_youtube.videos.`,
  );
}

async function locateYtDlp(startDir: string) {
  const candidateFiles = ["yt-dlp.sh", "yt-dlp"];
  let currentDir = startDir;

  while (true) {
    for (const fileName of candidateFiles) {
      const candidatePath = path.join(currentDir, fileName);
      if (await isExecutable(candidatePath)) {
        return candidatePath;
      }
    }

    const parentDir = path.dirname(currentDir);
    if (parentDir === currentDir) {
      break;
    }
    currentDir = parentDir;
  }

  throw new Error(
    "Unable to locate yt-dlp or yt-dlp.sh. Please ensure you run this script inside the forked yt-dlp repository.",
  );
}

async function isExecutable(filePath: string) {
  try {
    const stats = await fsp.stat(filePath);
    if (!stats.isFile()) {
      return false;
    }
    await fsp.access(filePath, constants.X_OK);
    return true;
  } catch {
    try {
      await fsp.access(filePath, constants.F_OK);
      return true;
    } catch {
      return false;
    }
  }
}

function getVideoSortKey(video: RawVideo) {
  if (typeof video.timestamp === "number" && !Number.isNaN(video.timestamp)) {
    return video.timestamp;
  }

  if (typeof video.upload_date === "string") {
    const parsed = parseUploadDate(video.upload_date);
    if (!Number.isNaN(parsed)) {
      return parsed;
    }
  }

  return 0;
}

function parseUploadDate(uploadDate: string) {
  if (uploadDate.length !== 8) {
    return Number.NaN;
  }

  const year = Number(uploadDate.slice(0, 4));
  const month = Number(uploadDate.slice(4, 6));
  const day = Number(uploadDate.slice(6, 8));

  if (
    Number.isNaN(year) ||
    Number.isNaN(month) ||
    Number.isNaN(day) ||
    month < 1 ||
    month > 12 ||
    day < 1 ||
    day > 31
  ) {
    return Number.NaN;
  }

  return Date.UTC(year, month - 1, day) / 1000;
}

function getScrapedAtDate(value: string) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return new Date();
  }
  return parsed;
}

function mapRawVideoToInsert(
  video: RawVideo,
  fallbackChannelUrl: string,
  scrapedAt: Date,
): VideoInsert | null {
  const id = toNonEmptyString(video.id);
  if (!id) {
    return null;
  }

  const channelUrl = toNonEmptyString(video.channel_url) ?? fallbackChannelUrl;
  const title = toNonEmptyString(video.title) ?? id;
  const description = toOptionalString(video.description);
  const durationSeconds = toIntegerOrNull(video.duration);
  const publishedTimestamp = toIntegerOrNull(video.timestamp);
  const uploadDate = toNonEmptyString(video.upload_date);
  const uploadedAt = getUploadedAtDate(video);

  return {
    id,
    channelUrl,
    videoUrl: resolveVideoUrl(video, id),
    title,
    description: description ?? null,
    durationSeconds,
    publishedTimestamp,
    uploadDate,
    uploadedAt,
    scrapedAt,
    isLive: isLiveVideo(video),
    rawData: video,
    updatedAt: new Date(),
  };
}

function resolveVideoUrl(video: RawVideo, fallbackId: string) {
  const candidates = [
    toNonEmptyString(video.webpage_url),
    toNonEmptyString(video.url),
    `https://www.youtube.com/watch?v=${fallbackId}`,
  ];

  for (const candidate of candidates) {
    if (candidate) {
      return candidate;
    }
  }

  return `https://www.youtube.com/watch?v=${fallbackId}`;
}

function getUploadedAtDate(video: RawVideo) {
  if (
    typeof video.timestamp === "number" &&
    Number.isFinite(video.timestamp) &&
    video.timestamp > 0
  ) {
    return new Date(video.timestamp * 1000);
  }

  if (typeof video.upload_date === "string") {
    const parsed = parseUploadDate(video.upload_date);
    if (!Number.isNaN(parsed) && parsed > 0) {
      return new Date(parsed * 1000);
    }
  }

  return null;
}

function isLiveVideo(video: RawVideo) {
  if (typeof video.is_live === "boolean") {
    return video.is_live;
  }

  if (typeof video.live_status === "string") {
    const normalized = video.live_status.toLowerCase();
    return normalized === "is_live" || normalized === "live";
  }

  return false;
}

function toNonEmptyString(value: unknown) {
  if (typeof value !== "string") {
    return undefined;
  }

  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

function toOptionalString(value: unknown) {
  const normalized = toNonEmptyString(value);
  return normalized ?? undefined;
}

function toIntegerOrNull(value: unknown) {
  if (typeof value === "number" && Number.isFinite(value) && value >= 0) {
    return Math.trunc(value);
  }

  if (typeof value === "string") {
    const parsed = Number(value);
    if (Number.isFinite(parsed) && parsed >= 0) {
      return Math.trunc(parsed);
    }
  }

  return null;
}

function loadLocalEnv() {
  const envFiles = [".env.local", ".env"];
  const visited = new Set<string>();
  let currentDir = path.dirname(fs.realpathSync(process.argv[1] ?? __filename));

  while (!visited.has(currentDir)) {
    visited.add(currentDir);

    for (const envFile of envFiles) {
      const candidate = path.resolve(currentDir, envFile);
      if (fs.existsSync(candidate)) {
        loadEnv({ path: candidate });
        return;
      }
    }

    const parent = path.dirname(currentDir);
    if (parent === currentDir) {
      break;
    }
    currentDir = parent;
  }

  loadEnv();
}

function parsePositiveInt(raw?: string) {
  if (!raw) {
    return undefined;
  }

  const value = Number(raw);
  if (!Number.isFinite(value) || value <= 0) {
    return undefined;
  }

  return Math.floor(value);
}

function splitArgs(raw?: string) {
  if (!raw) {
    return [];
  }

  const result: string[] = [];
  const regex = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let match: RegExpExecArray | null;
  while ((match = regex.exec(raw)) !== null) {
    if (match[1] !== undefined) {
      result.push(match[1]);
    } else if (match[2] !== undefined) {
      result.push(match[2]);
    } else if (match[3] !== undefined) {
      result.push(match[3]);
    }
  }
  return result;
}

function isTruthy(raw?: string) {
  if (!raw) {
    return false;
  }

  return ["1", "true", "yes", "on"].includes(raw.toLowerCase());
}

function shellJoin(executable: string, args: string[]) {
  return [executable, ...args].map(shellQuote).join(" ");
}

function shellQuote(value: string) {
  if (/^[\w@%+=:,./-]+$/i.test(value)) {
    return value;
  }

  return `'${value.replace(/'/g, `'\\''`)}'`;
}

function maybeLogProgress(count: number, video: RawVideo) {
  if (count % PROGRESS_INTERVAL !== 0) {
    return;
  }

  const label = [video.title, video.id].filter(Boolean).join(" • ");
  console.log(
    `[yt-dlp] Parsed ${count} entries${label ? ` (latest: ${label})` : ""}...`,
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
