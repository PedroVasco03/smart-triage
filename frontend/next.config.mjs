// O browser fala só com o Next (mesma origem, sem CORS): os pedidos a /backend/* são reenviados
// para o FastAPI. Assim o sistema funciona abra-se por localhost, 127.0.0.1 ou pelo IP da rede.
const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Next 16 (modo dev) bloqueia o JavaScript se a página for aberta por um host que não seja localhost.
  allowedDevOrigins: [
    "127.0.0.1",
    "localhost",
    "*.local",
    "192.168.*.*",
    "10.*.*.*",
    "172.*.*.*",
    ...(process.env.EXTRA_DEV_ORIGINS ? process.env.EXTRA_DEV_ORIGINS.split(",") : []),
  ],
  experimental: { proxyTimeout: 120000 },
  async rewrites() {
    return [{ source: "/backend/:path*", destination: `${backend}/:path*` }];
  },
};
export default nextConfig;
