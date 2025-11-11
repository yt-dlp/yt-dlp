import {
  boolean,
  index,
  integer,
  jsonb,
  pgSchema,
  text,
  timestamp,
} from "drizzle-orm/pg-core";
import { sql } from "drizzle-orm";

/**
 * The Carey Nieuwhof YouTube specific schema. Keeping it isolated from
 * the default `public` schema means we do not have to worry about naming
 * collisions with any future data models.
 */
export const cnYoutube = pgSchema("cn_youtube");

/**
 * Table for the raw metadata that comes from the yt-dlp scraper.
 * We store a few searchable columns alongside the complete raw payload.
 */
export const videos = cnYoutube.table(
  "videos",
  {
    id: text("id").notNull().primaryKey(),
    channelUrl: text("channel_url").notNull(),
    videoUrl: text("video_url").notNull(),
    title: text("title").notNull(),
    description: text("description"),
    durationSeconds: integer("duration_seconds"),
    publishedTimestamp: integer("published_timestamp"),
    uploadDate: text("upload_date"),
    uploadedAt: timestamp("uploaded_at", { withTimezone: true }),
    scrapedAt: timestamp("scraped_at", { withTimezone: true })
      .notNull()
      .default(sql`now()`),
    isLive: boolean("is_live").notNull().default(false),
    rawData: jsonb("raw_data").notNull(),
    createdAt: timestamp("created_at", { withTimezone: true })
      .notNull()
      .default(sql`now()`),
    updatedAt: timestamp("updated_at", { withTimezone: true })
      .notNull()
      .default(sql`now()`),
  },
  (table) => ({
    channelUrlIdx: index("videos_channel_url_idx").on(table.channelUrl),
    uploadedAtIdx: index("videos_uploaded_at_idx").on(table.uploadedAt),
  }),
);
