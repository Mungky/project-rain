// Minimal service worker — required for PWA installability.
// Just claims clients; no offline caching for now (keeps logic simple
// and avoids stale-asset bugs after deploys).

const CACHE_VERSION = "rain-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  // Pass-through. Browser handles cache + network normally.
  return;
});
