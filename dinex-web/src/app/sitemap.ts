import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

const BUILT = new Date();

/** Only public, useful pages. Add a line here when you add a new public page (blog, FAQ, pricing...). */
export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: `${SITE_URL}/`, lastModified: BUILT, changeFrequency: "weekly", priority: 1 },
    { url: `${SITE_URL}/terms`, lastModified: BUILT, changeFrequency: "yearly", priority: 0.3 },
  ];
}
