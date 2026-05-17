import api from "./axios";

export const triggerScrapeTopModels = (perModel = 500) =>
  api.post(`/admin/scrape-top-models?per_model=${perModel}`);

export const getScrapeStatus = () => api.get("/admin/scrape-status");

export const getAdminStats = () => api.get("/admin/stats");
