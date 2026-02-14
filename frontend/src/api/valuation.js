import api from "./axios";

export const createValuation = (data) => api.post("/valuations/", data);

export const createValuationWithImage = (formData) =>
  api.post("/valuations/with-image", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });

export const getValuations = () => api.get("/valuations/");

export const getValuation = (id) => api.get(`/valuations/${id}`);

export const deleteValuation = (id) => api.delete(`/valuations/${id}`);

export const getScraperBrands = () => api.get("/scraper/brands");

export const triggerScrape = (brand, maxPages = 1) =>
  api.post(`/scraper/scrape/${brand}?max_pages=${maxPages}`);

export const getScraperStats = () => api.get("/scraper/stats");
