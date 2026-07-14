"use client";

import { useEffect, useState } from "react";
import { getModels } from "@/lib/api";
import { getNvidiaKey, getNvidiaModel, setNvidiaKey, setNvidiaModel } from "@/lib/settings";
import { useLanguage } from "@/lib/i18n";

/** 설정 탭: BYO NVIDIA API 키 입력 + 모델 선택. 값은 브라우저 localStorage 에만 저장. */
export function Settings() {
  const { t } = useLanguage();
  const [key, setKey] = useState("");
  const [model, setModel] = useState("");
  const [models, setModels] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [reveal, setReveal] = useState(false);

  useEffect(() => {
    setKey(getNvidiaKey());
    setModel(getNvidiaModel());
  }, []);

  const onKeyChange = (value: string) => {
    setKey(value);
    setNvidiaKey(value);
  };

  const onModelChange = (value: string) => {
    setModel(value);
    setNvidiaModel(value);
  };

  const loadModels = async () => {
    setLoading(true);
    setStatus("");
    try {
      const list = await getModels();
      setModels(list);
      setStatus(t.settings.modelsLoaded(list.length));
    } catch (e) {
      setStatus(e instanceof Error ? e.message : t.settings.modelsFailed);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid max-w-2xl gap-5">
      <div>
        <h2 className="text-lg font-semibold">{t.settings.title}</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-neutral-400">{t.settings.intro}</p>
      </div>

      <label className="grid gap-1">
        <span className="text-sm font-medium">{t.settings.nvidiaKeyLabel}</span>
        <div className="flex gap-2">
          <input
            type={reveal ? "text" : "password"}
            value={key}
            onChange={(e) => onKeyChange(e.target.value)}
            placeholder="nvapi-..."
            autoComplete="off"
            spellCheck={false}
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 font-mono text-sm dark:border-neutral-700 dark:bg-neutral-900"
          />
          <button
            type="button"
            onClick={() => setReveal((r) => !r)}
            className="rounded-md border border-slate-300 px-3 py-2 text-xs dark:border-neutral-700"
          >
            {reveal ? t.settings.hide : t.settings.show}
          </button>
        </div>
        <span className="text-xs text-slate-400 dark:text-neutral-500">
          {t.settings.nvidiaKeyHint}{" "}
          <a
            href="https://build.nvidia.com/"
            target="_blank"
            rel="noreferrer"
            className="text-indigo-600 underline dark:text-indigo-400"
          >
            build.nvidia.com
          </a>
        </span>
      </label>

      <div className="grid gap-1">
        <span className="text-sm font-medium">{t.settings.modelLabel}</span>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={loadModels}
            disabled={loading || !key.trim()}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
          >
            {loading ? t.settings.loading : t.settings.loadModels}
          </button>
          <select
            value={model}
            onChange={(e) => onModelChange(e.target.value)}
            className="min-w-0 flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm dark:border-neutral-700 dark:bg-neutral-900"
          >
            <option value="">{t.settings.modelPlaceholder}</option>
            {/* 저장된 모델이 방금 불러온 목록에 없을 수도 있으니 항상 노출 */}
            {model && !models.includes(model) ? <option value={model}>{model}</option> : null}
            {models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
        {status ? <span className="text-xs text-slate-500 dark:text-neutral-400">{status}</span> : null}
      </div>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600 dark:border-neutral-800 dark:bg-neutral-900 dark:text-neutral-300">
        <div className="font-medium">{t.settings.howtoTitle}</div>
        <ol className="mt-2 list-decimal pl-5">
          {t.settings.howto.map((step, i) => (
            <li key={i} className="mt-1">
              {step}
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

export default Settings;
