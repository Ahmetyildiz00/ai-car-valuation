import api from "./axios";

// Scrape
export const triggerScrapeTopModels = (perModel = 500) =>
  api.post(`/admin/scrape-top-models?per_model=${perModel}`);
export const getScrapeStatus = () => api.get("/admin/scrape-status");
export const resetScrapeStatus = () => api.post("/admin/scrape-reset");

// Stats
export const getAdminStats = () => api.get("/admin/stats");

// ML model
export const triggerTrainModel = () => api.post("/admin/train-model");
export const getTrainStatus = () => api.get("/admin/train-status");
export const resetTrainStatus = () => api.post("/admin/train-reset");
export const getModelInfo = () => api.get("/admin/model-info");

// Embeddings
export const triggerBackfillEmbeddings = (force = false) =>
  api.post(`/admin/backfill-embeddings?force=${force}`);
export const getBackfillStatus = () => api.get("/admin/backfill-embeddings-status");
export const resetBackfillStatus = () => api.post("/admin/backfill-embeddings-reset");
