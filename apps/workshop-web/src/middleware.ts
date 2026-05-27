import { NextRequest, NextResponse } from "next/server";

// Basic HTTP auth gate. Configure via Vercel env vars:
//   BASIC_AUTH_USER, BASIC_AUTH_PASSWORD
//   BASIC_AUTH_DEBUG=1 → return diagnostic info on 401 (lengths only, no secrets)
// Leave USER/PASSWORD both blank to disable (e.g. for local dev).
export function middleware(req: NextRequest) {
  const expectedUser = (process.env.BASIC_AUTH_USER ?? "").trim();
  const expectedPass = (process.env.BASIC_AUTH_PASSWORD ?? "").trim();
  const debug = process.env.BASIC_AUTH_DEBUG === "1";

  if (!expectedUser || !expectedPass) {
    return NextResponse.next();
  }

  const header = req.headers.get("authorization");
  let receivedUser = "";
  let receivedPass = "";
  if (header?.startsWith("Basic ")) {
    try {
      const decoded = atob(header.slice(6));
      const colonIdx = decoded.indexOf(":");
      receivedUser = colonIdx >= 0 ? decoded.slice(0, colonIdx) : decoded;
      receivedPass = colonIdx >= 0 ? decoded.slice(colonIdx + 1) : "";
      if (receivedUser === expectedUser && receivedPass === expectedPass) {
        return NextResponse.next();
      }
    } catch {
      // Malformed header — fall through to 401
    }
  }

  const body = debug
    ? `Authentication failed.
Expected user length: ${expectedUser.length}
Received user length: ${receivedUser.length}
User match: ${receivedUser === expectedUser}
Expected pass length: ${expectedPass.length}
Received pass length: ${receivedPass.length}
Pass match: ${receivedPass === expectedPass}
First char of expected user code: ${expectedUser.charCodeAt(0)}
First char of received user code: ${receivedUser.charCodeAt(0) || "(empty)"}
`
    : "Authentication required";

  return new NextResponse(body, {
    status: 401,
    headers: {
      "WWW-Authenticate": 'Basic realm="Rain", charset="UTF-8"',
      "Content-Type": "text/plain",
    },
  });
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|.*\\.svg|manifest.json).*)"],
};
