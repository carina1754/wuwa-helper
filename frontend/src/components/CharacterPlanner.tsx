"use client";

import { useEffect, useMemo, useState } from "react";
import { getCharacters } from "@/lib/api";
import { ROLES } from "@/lib/constants";
import { useLanguage } from "@/lib/i18n";
import type { CharacterCatalogItem } from "@/lib/types";

export function CharacterPlanner() {
  const { t } = useLanguage();
  const [characters, setCharacters] = useState<CharacterCatalogItem[]>([]);
  const [search, setSearch] = useState("");
  const [role, setRole] = useState("");
  const [element, setElement] = useState("");
  const [error, setError] = useState("");

  function translateElement(value: string) {
    return (t.elements as Record<string, string>)[value] ?? value;
  }

  function translateWeaponType(value: string) {
    return (t.weaponTypes as Record<string, string>)[value] ?? value;
  }

  function translateStatName(value: string) {
    return (t.statNames as Record<string, string>)[value] ?? value;
  }

  function translateSonataSet(value: string) {
    return (t.sonataSets as Record<string, string>)[value] ?? value;
  }

  function translateWeaponName(value: string) {
    return (t.weaponNames as Record<string, string>)[value] ?? value;
  }

  function translateCharacterName(value: string) {
    return (t.characterNames as Record<string, string>)[value] ?? value;
  }

  useEffect(() => {
    getCharacters()
      .then(setCharacters)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const elements = useMemo(() => {
    return Array.from(new Set(characters.map((character) => character.element).filter(Boolean))).sort() as string[];
  }, [characters]);

  const filteredCharacters = useMemo(() => {
    const query = search.trim().toLowerCase();
    return characters.filter((character) => {
      const matchesSearch = !query || character.name.toLowerCase().includes(query);
      const matchesRole = !role || character.role === role;
      const matchesElement = !element || character.element === element;
      return matchesSearch && matchesRole && matchesElement;
    });
  }, [characters, element, role, search]);

  return (
    <section className="grid gap-4">
      <div className="rounded-md border border-slate-200 bg-white p-4 shadow-panel">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-950">{t.planner.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{t.planner.body}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <input
              className="min-h-10 rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder={t.planner.search}
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <select className="min-h-10 rounded-md border border-slate-300 px-3 py-2 text-sm" value={role} onChange={(event) => setRole(event.target.value)}>
              <option value="">{t.planner.allRoles}</option>
              {ROLES.map((item) => (
                <option key={item} value={item}>
                  {t.roles[item]}
                </option>
              ))}
            </select>
            <select className="min-h-10 rounded-md border border-slate-300 px-3 py-2 text-sm" value={element} onChange={(event) => setElement(event.target.value)}>
              <option value="">{t.planner.allElements}</option>
              {elements.map((item) => (
                <option key={item} value={item}>
                  {translateElement(item)}
                </option>
              ))}
            </select>
          </div>
        </div>
        {error ? <p className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-900">{error}</p> : null}
      </div>

      {filteredCharacters.length === 0 ? (
        <div className="rounded-md border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">{t.planner.noResults}</div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filteredCharacters.map((character) => (
            <article key={character.id} className="overflow-hidden rounded-md border border-slate-200 bg-white shadow-panel">
              {character.splash_image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={character.splash_image} alt="" className="w-full bg-slate-50 object-contain" style={{ aspectRatio: "696 / 960" }} />
              ) : null}
              <div className="grid gap-3 p-4">
                <div className="flex items-start gap-3">
                  {character.image ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={character.image} alt="" className="h-14 w-14 rounded-md object-cover" />
                  ) : null}
                  <div className="min-w-0">
                    <h3 className="truncate text-base font-semibold text-slate-950">{translateCharacterName(character.name)}</h3>
                    <p className="mt-1 text-sm text-slate-500">
                      {character.rarity}★ · {translateElement(character.element)} · {translateWeaponType(character.weapon_type)} · {t.roles[character.role]}
                    </p>
                  </div>
                </div>
                <dl className="grid gap-2 text-sm text-slate-700">
                  <div>
                    <dt className="font-medium text-slate-950">{t.planner.recommendedSet}</dt>
                    <dd>{character.default_sonata ? translateSonataSet(character.default_sonata) : "-"}</dd>
                  </div>
                  {character.sonata_fallbacks.length > 0 ? (
                    <div>
                      <dt className="font-medium text-slate-950">{t.planner.fallbackSets}</dt>
                      <dd>{character.sonata_fallbacks.map(translateSonataSet).join(", ")}</dd>
                    </div>
                  ) : null}
                  <div>
                    <dt className="font-medium text-slate-950">{t.planner.weapon}</dt>
                    <dd>{character.default_weapon ? translateWeaponName(character.default_weapon) : "-"}</dd>
                  </div>
                  <div>
                    <dt className="font-medium text-slate-950">{t.planner.bonusStats}</dt>
                    <dd>{character.bonus_stats.length ? character.bonus_stats.map(translateStatName).join(", ") : "-"}</dd>
                  </div>
                </dl>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
