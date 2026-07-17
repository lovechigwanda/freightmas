import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Builds a self-contained bundle mounted by a thin Frappe Desk Page
// (see freightmas/freightmas/page/shipment_dashboard). Fixed, non-hashed
// output filenames so the Page controller can reference them directly.
export default defineConfig({
	plugins: [vue()],
	build: {
		outDir: "../freightmas/public/dashboard",
		emptyOutDir: true,
		assetsDir: "assets",
		rollupOptions: {
			output: {
				entryFileNames: "dashboard.js",
				chunkFileNames: "assets/dashboard-[name].js",
				assetFileNames: (assetInfo) => {
					if (assetInfo.name && assetInfo.name.endsWith(".css")) {
						return "dashboard.css";
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
});
