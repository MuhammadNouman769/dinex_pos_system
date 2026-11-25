export const slugify = (s: string) => s.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "item";
/** Short unique-ish code so two dishes called "Burger" never clash on SKU. */
export const makeSku = (s: string) => `${slugify(s).toUpperCase().replace(/-/g, "").slice(0, 12)}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
