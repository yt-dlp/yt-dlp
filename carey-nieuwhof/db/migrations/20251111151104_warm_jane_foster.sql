CREATE SCHEMA "cn_youtube";
--> statement-breakpoint
CREATE TABLE "cn_youtube"."videos" (
	"id" text PRIMARY KEY NOT NULL,
	"channel_url" text NOT NULL,
	"video_url" text NOT NULL,
	"title" text NOT NULL,
	"description" text,
	"duration_seconds" integer,
	"published_timestamp" integer,
	"upload_date" text,
	"uploaded_at" timestamp with time zone,
	"scraped_at" timestamp with time zone DEFAULT now() NOT NULL,
	"is_live" boolean DEFAULT false NOT NULL,
	"raw_data" jsonb NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE INDEX "videos_channel_url_idx" ON "cn_youtube"."videos" USING btree ("channel_url");--> statement-breakpoint
CREATE INDEX "videos_uploaded_at_idx" ON "cn_youtube"."videos" USING btree ("uploaded_at");