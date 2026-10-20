import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Duke Islam",
    short_name: "Duke Islam",
    description: "Duke Islam: Campus prayer times, halal dining, and Muslim Life events at Duke University.",
    start_url: "/",
    display: "standalone",
    background_color: "#012169",
    theme_color: "#012169",
    icons: [
      {
        src: "/icon-192.png",
        sizes: "192x192",
        type: "image/png",
        purpose: "maskable",
      },
      {
        src: "/icon-512.png",
        sizes: "512x512",
        type: "image/png",
        purpose: "maskable",
      },
    ],
  };
}
