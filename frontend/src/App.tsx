
import { useEffect, useRef, useState } from "react";
import * as api from "./api";
import type { Domain, Recommendation, Schema, SearchHit } from "./types";
import FilterPanel, { type FilterValues } from "./components/FilterPanel";
import ResultCard from "./components/ResultCard";
import "./App.css";

export default function App() {
  const [domains, setDomains] = useState<Domain[]>([]);
  const [domain, setDomain] = useState("");
  const [schema, setSchema] = useState<Schema | null>(null);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [selected, setSelected] = useState<SearchHit | null>(null);
  const [diversity, setDiversity] = useState(0);
  const [k, setK] = useState(10);
  const [filters, setFilters] = useState<FilterValues>({});
  const [results, setResults] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reqId = useRef(0);

  useEffect(() => {
    api.getDomains()
      .then((d) => {
        setDomains(d);
        if (d.length) setDomain(d[0].name);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!domain) return;

    let cancelled = false;

    api.getSchema(domain)
      .then((s) => {
        if (!cancelled) {
          setSchema(s);
          setDiversity(s.default_diversity);
        }
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      });

    return () => {
      cancelled = true;
    };
  }, [domain]);

  useEffect(() => {
    const q = query.trim();

    if (!domain || q.length < 2) {
      setHits([]);
      return;
    }

    let cancelled = false;

    const t = setTimeout(() => {
      api.search(domain, q, 6)
        .then((h) => {
          if (!cancelled) setHits(h);
        })
        .catch((e: Error) => {
          if (!cancelled) setError(e.message);
        });
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(t);
    };
  }, [query, domain]);

  function changeDomain(name: string) {
    if (name === domain) return;

    setDomain(name);
    setSchema(null);
    setQuery("");
    setHits([]);
    setSelected(null);
    setResults([]);
    setFilters({});
    setError(null);
  }

  function cleanFilters(f: FilterValues) {
    const out: Record<string, unknown> = {};

    for (const def of schema?.filters ?? []) {
      const v = f[def.key];

      if (
        v === undefined ||
        v === "" ||
        (Array.isArray(v) && v.length === 0)
      ) continue;

      out[def.key] = def.type === "number" ? Number(v) : v;
    }

    return out;
  }

  async function run(
    item: SearchHit | null = selected,
    f: FilterValues = filters
  ) {
    if (!item || !schema) return;

    const id = ++reqId.current;

    setLoading(true);
    setError(null);

    try {
      const res = await api.recommend(domain, {
        item_id: item.id,
        k,
        diversity: schema.supports_diversity ? diversity : 0,
        filters: cleanFilters(f),
      });

      if (id === reqId.current) {
        setResults(res.results);
      }
    } catch (e) {
      if (id === reqId.current) {
        setResults([]);
        setError((e as Error).message);
      }
    } finally {
      if (id === reqId.current) {
        setLoading(false);
      }
    }
  }

  function pick(hit: SearchHit) {
    setSelected(hit);
    setQuery("");
    setHits([]);
    setResults([]);
    run(hit);
  }

  const activeHits = query.trim().length >= 2 ? hits : [];
  const good = activeHits.filter((h) => h.match >= 80);
  const suggestions = good.length ? good : activeHits;

  const maxScore = results.reduce(
    (m, r) => Math.max(m, r.score),
    0
  );

  const domainLabel = schema?.label?.toLowerCase() || "item";

  return (
    <div className="app">

      {/* NAVBAR */}
      <header className="navbar">
        <a className="brand" href="#">
          <span className="brand-icon">
            <span>✦</span>
          </span>
          <span>Recom<span className="brand-accent">AI</span></span>
        </a>

        <nav className="nav-links">
          <a href="#explore">Explore</a>
          <a href="#recommendations">Recommendations</a>
        </nav>

        <a href="#explore" className="nav-cta">
          Get Started <span>↗</span>
        </a>
      </header>

      <main>

        {/* HERO SECTION */}
        <section className="hero">
          <div className="hero-glow" />

          <div className="hero-content">
            <div className="eyebrow">
              <span className="live-dot" />
              AI-POWERED DISCOVERY
            </div>

            <h1>
              Discover your next
              <br />
              <span>favorite thing.</span>
            </h1>

            <p className="hero-description">
              Smart recommendations tailored to your interests.
              Discover books, music and more with the power of AI.
            </p>

            <a href="#explore" className="hero-button">
              Start Exploring <span>→</span>
            </a>

            <div className="hero-note">
              <span>✦</span> Personalized discovery, powered by AI
            </div>
          </div>

          <div className="hero-decoration">
            <div className="orbit orbit-one" />
            <div className="orbit orbit-two" />
            <div className="floating-card floating-one">
              <span>✦</span>
              <div>
                <strong>Smart matching</strong>
                <small>Built around your taste</small>
              </div>
            </div>
            <div className="floating-card floating-two">
              <span>◈</span>
              <div>
                <strong>Discover more</strong>
                <small>Explore new possibilities</small>
              </div>
            </div>
            <div className="hero-symbol">✦</div>
          </div>
        </section>

        {/* EXPLORATION SECTION */}
        <section className="explore-section" id="explore">

          <div className="section-heading">
            <div>
              <span className="section-label">YOUR DISCOVERY SPACE</span>
              <h2>What are you looking for?</h2>
              <p>Choose a category and find something you'll love.</p>
            </div>
            <span className="section-sparkle">✳</span>
          </div>

          {/* CATEGORY SELECTOR */}
          <div className="category-list">
            {domains.map((d, index) => (
              <button
                key={d.name}
                className={`category-button ${
                  d.name === domain ? "active" : ""
                }`}
                onClick={() => changeDomain(d.name)}
              >
                <span className="category-icon">
                  {["◈", "♫", "✧", "▤"][index % 4]}
                </span>
                {d.label}
                {d.name === domain && <span className="category-check">✓</span>}
              </button>
            ))}
          </div>

          {/* SEARCH BOX */}
          <div className="search-area">
            <div className="search-heading">
              <h3>Find something you love</h3>
              <span>Powered by intelligent search</span>
            </div>

            <div className="search-wrapper">
              <span className="search-icon">⌕</span>

              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={
                  schema
                    ? `Search for a ${domainLabel.replace(/s$/, "")}...`
                    : "Loading search..."
                }
                disabled={!schema}
              />

              <span className="search-shortcut">AI SEARCH</span>
            </div>

            {suggestions.length > 0 && (
              <div className="suggestion-box">
                {suggestions[0].match < 100 && (
                  <p className="suggestion-heading">Did you mean?</p>
                )}

                {suggestions.map((h) => (
                  <button
                    key={h.id}
                    className="suggestion-item"
                    onClick={() => pick(h)}
                  >
                    <span className="suggestion-icon">✦</span>
                    <span className="suggestion-text">
                      <strong>{h.title}</strong>
                      <small>{h.subtitle}</small>
                    </span>
                    <span className="suggestion-match">
                      {h.match}% match
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {domains.length === 0 && !error && (
            <div className="status-message">
              <span className="spinner" />
              Connecting to AI services... The first load may take around
              20 seconds.
            </div>
          )}

          {/* SELECTED ITEM */}
          {selected && (
            <div className="selected-item">
              <div className="selected-icon">✦</div>
              <div>
                <small>YOUR SELECTED ITEM</small>
                <strong>{selected.title}</strong>
                <span>{selected.subtitle}</span>
              </div>
              <button
                className="change-selection"
                onClick={() => {
                  setSelected(null);
                  setResults([]);
                }}
              >
                Change
              </button>
            </div>
          )}

          {/* SETTINGS AND FILTERS */}
          {schema && selected && (
            <div className="settings-layout">

              <div className="settings-card">
                <div className="settings-title">
                  <div>
                    <span className="section-label">CUSTOMIZE</span>
                    <h3>Recommendation settings</h3>
                  </div>
                  <span className="settings-symbol">⚙</span>
                </div>

                <div className="setting-control">
                  <label htmlFor="result-count">
                    Number of recommendations
                  </label>
                  <select
                    id="result-count"
                    value={k}
                    onChange={(e) => setK(Number(e.target.value))}
                  >
                    {[5, 10, 15, 20].map((n) => (
                      <option key={n} value={n}>{n} results</option>
                    ))}
                  </select>
                </div>

                {schema.supports_diversity && (
                  <div className="setting-control">
                    <div className="range-label">
                      <label htmlFor="diversity">
                        Recommendation diversity
                      </label>
                      <strong>{diversity.toFixed(2)}</strong>
                    </div>

                    <input
                      id="diversity"
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={diversity}
                      onChange={(e) => setDiversity(Number(e.target.value))}
                    />
                    <div className="range-hints">
                      <span>More similar</span>
                      <span>More diverse</span>
                    </div>
                  </div>
                )}

                <button className="update-button" onClick={() => run()}>
                  Update recommendations <span>→</span>
                </button>
              </div>

              <div className="filters-card">
                <div className="filters-heading">
                  <div>
                    <span className="section-label">REFINE RESULTS</span>
                    <h3>Filters</h3>
                  </div>
                  <span>☷</span>
                </div>

                <FilterPanel
                  defs={schema.filters}
                  values={filters}
                  onChange={setFilters}
                  onApply={() => run()}
                  onClear={() => {
                    setFilters({});
                    run(selected, {});
                  }}
                />
              </div>
            </div>
          )}

          {/* STATUS MESSAGES */}
          {error && (
            <div className="error-message">
              <strong>Something went wrong</strong>
              <span>{error}</span>
            </div>
          )}

          {loading && (
            <div className="loading-message">
              <span className="spinner" />
              <div>
                <strong>Finding your perfect matches...</strong>
                <p>Our recommendation engine is working its magic.</p>
              </div>
            </div>
          )}

          {/* RESULTS */}
          <section className="results-section" id="recommendations">

            {results.length > 0 && (
              <>
                <div className="results-heading">
                  <div>
                    <span className="section-label">HANDPICKED FOR YOU</span>
                    <h2>Your recommendations</h2>
                    <p>Discover items selected based on your preferences.</p>
                  </div>
                  <span className="result-count">
                    {results.length} RESULTS
                  </span>
                </div>

                <div className="results-grid">
                  {results.map((r, i) => (
                    <div className="result-wrapper" key={r.id}>
                      <ResultCard
                        rank={i + 1}
                        item={r}
                        maxScore={maxScore}
                      />
                    </div>
                  ))}
                </div>
              </>
            )}

            {!loading && selected && results.length === 0 && !error && (
              <div className="empty-state">
                <div className="empty-icon">✧</div>
                <h3>No recommendations found</h3>
                <p>Try changing your filters or recommendation settings.</p>
              </div>
            )}

            {!selected && !loading && !error && (
              <div className="discovery-placeholder">
                <div className="placeholder-icon">✦</div>
                <h3>Your next discovery starts here.</h3>
                <p>
                  Select a category, search for something you like,
                  and let RecomAI find similar items for you.
                </p>
              </div>
            )}

          </section>
        </section>
      </main>

      {/* FOOTER */}
      <footer className="footer">
        <a className="brand" href="#">
          <span className="brand-icon">✦</span>
          <span>Recom<span className="brand-accent">AI</span></span>
        </a>
        <p>Discover more. Explore smarter. Powered by AI.</p>
        <span>© 2026 RecomAI</span>
      </footer>

    </div>
  );
}
