import { auth } from "@/auth";
import { NextResponse } from "next/server";

const PROTECTED_PREFIXES = [
  "/dashboard",
  "/chat",
  "/documents",
  "/upload",
  "/summaries",
  "/settings",
];

export default auth((req) => {
  const { nextUrl, auth: session } = req;
  const isProtected = PROTECTED_PREFIXES.some((p) =>
    nextUrl.pathname.startsWith(p)
  );

  if (isProtected && !session) {
    const signInUrl = new URL("/signin", nextUrl.origin);
    signInUrl.searchParams.set("callbackUrl", nextUrl.pathname);
    return NextResponse.redirect(signInUrl);
  }

  // Already signed in, redirect away from auth pages
  if (session && nextUrl.pathname === "/signin") {
    return NextResponse.redirect(new URL("/dashboard", nextUrl.origin));
  }

  return NextResponse.next();
});

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.svg$).*)",
  ],
};
