// Demo frontend config for `envdiff scan`.
export const sentryDsn = import.meta.env.SENTRY_DSN;
export const featureFlags = process.env.FEATURE_FLAGS ?? "";
export const mode = import.meta.env.MODE; // Vite built-in, ignored by default
