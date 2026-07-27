"use client";

import { AlignCenter, AlignLeft, AlignRight, Bold, Italic } from "lucide-react";

import { cn } from "@/lib/utils";
import type { Alinhamento, Fonte, Tipografia } from "@/lib/tipos";

export function Campo({
  rotulo,
  valor,
  onChange,
  placeholder,
  tipo = "text",
  className,
  maxLength,
}: {
  rotulo: string;
  valor: string | null;
  onChange: (v: string) => void;
  placeholder?: string;
  tipo?: string;
  className?: string;
  maxLength?: number;
}) {
  return (
    <div className={className}>
      <label className="rotulo">{rotulo}</label>
      <input
        type={tipo}
        className="campo"
        placeholder={placeholder}
        maxLength={maxLength}
        value={valor ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

export function AreaTexto({
  rotulo,
  valor,
  onChange,
  placeholder,
  linhas = 3,
}: {
  rotulo: string;
  valor: string | null;
  onChange: (v: string) => void;
  placeholder?: string;
  linhas?: number;
}) {
  return (
    <div>
      <label className="rotulo">{rotulo}</label>
      <textarea
        className="campo resize-y"
        rows={linhas}
        placeholder={placeholder}
        value={valor ?? ""}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

export function Marcador({
  rotulo,
  descricao,
  marcado,
  onChange,
}: {
  rotulo: string;
  descricao?: string;
  marcado: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5 py-1.5">
      <input
        type="checkbox"
        checked={marcado}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 h-4 w-4 rounded border-dark/20 text-navy accent-navy"
      />
      <span>
        <span className="text-sm text-dark/85">{rotulo}</span>
        {descricao && (
          <span className="block text-xs text-dark/45">{descricao}</span>
        )}
      </span>
    </label>
  );
}

const ALINHAMENTOS: { valor: Alinhamento; Icone: typeof AlignLeft }[] = [
  { valor: "esquerda", Icone: AlignLeft },
  { valor: "centro", Icone: AlignCenter },
  { valor: "direita", Icone: AlignRight },
];

/** Editor de tipografia — usado identico no cabecalho e no rodape,
 *  cada um com seu proprio estado. */
export function EditorTipografia({
  titulo,
  valor,
  fontes,
  onChange,
}: {
  titulo: string;
  valor: Tipografia;
  fontes: Fonte[];
  onChange: (t: Tipografia) => void;
}) {
  const set = <K extends keyof Tipografia>(k: K, v: Tipografia[K]) =>
    onChange({ ...valor, [k]: v });

  return (
    <fieldset className="rounded-lg border border-dark/[.08] p-4">
      <legend className="px-1.5 text-xs font-medium uppercase tracking-wide text-dark/45">
        {titulo}
      </legend>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="rotulo">Fonte</label>
          <select
            className="campo"
            value={valor.fonte}
            onChange={(e) => set("fonte", e.target.value)}
          >
            {fontes.map((f) => (
              <option key={f.valor} value={f.valor}>
                {f.rotulo}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="rotulo">Tamanho (pt)</label>
          <input
            type="number"
            min={6}
            max={72}
            className="campo"
            value={valor.tamanho}
            onChange={(e) => set("tamanho", Number(e.target.value) || 10)}
          />
        </div>
      </div>

      <div className="mt-3 flex items-end gap-3">
        <div>
          <label className="rotulo">Alinhamento</label>
          <div className="flex overflow-hidden rounded-lg border border-dark/10">
            {ALINHAMENTOS.map(({ valor: a, Icone }) => (
              <button
                key={a}
                type="button"
                onClick={() => set("alinhamento", a)}
                className={cn(
                  "px-3 py-2.5 transition",
                  valor.alinhamento === a
                    ? "bg-navy text-white"
                    : "bg-white text-dark/50 hover:bg-cinza",
                )}
                aria-label={a}
              >
                <Icone className="h-4 w-4" />
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="rotulo">Estilo</label>
          <div className="flex overflow-hidden rounded-lg border border-dark/10">
            <button
              type="button"
              onClick={() => set("negrito", !valor.negrito)}
              className={cn(
                "px-3 py-2.5 transition",
                valor.negrito ? "bg-navy text-white" : "bg-white text-dark/50 hover:bg-cinza",
              )}
              aria-label="negrito"
            >
              <Bold className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => set("italico", !valor.italico)}
              className={cn(
                "px-3 py-2.5 transition",
                valor.italico ? "bg-navy text-white" : "bg-white text-dark/50 hover:bg-cinza",
              )}
              aria-label="italico"
            >
              <Italic className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="flex-1">
          <label className="rotulo">Cor</label>
          <div className="flex items-center gap-2">
            <input
              type="color"
              value={valor.cor}
              onChange={(e) => set("cor", e.target.value.toUpperCase())}
              className="h-[42px] w-12 cursor-pointer rounded-lg border border-dark/10 bg-white p-1"
            />
            <span className="font-mono text-xs text-dark/45">{valor.cor}</span>
          </div>
        </div>
      </div>
    </fieldset>
  );
}
