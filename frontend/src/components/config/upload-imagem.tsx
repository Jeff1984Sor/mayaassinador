"use client";

import { Loader2, Trash2, Upload } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { api, mensagemErro } from "@/lib/api";

export const TOLERANCIA_MAXIMA = 120;

export function UploadImagem({
  titulo,
  descricao,
  url,
  urlOriginal,
  endpoint,
  onMudou,
  tolerancia,
  onTolerancia,
}: {
  titulo: string;
  descricao: string;
  /** ja com o token na query string */
  url: string | null;
  urlOriginal?: string | null;
  endpoint: string;
  onMudou: () => void;
  /** presente = a imagem passa por remocao de fundo e o slider aparece */
  tolerancia?: number;
  onTolerancia?: (v: number) => Promise<void>;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [ocupado, setOcupado] = useState(false);

  async function enviar(arquivo: File) {
    const form = new FormData();
    form.append("arquivo", arquivo);
    setOcupado(true);
    try {
      await api.post(endpoint, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(`${titulo} atualizada`);
      onMudou();
    } catch (e) {
      toast.error(mensagemErro(e, "Nao foi possivel enviar a imagem"));
    } finally {
      setOcupado(false);
      if (input.current) input.current.value = "";
    }
  }

  async function remover() {
    setOcupado(true);
    try {
      await api.delete(endpoint);
      toast.success(`${titulo} removida`);
      onMudou();
    } catch (e) {
      toast.error(mensagemErro(e));
    } finally {
      setOcupado(false);
    }
  }

  return (
    <div className="rounded-lg border border-dark/[.08] p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-dark">{titulo}</p>
          <p className="text-xs text-dark/65">{descricao}</p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button
            type="button"
            onClick={() => input.current?.click()}
            disabled={ocupado}
            className="inline-flex items-center gap-1.5 rounded-lg border border-dark/10 px-3 py-1.5
                       text-xs font-medium text-dark/88 transition hover:bg-cinza disabled:opacity-50"
          >
            {ocupado ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Upload className="h-3.5 w-3.5" />
            )}
            Enviar
          </button>
          {url && (
            <button
              type="button"
              onClick={remover}
              disabled={ocupado}
              className="rounded-lg border border-dark/10 px-2.5 py-1.5 text-risco
                         transition hover:bg-risco/5 disabled:opacity-50"
              aria-label="Remover"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>

      <input
        ref={input}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void enviar(f);
        }}
      />

      {url ? (
        <div className="grid grid-cols-2 gap-3">
          {urlOriginal && (
            <Quadro rotulo="Antes (original)" src={urlOriginal} xadrez={false} />
          )}
          <Quadro
            rotulo={urlOriginal ? "Depois (fundo removido)" : "Enviada"}
            src={url}
            xadrez={!!urlOriginal}
          />
        </div>
      ) : (

        <div className="flex h-24 items-center justify-center rounded-lg border border-dashed
                        border-dark/15 text-xs text-dark/55">
          Nenhuma imagem enviada
        </div>
      )}

      {url && tolerancia !== undefined && onTolerancia && (
        <AjusteFundo valor={tolerancia} onAplicar={onTolerancia} />
      )}
    </div>
  );
}

/** Slider da forca da remocao de fundo, com aplicacao no servidor.
 *
 * O recorte roda no Pillow, nao no navegador: refazer o mesmo algoritmo em
 * canvas so criaria uma segunda verdade, e o preview passaria a divergir do
 * PDF — o mesmo erro que o `linhasEscritorio` duplicado ja custou caro.
 * Em troca, cada passo custa uma ida ao servidor; dai o debounce.
 */
function AjusteFundo({
  valor,
  onAplicar,
}: {
  valor: number;
  onAplicar: (v: number) => Promise<void>;
}) {
  const [local, setLocal] = useState(valor);
  const [aplicando, setAplicando] = useState(false);

  // o valor de fora manda quando a imagem e trocada ou recarregada
  useEffect(() => setLocal(valor), [valor]);

  useEffect(() => {
    if (local === valor) return;
    const t = setTimeout(async () => {
      setAplicando(true);
      try {
        await onAplicar(local);
      } finally {
        setAplicando(false);
      }
    }, 450);
    return () => clearTimeout(t);
    // onAplicar muda a cada render do pai; segui-lo reiniciaria o debounce
    // para sempre e o slider nunca aplicaria nada
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [local, valor]);

  return (
    <div className="mt-3 border-t border-dark/[.07] pt-3">
      <div className="flex items-baseline justify-between gap-2">
        <label className="rotulo">Forca da remocao de fundo</label>
        {aplicando && (
          <span className="flex items-center gap-1 text-xs text-dark/65">
            <Loader2 className="h-3 w-3 animate-spin" />
            aplicando
          </span>
        )}
      </div>

      <div className="flex items-center gap-3">
        <input
          type="range"
          className="h-1.5 flex-1 cursor-pointer accent-indigo"
          min={0}
          max={TOLERANCIA_MAXIMA}
          value={local}
          onChange={(e) => setLocal(Number(e.target.value))}
        />
        <span className="w-8 shrink-0 text-center text-xs tabular-nums text-dark/65">
          {local}
        </span>
      </div>

      <p className="mt-1 text-xs text-dark/65">
        Menor tira so o branco puro; maior alcanca o cinza do papel escaneado.
        Se o traco comecar a sumir, volte. Cada ajuste parte do original, entao
        da para ir e voltar sem estragar a imagem.
      </p>
    </div>
  );
}

function Quadro({
  rotulo,
  src,
  xadrez,
}: {
  rotulo: string;
  src: string;
  xadrez: boolean;
}) {
  return (
    <div>
      <p className="mb-1 text-[11px] uppercase tracking-wide text-dark/62">
        {rotulo}
      </p>
      <div
        className="flex h-24 items-center justify-center rounded-lg border border-dark/[.08] p-2"
        style={
          xadrez
            ? {
                // xadrez revela a transparencia — sem isso, "fundo removido"
                // fica indistinguivel de "fundo branco"
                backgroundImage:
                  "repeating-conic-gradient(#eceef4 0% 25%, #fff 0% 50%)",
                backgroundSize: "12px 12px",
              }
            : { background: "#fff" }
        }
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={src} alt="" className="max-h-full max-w-full object-contain" />
      </div>
    </div>
  );
}
