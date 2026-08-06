"use client";

import {
  Crop,
  Loader2,
  RotateCcw,
  RotateCw,
  Undo2,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { EdicaoImagem, Recorte } from "@/lib/tipos";
import { cn } from "@/lib/utils";

export const TOLERANCIA_MAXIMA = 120;

/** Editor de recorte, rotacao e remocao de fundo.
 *
 * Todo o processamento roda no Pillow, nao em canvas aqui: reimplementar o
 * algoritmo no cliente criaria uma segunda verdade e o preview passaria a
 * divergir do PDF. A tela so coleta a intencao — a caixa de recorte, o
 * angulo, a forca — e manda o estado inteiro para o servidor refazer tudo a
 * partir do original. Dai o debounce: cada mexida custa uma ida ao backend.
 */
export function EditorImagem({
  valor,
  urlOriginal,
  onAplicar,
  permitirDesligarFundo = false,
}: {
  valor: EdicaoImagem;
  /** o original, sem tratamento — e sobre ele que a caixa e desenhada */
  urlOriginal: string | null;
  onAplicar: (e: EdicaoImagem) => Promise<void>;
  /** o logo pode dispensar a remocao de fundo; assinatura e rubrica nao */
  permitirDesligarFundo?: boolean;
}) {
  const [local, setLocal] = useState<EdicaoImagem>(valor);
  const [aplicando, setAplicando] = useState(false);
  const [recortando, setRecortando] = useState(false);

  // O pai monta `valor` inline, entao ele e um objeto novo a cada render.
  // Comparar por identidade zeraria o editor no meio do arraste; o que
  // importa e o conteudo — dai a chave serializada.
  const chave = JSON.stringify(valor);

  // o valor de fora manda quando a imagem e trocada ou recarregada
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => setLocal(valor), [chave]);

  useEffect(() => {
    if (igual(local, valor)) return;
    const t = setTimeout(async () => {
      setAplicando(true);
      try {
        await onAplicar(local);
      } finally {
        setAplicando(false);
      }
    }, 450);
    return () => clearTimeout(t);
    // onAplicar tambem muda a cada render do pai; segui-lo reiniciaria o
    // debounce para sempre e nada seria aplicado
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [local, chave]);

  const mudar = (partes: Partial<EdicaoImagem>) =>
    setLocal((a) => ({ ...a, ...partes }));

  // -180..180 mantem o angulo dentro do que o backend aceita
  const girar = (graus: number) =>
    mudar({ rotacao: normalizar(local.rotacao + graus) });

  const limpo =
    local.rotacao === 0 && !local.recorte && local.tolerancia === 40;

  return (
    <div className="mt-3 space-y-3 border-t border-dark/[.07] pt-3">
      <div className="flex flex-wrap items-center gap-2">
        <Botao
          icone={<RotateCcw className="h-3.5 w-3.5" />}
          rotulo="Girar -90"
          onClick={() => girar(-90)}
        />
        <Botao
          icone={<RotateCw className="h-3.5 w-3.5" />}
          rotulo="Girar +90"
          onClick={() => girar(90)}
        />
        <Botao
          icone={<Crop className="h-3.5 w-3.5" />}
          rotulo={recortando ? "Concluir recorte" : "Recortar"}
          ativo={recortando}
          onClick={() => setRecortando((v) => !v)}
        />
        {local.recorte && (
          <Botao
            icone={<Undo2 className="h-3.5 w-3.5" />}
            rotulo="Limpar recorte"
            onClick={() => mudar({ recorte: null })}
          />
        )}

        <span className="ml-auto flex items-center gap-2">
          {aplicando && (
            <span className="flex items-center gap-1 text-xs text-dark/65">
              <Loader2 className="h-3 w-3 animate-spin" />
              aplicando
            </span>
          )}
          <button
            type="button"
            className="text-xs text-indigo hover:underline disabled:opacity-40 disabled:no-underline"
            disabled={limpo}
            onClick={() =>
              mudar({ rotacao: 0, recorte: null, tolerancia: 40 })
            }
          >
            Restaurar
          </button>
        </span>
      </div>

      {recortando && urlOriginal && (
        <SeletorRecorte
          src={urlOriginal}
          valor={local.recorte}
          onMudou={(r) => mudar({ recorte: r })}
        />
      )}

      <Deslizante
        rotulo="Angulo fino"
        valor={local.rotacao}
        min={-180}
        max={180}
        sufixo="°"
        onChange={(v) => mudar({ rotacao: v })}
      />

      {permitirDesligarFundo && (
        <label className="flex cursor-pointer items-center gap-2 text-sm text-dark">
          <input
            type="checkbox"
            className="h-4 w-4 accent-indigo"
            checked={local.remover_fundo}
            onChange={(e) => mudar({ remover_fundo: e.target.checked })}
          />
          Remover o fundo branco
        </label>
      )}

      {local.remover_fundo && (
        <>
          <Deslizante
            rotulo="Forca da remocao de fundo"
            valor={local.tolerancia}
            min={0}
            max={TOLERANCIA_MAXIMA}
            onChange={(v) => mudar({ tolerancia: v })}
          />
          <p className="text-xs text-dark/65">
            Menor tira so o branco puro; maior alcanca o cinza do papel
            escaneado. Se o traco comecar a sumir, volte.
          </p>
        </>
      )}

      <p className="text-xs text-dark/65">
        Cada ajuste parte do original guardado, entao da para ir e voltar sem
        estragar a imagem.
      </p>
    </div>
  );
}

/** Caixa de recorte desenhada por arraste, em fracao do lado da imagem.
 *
 * A fracao e o que permite desenhar sobre um preview de 300px e o corte sair
 * certo num arquivo de 1600px — a tela nunca precisa saber o tamanho real.
 */
function SeletorRecorte({
  src,
  valor,
  onMudou,
}: {
  src: string;
  valor: Recorte | null;
  onMudou: (r: Recorte | null) => void;
}) {
  const area = useRef<HTMLDivElement>(null);
  const inicio = useRef<{ x: number; y: number } | null>(null);
  const [arrastando, setArrastando] = useState<Recorte | null>(null);

  function posicao(e: React.PointerEvent) {
    const caixa = area.current!.getBoundingClientRect();
    return {
      x: limitar((e.clientX - caixa.left) / caixa.width),
      y: limitar((e.clientY - caixa.top) / caixa.height),
    };
  }

  function aoMover(e: React.PointerEvent) {
    if (!inicio.current) return;
    const p = posicao(e);
    setArrastando(retangulo(inicio.current, p));
  }

  function aoSoltar(e: React.PointerEvent) {
    if (!inicio.current) return;
    const r = retangulo(inicio.current, posicao(e));
    inicio.current = null;
    setArrastando(null);
    // um clique sem arraste nao e um recorte — seria cortar tudo fora
    onMudou(r.largura < 0.02 || r.altura < 0.02 ? null : r);
  }

  const caixa = arrastando ?? valor;

  return (
    <div>
      <div
        ref={area}
        className="relative select-none touch-none overflow-hidden rounded-lg border
                   border-dark/[.08] bg-white"
        onPointerDown={(e) => {
          (e.target as HTMLElement).setPointerCapture(e.pointerId);
          inicio.current = posicao(e);
          setArrastando(null);
        }}
        onPointerMove={aoMover}
        onPointerUp={aoSoltar}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt=""
          draggable={false}
          className="block max-h-56 w-full cursor-crosshair object-contain"
        />

        {caixa && (
          // a sombra gigante escurece tudo o que fica FORA da caixa, o que
          // mostra o resultado sem precisar recortar de verdade a cada
          // movimento do mouse
          <div
            className="pointer-events-none absolute border-2 border-white"
            style={{
              left: `${caixa.x * 100}%`,
              top: `${caixa.y * 100}%`,
              width: `${caixa.largura * 100}%`,
              height: `${caixa.altura * 100}%`,
              boxShadow: "0 0 0 9999px rgba(15,23,41,.45)",
            }}
          />
        )}
      </div>

      <p className="mt-1 text-xs text-dark/65">
        Arraste sobre a imagem para escolher a area. Um clique sem arraste
        limpa o recorte.
      </p>
    </div>
  );
}

function Deslizante({
  rotulo,
  valor,
  min,
  max,
  sufixo = "",
  onChange,
}: {
  rotulo: string;
  valor: number;
  min: number;
  max: number;
  sufixo?: string;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <label className="rotulo">{rotulo}</label>
      <div className="flex items-center gap-3">
        <input
          type="range"
          className="h-1.5 flex-1 cursor-pointer accent-indigo"
          min={min}
          max={max}
          value={valor}
          onChange={(e) => onChange(Number(e.target.value))}
        />
        <span className="w-12 shrink-0 text-center text-xs tabular-nums text-dark/65">
          {valor}
          {sufixo}
        </span>
      </div>
    </div>
  );
}

function Botao({
  icone,
  rotulo,
  onClick,
  ativo = false,
}: {
  icone: React.ReactNode;
  rotulo: string;
  onClick: () => void;
  ativo?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition",
        ativo
          ? "border-indigo bg-indigo/10 text-navy"
          : "border-dark/10 text-dark/88 hover:bg-cinza",
      )}
    >
      {icone}
      {rotulo}
    </button>
  );
}

const limitar = (v: number) => Math.min(1, Math.max(0, v));

/** Mantem o angulo em -180..180, que e a faixa aceita pelo backend. */
function normalizar(graus: number): number {
  const g = ((graus % 360) + 360) % 360;
  return g > 180 ? g - 360 : g;
}

function retangulo(
  a: { x: number; y: number },
  b: { x: number; y: number },
): Recorte {
  // arraste em qualquer direcao: o retangulo nasce dos extremos, nunca
  // com largura negativa
  return {
    x: Math.min(a.x, b.x),
    y: Math.min(a.y, b.y),
    largura: Math.abs(b.x - a.x),
    altura: Math.abs(b.y - a.y),
  };
}

function igual(a: EdicaoImagem, b: EdicaoImagem): boolean {
  return (
    a.remover_fundo === b.remover_fundo &&
    a.tolerancia === b.tolerancia &&
    a.rotacao === b.rotacao &&
    JSON.stringify(a.recorte) === JSON.stringify(b.recorte)
  );
}
