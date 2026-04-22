import api from "./axios";

export const getSubscription = () => api.get("/subscription");

export const upgradeSubscription = (durationDays = 30) =>
  api.post("/subscription/upgrade", { tier: "pro", duration_days: durationDays });

export const cancelSubscription = () => api.post("/subscription/cancel");
