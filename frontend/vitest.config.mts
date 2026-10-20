import { defineConfig } from "vitest/config";

// JSX is compiled by Vite's built-in transform (tsconfig "jsx": "react-jsx"),
// so @vitejs/plugin-react is not needed.
export default defineConfig({
  resolve: {
    alias: { "@": import.meta.dirname },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["__tests__/**/*.test.{ts,tsx}"],
    css: false,
  },
});
