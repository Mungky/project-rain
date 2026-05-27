import type { NextConfig } from "next";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const MINIO_HOSTNAME = process.env.NEXT_PUBLIC_MINIO_HOSTNAME ?? "localhost";
const MINIO_PORT = process.env.NEXT_PUBLIC_MINIO_PORT ?? "9000";
const MINIO_PROTOCOL = (process.env.NEXT_PUBLIC_MINIO_PROTOCOL ?? "http") as
  | "http"
  | "https";

const apiUrl = new URL(API_BASE_URL);

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          {
            key: "Cross-Origin-Embedder-Policy",
            value: "credentialless",
          },
          {
            key: "Cross-Origin-Opener-Policy",
            value: "same-origin",
          },
          {
            key: "Cross-Origin-Resource-Policy",
            value: "cross-origin",
          },
        ],
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: apiUrl.protocol.replace(":", "") as "http" | "https",
        hostname: apiUrl.hostname,
        port: apiUrl.port || undefined,
        pathname: "/v1/documents/**",
      },
      {
        protocol: MINIO_PROTOCOL,
        hostname: MINIO_HOSTNAME,
        port: MINIO_PROTOCOL === "https" ? undefined : MINIO_PORT,
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;
