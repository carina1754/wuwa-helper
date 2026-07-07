"use client";

import { useEffect, useState } from "react";
import { getUpdates } from "@/lib/api";
import { API_BASE_URL } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";
import type { GameUpdateSummary } from "@/lib/types";

export function UpdatesSummary() {
  const { t } = useLanguage();
  const [updates, setUpdates] = useState<GameUpdateSummary[]>([]);
  const [error, setError] = useState("");
  // Which past-version row is expanded in place (accordion). null = all closed.
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    getUpdates()
      .then(setUpdates)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  // The featured card is always the latest; older versions are listed below and
  // expand in place when clicked.
  const [featured, ...archive] = updates;

  return (
    <>
      <div className="bhead">
        <div className="kick">{t.tabs.Updates}</div>
        <h1>{t.updates.title}</h1>
        <p>{t.updates.body}</p>
      </div>

      {error ? (
        <p className="mt-3 rounded-md border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-400">{error}</p>
      ) : null}

      {featured ? (
        <article className="feat">
          <div className="art">
            {featured.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={`${API_BASE_URL}${featured.image_url}`}
                alt={featured.title_ko}
                loading="lazy"
                className="absolute inset-0 h-full w-full object-cover"
              />
            ) : (
              <>
                <span className="cnr tl" />
                <span className="cnr br" />
                <span className="v">{featured.version}</span>
                <span className="vt">VERSION</span>
              </>
            )}
          </div>
          <div className="body">
            <span className="now">
              <i />
              {t.tabs.Updates}
            </span>
            {featured.release_date_kst ? (
              <time>
                {featured.release_date_kst} {t.updates.releaseDate}
              </time>
            ) : null}
            <h2>{featured.title_ko}</h2>
            <p>{featured.summary_ko}</p>
            {featured.highlights_ko.length > 0 || featured.source_links.length > 0 ? (
              <div className="tags">
                {featured.highlights_ko.map((highlight) => (
                  <span key={highlight} className="tag">
                    {highlight}
                  </span>
                ))}
                {featured.source_links.map((source, index, arr) => (
                  <a key={source} href={source} target="_blank" rel="noreferrer" className="tag src">
                    {t.updates.source}
                    {arr.length > 1 ? ` ${index + 1}` : ""} →
                  </a>
                ))}
              </div>
            ) : null}
          </div>
        </article>
      ) : null}

      {updates.length === 0 && !error ? <div className="soon">{t.updates.empty}</div> : null}

      {archive.length > 0 ? <div className="arch">{t.tabs.Updates}</div> : null}
      {archive.map((update) => {
        const open = expandedId === update.id;
        return (
          <div key={update.id} className={`acc${open ? " open" : ""}`}>
            <button
              type="button"
              className="urow"
              aria-expanded={open}
              onClick={() => setExpandedId(open ? null : update.id)}
              aria-label={`${update.version} ${update.title_ko}`}
            >
              <span className="ver">{update.version}</span>
              <span className="um">
                <b>{update.title_ko}</b>
              </span>
              <span className="ud">
                {update.release_date_kst ?? ""}
                <span className="arw">→</span>
              </span>
            </button>
            <div className="acc-panel">
              <div className="acc-inner">
                <div className={`acc-media${update.image_url ? " has-bg" : ""}`}>
                  {update.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img className="acc-bg" src={`${API_BASE_URL}${update.image_url}`} alt="" loading="lazy" />
                  ) : null}
                  <div className="acc-body">
                    <p>{update.summary_ko}</p>
                    {update.highlights_ko.length > 0 || update.source_links.length > 0 ? (
                      <div className="tags">
                        {update.highlights_ko.map((highlight) => (
                          <span key={highlight} className="tag">
                            {highlight}
                          </span>
                        ))}
                        {update.source_links.map((source, index, arr) => (
                          <a key={source} href={source} target="_blank" rel="noreferrer" className="tag src">
                            {t.updates.source}
                            {arr.length > 1 ? ` ${index + 1}` : ""} →
                          </a>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
          </div>
        );
      })}
    </>
  );
}
