import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Builds a self-contained bundle mounted by freightmas/www/client-portal/
// (a plain website page, not a Desk Page - portal users are Website Users
// and never load desk.html). Fixed, non-hashed output filenames so the
// page's Jinja template can reference them directly, mirroring dashboard/
// vite.config.js but into its own output dir/filenames so the two bundles
// never collide.
export default defineConfig(({ command }) => ({
	// Built assets are served by Frappe from /assets/freightmas/portal/ -
	// asset URLs emitted into portal.css (fonts, etc.) need to be rooted
	// there, not at the site root. Leave the dev server at "/" so `npm run
	// dev` still works standalone.
	base: command === "build" ? "/assets/freightmas/portal/" : "/",
	plugins: [vue()],
	build: {
		outDir: "../freightmas/public/portal",
		emptyOutDir: true,
		assetsDir: "assets",
		rollupOptions: {
			output: {
				entryFileNames: "portal.js",
				chunkFileNames: "assets/portal-[name].js",
				assetFileNames: (assetInfo) => {
					if (assetInfo.name && assetInfo.name.endsWith(".css")) {
						return "portal.css";
					}
					return "assets/[name][extname]";
				},
			},
		},
	},
	server: {
		proxy: {
			"/api": "http://freightmas.localhost:8000",
		},
	},
}));
