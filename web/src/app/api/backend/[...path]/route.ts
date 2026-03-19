import { auth } from "@/auth";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_BASE_URL =
  process.env.BACKEND_API_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  "http://127.0.0.1:8000";

const BACKEND_API_KEY =
  process.env.BACKEND_API_KEY ||
  process.env.RAG_API_KEYS ||
  "changeme-reviewer-key";

type RouteContext = {
  params: {
    path: string[];
  };
};

async function proxy(request: NextRequest, { params }: RouteContext) {
  const session = await auth();
  if (!session?.user) {
    return NextResponse.json(
      {
        error: {
          code: "unauthorized",
          message: "You must be signed in to access the backend proxy.",
        },
      },
      { status: 401 }
    );
  }

  const upstreamPath = params.path.join("/");
  const upstreamUrl = new URL(`${BACKEND_BASE_URL.replace(/\/$/, "")}/${upstreamPath}`);
  upstreamUrl.search = request.nextUrl.search;

  const headers = new Headers();
  headers.set("x-api-key", BACKEND_API_KEY);
  headers.set("x-user-id", session.user.email || session.user.id || "web-user");

  const contentType = request.headers.get("content-type");
  let body: BodyInit | undefined;

  if (request.method !== "GET" && request.method !== "HEAD") {
    if (contentType?.includes("multipart/form-data")) {
      body = await request.formData();
    } else {
      const rawBody = await request.text();
      if (rawBody) {
        body = rawBody;
      }
      if (contentType) {
        headers.set("content-type", contentType);
      }
    }
  }

  const response = await fetch(upstreamUrl, {
    method: request.method,
    headers,
    body,
    cache: "no-store",
  });

  const responseHeaders = new Headers();
  const responseContentType = response.headers.get("content-type");
  if (responseContentType) {
    responseHeaders.set("content-type", responseContentType);
  }

  return new NextResponse(response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}
