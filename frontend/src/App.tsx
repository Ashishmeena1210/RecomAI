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

  // 1. Load domains once. The first call can be slow: the backend loads its models then.
  useEffect(() => {
    api.getDomains()
      .then((d) => {
        setDomains(d);
        if (d.length) setDomain(d[0].name);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  // 2. Domain changed: fetch its filter schema (state is reset in changeDomain).
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

  // 3. Debounced search-as-you-type (typo tolerance happens in the backend).
  useEffect(() => {
    const q = query.trim();
    if (!domain || q.length < 2) return;
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
      if (v === undefined || v === "" || (Array.isArray(v) && v.length === 0)) continue;
      out[def.key] = def.type === "number" ? Number(v) : v;
    }
    return out;
  }

  async function run(item: SearchHit | null = selected, f: FilterValues = filters) {
    if (!item || !schema) return;
    const id = ++reqId.current; // ignore out-of-order responses
    setLoading(true);
    setError(null);
    try {
      const res = await api.recommend(domain, {
        item_id: item.id,
        k,
        diversity: schema.supports_diversity ? diversity : 0,
        filters: cleanFilters(f),
      });
      if (id === reqId.current) setResults(res.results);
    } catch (e) {
      if (id === reqId.current) {
        setResults([]);
        setError((e as Error).message);
      }
    } finally {
      if (id === reqId.current) setLoading(false);
    }
  }

  function pick(hit: SearchHit) {
    setSelected(hit);
    setHits([]);
    run(hit);
  }

  // Derived values: no state is set for these.
  const activeHits = query.trim().length >= 2 ? hits : [];
  const good = activeHits.filter((h) => h.match >= 80);
  const suggestions = good.length ? good : activeHits;
  const maxScore = results.reduce((m, r) => Math.max(m, r.score), 0);

  return (
    <div className="app">
      <header>
        <h1>RecomAI</h1>
        <p className="muted">Content-based recommendations with explanations</p>
      </header>

      {domains.length === 0 && !error && (
        <p className="muted">Connecting to the backend… the first load can take around 20 seconds.</p>
      )}

      <nav className="tabs">
        {domains.map((d) => (
          <button
            key={d.name}
            className={d.name === domain ? "active" : ""}
            onClick={() => changeDomain(d.name)}
          >
            {d.label}
          </button>
        ))}
      </nav>

      {schema && (
        <>
          <div className="search">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={`Search a ${schema.label.toLowerCase().replace(/s$/, "")}…`}
            />
            {suggestions.length > 0 && (
              <ul className="hits">
                {suggestions[0].match < 100 && <li className="hint">Did you mean…?</li>}
                {suggestions.map((h) => (
                  <li key={h.id}>
                    <button onClick={() => pick(h)}>
                      {h.title} <span className="muted">{h.subtitle}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {selected && (
            <>
              <p className="because">
                Because you picked <strong>{selected.title}</strong>{" "}
                <span className="muted">({selected.subtitle})</span>
              </p>

              <div className="controls">
                <label>
                  Results
                  <select value={k} onChange={(e) => setK(Number(e.target.value))}>
                    {[5, 10, 15, 20].map((n) => (
                      <option key={n}>{n}</option>
                    ))}
                  </select>
                </label>

                {schema.supports_diversity && (
                  <label>
                    Diversity {diversity.toFixed(2)}
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={diversity}
                      onChange={(e) => setDiversity(Number(e.target.value))}
                    />
                  </label>
                )}
                <button onClick={() => run()}>Update</button>
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
            </>
          )}
        </>
      )}

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Finding recommendations…</p>}
      {!loading && selected && results.length === 0 && !error && (
        <p className="muted">No results. Try loosening the filters.</p>
      )}

      <section className="results">
        {results.map((r, i) => (
          <ResultCard key={r.id} rank={i + 1} item={r} maxScore={maxScore} />
        ))}
      </section>
    </div>
  );
}