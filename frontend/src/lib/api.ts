import { createApiClient } from "@pm/core";

/** Single shared client. In dev, Vite proxies "/api" -> backend :8000. */
export const api = createApiClient("/api");
