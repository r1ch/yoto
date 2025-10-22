import fs from "fs-extra";
import path from "path";
import yaml from "js-yaml";
import needle from "needle";
import ffmpeg from "fluent-ffmpeg";
import ffmpegPath from "ffmpeg-static";

ffmpeg.setFfmpegPath(ffmpegPath);

const INPUT_DIR = "./_feeds";        // Directory containing .yaml files
const OUTPUT_DATA_DIR = "./_data";   // Where JSON metadata is saved

async function main() {
  await fs.ensureDir(OUTPUT_DATA_DIR);

  const files = (await fs.readdir(INPUT_DIR)).filter(f => f.endsWith(".xml"));

  for (const file of files) {
    const yamlPath = path.join(INPUT_DIR, file);
    const yamlContent = await fs.readFile(yamlPath, "utf8");

    // Remove leading/trailing ---
    const cleaned = yamlContent.trim().replace(/^---\s*/, "").replace(/\s*---\s*$/, "");

    let config;
    try {
      config = yaml.load(cleaned);
    } catch (err) {
      console.error(`❌ Failed to parse ${file}: ${err.message}`);
      continue;
    }

    const {
      title,
      short,
      source,         // RSS feed URL
      destination,
      extension = "mp3",
      trim = 0,
    } = config;

    if (!short || !source || !destination) {
      console.error(`⚠️ Missing required fields in ${file}, skipping`);
      continue;
    }

    console.log(`🎧 Fetching RSS feed for ${title || short}`);

    let feed;
    try {
      const res = await needle("get", source);
      feed = res.body;
    } catch (err) {
      console.error(`❌ Failed to fetch RSS feed ${source}: ${err.message}`);
      continue;
    }

    const firstItem = feed
      ?.children.find(x => x.name === "channel")
      ?.children.find(x => x.name === "item");

    if (!firstItem) {
      console.error(`⚠️ No <item> found in RSS feed for ${short}`);
      continue;
    }

    // Extract media URL from enclosure or media:content
    const mediaItem = firstItem.children.find(x =>
      x.name === "media:content" || x.name === "enclosure"
    );

    const mediaUrl = mediaItem?.url || mediaItem?.attributes?.url;

    if (!mediaUrl) {
      console.error(`⚠️ No media enclosure found for ${short}`);
      continue;
    }

    console.log(`🎙️  Latest episode URL: ${mediaUrl}`);

    const destDir = path.resolve(destination);
    await fs.ensureDir(destDir);

    const tempFile = path.join(destDir, `${short}-raw.${extension}`);
    const outputFile = path.join(destDir, `${short}.mp3`);
    const dataFile = path.join(OUTPUT_DATA_DIR, `${short}.json`);

    // Download media file
    console.log(`⬇️  Downloading audio...`);
    try {
      const stream = needle.get(mediaUrl, { follow_max: 10 });
      await new Promise((resolve, reject) => {
        const out = fs.createWriteStream(tempFile);
        stream.pipe(out);
        stream.on("end", resolve);
        stream.on("error", reject);
      });
    } catch (err) {
      console.error(`❌ Failed to download audio: ${err.message}`);
      continue;
    }

    console.log(`✅ Downloaded to ${tempFile}`);

    // Convert and trim audio
    console.log(`🎬 Converting and trimming first ${trim}s...`);
    try {
      await new Promise((resolve, reject) => {
        ffmpeg(tempFile)
          .setStartTime(trim)
          .toFormat("mp3")
          .on("error", reject)
          .on("end", resolve)
          .save(outputFile);
      });
    } catch (err) {
      console.error(`❌ Failed to convert audio: ${err.message}`);
      continue;
    }

    // Get MP3 duration and write metadata
    const duration = await getAudioDuration(outputFile);
    const episodeTitle = firstItem.children.find(x => x.name === "title")?.children?.[0] || null;
    const episodePubDate = firstItem.children.find(x => x.name === "pubDate")?.children?.[0] || null;
    const episodeDescription = firstItem.children.find(x => x.name === "description")?.children?.[0] || null;
    const episodeGuid = firstItem.children.find(x => x.name === "guid")?.children?.[0] || null;
    const episodeLink = firstItem.children.find(x => x.name === "link")?.children?.[0] || null;

    const metadata = {
      podcast: {
        title,
        short,
        source,
        destination,
        extension,
        trim,
      },
      episode: {
        title: episodeTitle,
        pubDate: episodePubDate,
        description: episodeDescription,
        guid: episodeGuid,
        link: episodeLink,
        media_url: mediaUrl,
      },
      output: {
        file: outputFile,
        duration_seconds: duration,
        downloaded_at: new Date().toISOString(),
      }
    };

await fs.writeJson(dataFile, metadata, { spaces: 2 });

    console.log(`📄 Saved metadata to ${dataFile}`);
    console.log(`✅ Done: ${short}.mp3 (${duration.toFixed(2)}s)`);

    await fs.remove(tempFile);
  }
}

async function getAudioDuration(filePath) {
  return new Promise((resolve, reject) => {
    ffmpeg.ffprobe(filePath, (err, metadata) => {
      if (err) return reject(err);
      resolve(metadata.format.duration || 0);
    });
  });
}

main()
  .then(() => {
    console.log("🏁 Done. Forcing exit in 2 seconds...");
    setTimeout(() => process.exit(0), 2000);
  })
  .catch(err => {
    console.error("💥 Error:", err);
    process.exit(1);
  });