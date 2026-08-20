// Service Worker for ConstructionOS Offline Shell Caching
const CACHE_VERSION = 'v1.0.2-20260820';
const CACHE_NAME = `constructionos-shell-${CACHE_VERSION}`;

const SHELL_ASSETS = [
  '/',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/icons/apple-touch-icon.png'
];

// Install Event: Cache app shell assets and activate immediately
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(SHELL_ASSETS);
    }).then(() => {
      return self.skipWaiting();
    })
  );
});

// Activate Event: Purge ALL stale cache versions so new deployments take immediate effect
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name.startsWith('constructionos-shell-') && name !== CACHE_NAME)
          .map((name) => {
            console.log(`[SW] Deleting legacy cache: ${name}`);
            return caches.delete(name);
          })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// Fetch Event: Network-first for navigation/HTML & shell updates, bypassing API endpoints
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Only handle GET requests
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // Exclude API endpoints, backend requests, and external calls
  if (
    url.pathname.startsWith('/api/') ||
    url.pathname.includes('/events') ||
    url.port === '8000' ||
    url.hostname.includes('onrender.com') ||
    (url.hostname.includes('vercel.app') && url.pathname.startsWith('/api'))
  ) {
    return;
  }

  // Navigation requests: Network-First to ensure redesigns load fresh HTML immediately
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const copy = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
          }
          return networkResponse;
        })
        .catch(() => {
          return caches.match('/') || caches.match(request);
        })
    );
    return;
  }

  // Static assets: Stale-While-Revalidate with immediate background refresh
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      const fetchPromise = fetch(request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          caches.open(CACHE_NAME).then((cache) => cache.put(request, networkResponse.clone()));
        }
        return networkResponse;
      }).catch(() => cachedResponse);

      return cachedResponse || fetchPromise;
    })
  );
});
