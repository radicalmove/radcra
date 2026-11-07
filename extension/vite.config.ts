import { copyFileSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineConfig, type Plugin } from "vite";
import { buildSync } from "esbuild";
import {
  EXTENSION_DESCRIPTION,
  EXTENSION_NAME,
  UPDATE_METADATA_HOST_PERMISSION,
  loadBuildConfig,
  loadExtensionVersion,
} from "./src/build-config.ts";

const packageJson = JSON.parse(readFileSync(resolve("package.json"), "utf8"));
const lockJson = JSON.parse(readFileSync(resolve("package-lock.json"), "utf8"));
const { version } = loadExtensionVersion(packageJson, lockJson);
const { moodlePatterns, optionalPatterns, serviceOrigin, publicKey, buildCommit, demoMoodleOrigin, demoServiceOrigin } = loadBuildConfig(process.env);

function manifestPlugin(): Plugin {
  return {
    name: "configured-manifest",
    writeBundle() {
      const source = JSON.parse(readFileSync(resolve("public/manifest.json"), "utf8"));
      if (source.version !== "0.0.0") throw new Error("Public manifest version placeholder must remain 0.0.0");
      source.version = version;
      source.name = EXTENSION_NAME;
      source.description = EXTENSION_DESCRIPTION;
      source.key = publicKey;
      source.host_permissions = [...new Set([...moodlePatterns, `${serviceOrigin.replace(/\/$/, "")}/*`, ...(demoServiceOrigin ? [`${demoServiceOrigin}/*`] : []), UPDATE_METADATA_HOST_PERMISSION])];
      source.optional_host_permissions = optionalPatterns;
      const broad = moodlePatterns.filter((pattern) => new URL(pattern).pathname === "/*");
      const narrow = moodlePatterns.filter((pattern) => new URL(pattern).pathname !== "/*");
      const script = source.content_scripts[0];
      source.content_scripts = [
        ...(broad.length ? [{ ...script, matches: broad }] : []),
        ...(narrow.length ? [{ ...script, matches: narrow, match_origin_as_fallback: false }] : []),
      ];
      writeFileSync(resolve("dist/manifest.json"), `${JSON.stringify(source, null, 2)}\n`);
      for (const asset of ["sphere-controls.html", "sphere-controls.js"]) copyFileSync(resolve("public", asset), resolve("dist", asset));
    },
  };
}

function extensionIconsPlugin(): Plugin {
  return {
    name: "copy-extension-icons",
    closeBundle() {
      const destination = resolve("dist/icons");
      mkdirSync(destination, { recursive: true });
      for (const size of [16, 48, 128]) {
        copyFileSync(resolve(`public/icons/icon${size}.png`), resolve(destination, `icon${size}.png`));
      }
    },
  };
}

function extensionFontsPlugin(): Plugin {
  return {
    name: "copy-extension-fonts",
    closeBundle() {
      const destination = resolve("dist/fonts");
      mkdirSync(destination, { recursive: true });
      copyFileSync(resolve("public/fonts/OFL.txt"), resolve(destination, "OFL.txt"));
      for (const weight of ["Regular", "Medium", "SemiBold", "Bold"]) {
        copyFileSync(resolve(`public/fonts/Poppins-${weight}.ttf`), resolve(destination, `Poppins-${weight}.ttf`));
      }
    },
  };
}

function classicEntryBundlesPlugin(): Plugin {
  return {
    name: "classic-self-contained-extension-entries",
    closeBundle() {
      const define = {
        __MOODLE_PATTERNS__: JSON.stringify(moodlePatterns), __OPTIONAL_FRAME_PATTERNS__: JSON.stringify(optionalPatterns),
        __REVIEW_SERVICE_ORIGIN__: JSON.stringify(serviceOrigin), __EXTENSION_VERSION__: JSON.stringify(version), __BUILD_COMMIT__: JSON.stringify(buildCommit), __REVIEW_DEMO_MOODLE_ORIGIN__: JSON.stringify(demoMoodleOrigin), __REVIEW_DEMO_SERVICE_ORIGIN__: JSON.stringify(demoServiceOrigin),
      };
      for (const entry of ["background", "content"]) buildSync({ entryPoints: [resolve(`src/${entry}.ts`)], outfile: resolve(`dist/${entry}.js`), bundle: true, format: "iife", platform: "browser", target: "chrome120", define, minify: true });
      rmSync(resolve("dist/chunks"), { recursive: true, force: true });
    },
  };
}

export default defineConfig({
  publicDir: false,
  define: {
    __MOODLE_PATTERNS__: JSON.stringify(moodlePatterns),
    __OPTIONAL_FRAME_PATTERNS__: JSON.stringify(optionalPatterns),
    __REVIEW_SERVICE_ORIGIN__: JSON.stringify(serviceOrigin),
    __REVIEW_DEMO_MOODLE_ORIGIN__: JSON.stringify(demoMoodleOrigin),
    __REVIEW_DEMO_SERVICE_ORIGIN__: JSON.stringify(demoServiceOrigin),
    __EXTENSION_VERSION__: JSON.stringify(version),
    __BUILD_COMMIT__: JSON.stringify(buildCommit),
  },
  build: {
    target: "chrome120",
    rollupOptions: {
      input: { background: resolve("src/background.ts"), content: resolve("src/content.ts") },
      output: { entryFileNames: "[name].js", chunkFileNames: "chunks/[name]-[hash].js" },
    },
  },
  plugins: [manifestPlugin(), classicEntryBundlesPlugin(), extensionIconsPlugin(), extensionFontsPlugin()],
});
