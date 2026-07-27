/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // o build roda no prod2; nao queremos que lint/type quebrem o deploy
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
