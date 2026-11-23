export type Domain = {
  name: string;
  label: string;
  supports_diversity: boolean;
  default_diversity: number;
};

export type FilterDef = {
  key: string;
  label: string;
  type: "select" | "multiselect" | "number";
  options?: string[];
};

export type Schema = Domain & { filters: FilterDef[] };

export type SearchHit = { id: string; title: string; subtitle: string; match: number };

export type Meta = {
  year?: number;
  vote_average?: number;
  runtime?: number;
  publisher?: string;
  image_url?: string;
  genre?: string;
  album?: string;
  audio?: Record<string, number>;
  spotify_url?: string;
  [k: string]: unknown;
};

export type Recommendation = {
  id: string;
  title: string;
  subtitle: string;
  score: number;
  reason: string[];
  meta: Meta;
  contributions?: Record<string, number>;   // movies only
};

export type RecommendResponse = {
  domain: string;
  item_id: string;
  diversity_applied: number;
  count: number;
  results: Recommendation[];
};