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

/** Controle de tamanho em pontos: arraste para ajustar, digite para precisar.
 *
 * O valor viaja em pontos porque e a unidade do PDF e do Word, mas ninguem
 * pensa em pontos — por isso mostramos o equivalente em milimetros ao lado.
 */
export function Tamanho({
  rotulo,
  descricao,
  valor,
  onChange,
  min,
  max,
  padrao,
}: {
  rotulo: string;
  descricao?: string;
  valor: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  padrao: number;
}) {
  // preso na faixa: o backend rejeita fora dela e o usuario perderia o salvamento
  const limitar = (v: number) => Math.min(max, Math.max(min, Math.round(v) || min));
  const mm = (valor / 72) * 25.4;

  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <label className="rotulo">{rotulo}</label>
        <button
          type="button"
          className="text-xs text-indigo hover:underline disabled:opacity-40 disabled:no-underline"
          disabled={valor === padrao}
          onClick={() => onChange(padrao)}
        >
          Restaurar padrao
        </button>
      </div>

      <div className="flex items-center gap-3">
        <input
          type="range"
          className="h-1.5 flex-1 cursor-pointer accent-indigo"
          min={min}
          max={max}
          value={valor}
          onChange={(e) => onChange(limitar(Number(e.target.value)))}
        />
        <input
          type="number"
          className="campo w-20 shrink-0 text-center"
          min={min}
          max={max}
          value={valor}
          onChange={(e) => onChange(limitar(Number(e.target.value)))}
        />
        <span className="w-16 shrink-0 text-xs text-dark/65">
          pt · {mm.toFixed(1)}mm
        </span>
      </div>

      {descricao && <p className="mt-1 text-xs text-dark/65">{descricao}</p>}
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
        <span className="text-sm text-dark/95">{rotulo}</span>
        {descricao && (
          <span className="block text-xs text-dark/65">{descricao}</span>
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
      <legend className="px-1.5 text-xs font-medium uppercase tracking-wide text-dark/65">
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
                    : "bg-white text-dark/70 hover:bg-cinza",
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
                valor.negrito ? "bg-navy text-white" : "bg-white text-dark/70 hover:bg-cinza",
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
                valor.italico ? "bg-navy text-white" : "bg-white text-dark/70 hover:bg-cinza",
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
            <span className="font-mono text-xs text-dark/65">{valor.cor}</span>
          </div>
        </div>
      </div>
    </fieldset>
  );
}
