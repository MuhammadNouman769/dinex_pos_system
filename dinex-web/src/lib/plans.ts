import type { PublicPlan } from "./types";

/** Shown if the plans cannot be loaded (e.g. no internet on the first visit). The server's plans win whenever they load. */
export const FALLBACK_PLANS: PublicPlan[] = [
  { code: "starter", name: "Starter", description: "One restaurant, getting started", price_monthly: "2999", max_locations: 1, max_users: 5, features: ["POS & bill printing", "Orders & kitchen board", "Menu, recipes & inventory", "Cash shifts & daily reports"] },
  { code: "growth", name: "Growth", description: "Busy restaurants and small chains", price_monthly: "4999", max_locations: 3, max_users: 15, features: ["Everything in Starter", "Up to 3 branches", "15 staff accounts", "Audit log & manager controls"] },
  { code: "pro", name: "Pro", description: "Chains and large restaurants", price_monthly: "6999", max_locations: 10, max_users: 50, features: ["Everything in Growth", "Up to 10 branches", "50 staff accounts", "Priority support"] },
];
export const POPULAR_PLAN = "growth";
