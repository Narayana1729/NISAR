#!/usr/bin/env node
import { preview } from 'vite';

const port = parseInt(process.env.PORT || '8080', 10);
const host = process.env.HOST || '0.0.0.0';

console.log(`[NISAR] Starting production server on http://${host}:${port}...`);

try {
  const server = await preview({
    preview: {
      port,
      host,
    },
  });

  server.printUrls();

  const shutdown = () => {
    console.log("\n[NISAR] Shutting down production server...");
    server.httpServer.close(() => {
      process.exit(0);
    });
  };

  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
} catch (error) {
  console.error("[NISAR] Failed to start production server:", error);
  process.exit(1);
}
