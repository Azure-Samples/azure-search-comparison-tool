import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import basicSsl from "@vitejs/plugin-basic-ssl";

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react(), basicSsl()],
    build: {
        outDir: "../backend/static",
        emptyOutDir: true,
        sourcemap: true
    },
    server: {
        proxy: {
            "/searchText": "http://127.0.0.1:5000",
            "/embedQuery": "http://127.0.0.1:5000",
            "/approaches": "http://127.0.0.1:5000"
        }
    }
});
