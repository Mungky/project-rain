import { NextRequest, NextResponse } from "next/server";

// Basic HTTP auth gate. Configure via Vercel env vars:
//   BASIC_AUTH_USER, BASIC_AUTH_PASSWORD
// Leave both blank to disable (e.g. for local dev).
export function middleware(req: NextRequest) {
  const expectedUser = process.env.BASIC_AUTH_USER;
  const expectedPass = process.env.BASIC_AUTH_PASSWORD;

  if (!expectedUser || !expectedPass) {
    return NextResponse.next();
  }

  const header = req.headers.get("authorization");
  if (header?.startsWith("Basic ")) {
    const decoded = atob(header.slice(6));
    const [user, ...passParts] = decoded.split(":");
    const pass = passParts.join(":");
    if (user === expectedUser && pass === expectedPass) {
      return NextResponse.next();
    }
  }

  return new NextResponse("Authentication required", {
    status: 401,
    headers: { "WWW-Authenticate": 'Basic realm="Rain", charset="UTF-8"' },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.svg|manifest.json).*)"],
};
