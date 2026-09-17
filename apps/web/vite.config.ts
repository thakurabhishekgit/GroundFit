import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig(({ mode }) => {
  // Load env from monorepo root so VITE_* can live in ../../.env
  const env = loadEnv(mode, path.resolve(__dirname, "../.."), "");
  return {
    plugins: [react()],
    server: {
      port: 2000,
      strictPort: true,
    },
    define: {
      "import.meta.env.VITE_API_URL": JSON.stringify(
        env.VITE_API_URL || "http://localhost:7000"
      ),
      "import.meta.env.VITE_GOOGLE_CLIENT_ID": JSON.stringify(
        env.VITE_GOOGLE_CLIENT_ID || env.GOOGLE_CLIENT_ID || ""
      ),
    },
  };
});
