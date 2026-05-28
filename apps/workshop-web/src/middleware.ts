import { NextRequest, NextResponse } from "next/server";

// Basic HTTP auth gate. Configure via Vercel env vars:
//   BASIC_AUTH_USER, BASIC_AUTH_PASSWORD
// Leave both blank to disable (e.g. for local dev).
const PUBLIC_PATHS = new Set([
  "/manifest.webmanifest",
  "/sw.js",
  "/icon.svg",
  "/apple-icon.png",
  "/favicon.ico",
  "/rain-logo.svg",
  "/logo.svg",
  "/rain-preload.js",
]);

/** Length-independent constant-time string comparison via SHA-256 digests. */
async function timingSafeEqual(a: string, b: string): Promise<boolean> {
  const enc = new TextEncoder();
  const [ha, hb] = await Promise.all([
    crypto.subtle.digest("SHA-256", enc.encode(a)),
    crypto.subtle.digest("SHA-256", enc.encode(b)),
  ]);
  const va = new Uint8Array(ha);
  const vb = new Uint8Array(hb);
  let diff = 0;
  for (let i = 0; i < va.length; i++) diff |= (va[i] ?? 0) ^ (vb[i] ?? 0);
  return diff === 0;
}

export async function middleware(req: NextRequest) {
  const expectedUser = (process.env.BASIC_AUTH_USER ?? "").trim();
  const expectedPass = (process.env.BASIC_AUTH_PASSWORD ?? "").trim();
  if (!expectedUser || !expectedPass) return NextResponse.next();

  // Whitelisted public assets needed for PWA install before login.
  if (PUBLIC_PATHS.has(req.nextUrl.pathname)) return NextResponse.next();

  const header = req.headers.get("authorization");
  if (header?.startsWith("Basic ")) {
    try {
      const decoded = atob(header.slice(6));
      const colonIdx = decoded.indexOf(":");
      const receivedUser = colonIdx >= 0 ? decoded.slice(0, colonIdx) : decoded;
      const receivedPass = colonIdx >= 0 ? decoded.slice(colonIdx + 1) : "";
      const [userOk, passOk] = await Promise.all([
        timingSafeEqual(receivedUser, expectedUser),
        timingSafeEqual(receivedPass, expectedPass),
      ]);
      if (userOk && passOk) return NextResponse.next();
    } catch {
      // Malformed header — fall through to 401
    }
  }

  return new NextResponse("Authentication required", {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Rain", charset="UTF-8"',
      "Content-Type": "text/plain",
    },
  });
}

export const config = {
  // Match every path; we whitelist PWA assets inside the handler so the
  // matcher regex can't be tricked by ".svg"/".png" suffixes in arbitrary URLs.
  matcher: ["/((?!_next/static|_next/image).*)"],
};
