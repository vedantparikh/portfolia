// Up to 10 distinct, non-empty tags, as the API accepts
export const parseTags = (text) =>
  [...new Set(text.split(",").map((tag) => tag.trim()).filter(Boolean))].slice(0, 10);
