import type { Recommendation } from "../types";

const AUDIO_BARS = ["danceability", "energy", "valence", "acousticness", "speechiness", "liveness"];

type Props = { rank: number; item: Recommendation; maxScore: number };

export default function ResultCard({ rank, item, maxScore }: Props) {
  const m = item.meta ?? {};
  const img = m.image_url?.replace(/^http:/, "https:");
  const chips = [
    m.year,
    m.genre,
    m.album,
    m.publisher,
    m.vote_average != null ? `★ ${m.vote_average}` : null,
    m.runtime ? `${m.runtime} min` : null,
  ].filter((x): x is string | number => x != null && x !== "");

  // Bar is relative to the best score in THIS list. Scores are not comparable across lists.
  const pct = maxScore > 0 ? Math.round((item.score / maxScore) * 100) : 0;

  return (
    <article className="card">
      <div className="rank">{rank}</div>
      {img && (
        <img
          className="cover"
          src={img}
          alt=""
          loading="lazy"
          onError={(e) => (e.currentTarget.style.display = "none")}
        />
      )}
      <div className="body">
        <h3>{item.title}</h3>
        <p className="sub">{item.subtitle}</p>

        <div className="bar" title="Relative to the top result in this list">
          <div style={{ width: `${pct}%` }} />
        </div>
        <small className="muted">score {item.score.toFixed(3)}</small>

        {chips.length > 0 && (
          <div className="chips">
            {chips.map((c, i) => <span key={i}>{c}</span>)}
          </div>
        )}

        {item.reason?.length > 0 && (
          <ul className="reasons">
            {item.reason.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        )}

        {item.contributions && (
          <details>
            <summary>Score breakdown</summary>
            {Object.entries(item.contributions).map(([k, v]) => (
              <div className="mini" key={k}>
                <span>{k}</span>
                <div className="bar"><div style={{ width: `${Math.min(100, (v / item.score) * 100)}%` }} /></div>
                <span>{v.toFixed(3)}</span>
              </div>
            ))}
          </details>
        )}

        {m.audio && (
          <details>
            <summary>Audio profile</summary>
            {AUDIO_BARS.filter((k) => k in m.audio!).map((k) => (
              <div className="mini" key={k}>
                <span>{k}</span>
                <div className="bar"><div style={{ width: `${Math.round(m.audio![k] * 100)}%` }} /></div>
                <span>{m.audio![k].toFixed(2)}</span>
              </div>
            ))}
          </details>
        )}

        {m.spotify_url && (
          <a href={m.spotify_url} target="_blank" rel="noreferrer">Listen on Spotify ↗</a>
        )}
      </div>
    </article>
  );
}