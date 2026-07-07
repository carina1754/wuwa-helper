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
  const [selectedVersion, setSelectedVersion] = useState<string | null>(null);

  useEffect(() => {
    getUpdates()
      .then(setUpdates)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  // The featured card shows the selected version (default: the latest). Every
  // other version is listed below and can be clicked to become featured.
  const featured =
    (selectedVersion ? updates.find((update) => update.version === selectedVersion) : undefined) ?? updates[0];
  const archive = updates.filter((update) => update !== featured);
  const isLatest = Boolean(featured) && featured === updates[0];

  function selectVersion(version: string) {
    setSelectedVersion(version);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

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
            {isLatest ? (
              <span className="now">
                <i />
                {t.tabs.Updates}
              </span>
            ) : null}
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
                {featured.source_links.map((source, index) => (
                  <a key={source} href={source} target="_blank" rel="noreferrer" className="tag src">
                    {t.updates.source} {index + 1} →
                  </a>
                ))}
              </div>
            ) : null}
          </div>
        </article>
      ) : null}

      {updates.length === 0 && !error ? <div className="soon">{t.updates.empty}</div> : null}

      {archive.length > 0 ? <div className="arch">{t.tabs.Updates}</div> : null}
      {archive.map((update) => (
        <button
          key={update.id}
          type="button"
          className="urow"
          onClick={() => selectVersion(update.version)}
          aria-label={`${update.version} ${update.title_ko}`}
        >
          <span className="ver">{update.version}</span>
          <span className="um">
            <b>{update.title_ko}</b>
            <p>{update.summary_ko}</p>
          </span>
          <span className="ud">
            {update.release_date_kst ?? ""}
            <span className="arw">→</span>
          </span>
        </button>
      ))}
    </>
  );
}
