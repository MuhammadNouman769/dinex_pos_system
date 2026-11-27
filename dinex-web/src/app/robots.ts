import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{
      userAgent: "*",
      allow: ["/", "/terms"],
      // App screens and the API are for signed-in people only. Login/signup pages are NOT blocked here on purpose:
      // Google must be able to crawl them to see their "noindex" tag.
      disallow: ["/api/", "/django-admin/", "/admin",
        "/dashboard", "/pos", "/orders", "/kitchen", "/tables", "/reservations", "/customers", "/cash", "/inventory",
        "/purchases", "/expenses", "/reports", "/day-report", "/payroll", "/staff", "/setup", "/billing", "/kiosk"],
    }],
    sitemap: `${SITE_URL}/sitemap.xml`,
    host: SITE_URL,
  };
}
