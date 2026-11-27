/** Public facts about the site, used for Google (metadata, sitemap, structured data). */
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000").replace(/\/+$/, "");
export const SITE_NAME = "DineX";
export const SITE_TAGLINE = "Restaurant POS software that works offline";
export const SITE_DESCRIPTION =
  "DineX is a restaurant POS and management system by XverLabs: billing, kitchen orders, tables, recipe-based inventory, staff, payroll and loyalty points. Works even when the internet is down. 14-day free trial.";
export const COMPANY = "XverLabs";
/** Optional public contact details, set in deploy/.env (left empty = not shown). */
export const CONTACT_PHONE = process.env.NEXT_PUBLIC_CONTACT_PHONE || "";
export const WHATSAPP = (process.env.NEXT_PUBLIC_WHATSAPP || "923248699647").replace(/\D/g, "");
export const WHATSAPP_URL = `https://wa.me/${WHATSAPP}?text=${encodeURIComponent("Assalam o Alaikum, I want a demo of DineX restaurant POS.")}`;
export const CONTACT_EMAIL = process.env.NEXT_PUBLIC_CONTACT_EMAIL || "";
export const GOOGLE_VERIFICATION = process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION || "";
export const abs = (path = "/") => `${SITE_URL}${path.startsWith("/") ? path : `/${path}`}`;
