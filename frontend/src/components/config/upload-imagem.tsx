"use client";

import { Loader2, Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { EditorImagem } from "@/components/config/editor-imagem";
import { api, mensagemErro } from "@/lib/api";
import type { EdicaoImagem } from "@/lib/tipos";

export function UploadImagem({
  titulo,
  descricao,
  url,
  urlOriginal,
  endpoint,
  onMudou,
  edicao,
  onEditar,
  permitirDesligarFundo,
}: {
  titulo: string;
  descricao: string;
  /** ja com o token na query string */
  url: string | null;
  urlOriginal?: string | null;
  endpoint: string;
  onMudou: () => void;
  /** presente = a imagem e editavel e o editor aparece abaixo do preview */
  edicao?: EdicaoImagem;
  onEditar?: (e: EdicaoImagem) => Promise<void>;
  permitirDesligarFundo?: boolean;
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
            rotulo={urlOriginal ? "Depois (editada)" : "Enviada"}
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

      {url && edicao && onEditar && (
        <EditorImagem
          valor={edicao}
          urlOriginal={urlOriginal ?? url}
          onAplicar={onEditar}
          permitirDesligarFundo={permitirDesligarFundo}
        />
      )}
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
