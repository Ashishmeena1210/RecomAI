import type { FilterDef } from "../types";

export type FilterValues = Record<string, string | string[]>;

type Props = {
  defs: FilterDef[];
  values: FilterValues;
  onChange: (v: FilterValues) => void;
  onApply: () => void;
  onClear: () => void;
};

export default function FilterPanel({ defs, values, onChange, onApply, onClear }: Props) {
  if (!defs.length) return null;
  const set = (key: string, v: string | string[]) => onChange({ ...values, [key]: v });

  return (
    <details className="filters">
      <summary>Filters</summary>
      <div className="filter-grid">
        {defs.map((f) => (
          <label key={f.key}>
            <span>{f.label}</span>

            {f.type === "number" && (
              <input
                type="number"
                step="any"
                value={(values[f.key] as string) ?? ""}
                onChange={(e) => set(f.key, e.target.value)}
              />
            )}

            {f.type === "select" && (f.options?.length ?? 0) > 40 && (
              <>
                <input
                  list={`dl-${f.key}`}
                  placeholder="Any"
                  value={(values[f.key] as string) ?? ""}
                  onChange={(e) => set(f.key, e.target.value)}
                />
                <datalist id={`dl-${f.key}`}>
                  {f.options!.map((o) => <option key={o} value={o} />)}
                </datalist>
              </>
            )}

            {f.type === "select" && (f.options?.length ?? 0) <= 40 && (
              <select
                value={(values[f.key] as string) ?? ""}
                onChange={(e) => set(f.key, e.target.value)}
              >
                <option value="">Any</option>
                {f.options?.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            )}

            {f.type === "multiselect" && (
              <select
                multiple
                value={(values[f.key] as string[]) ?? []}
                onChange={(e) =>
                  set(f.key, Array.from(e.target.selectedOptions, (o) => o.value))
                }
              >
                {f.options?.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            )}
          </label>
        ))}
      </div>
      <div className="row">
        <button onClick={onApply}>Apply</button>
        <button className="ghost" onClick={onClear}>Clear</button>
      </div>
    </details>
  );
}