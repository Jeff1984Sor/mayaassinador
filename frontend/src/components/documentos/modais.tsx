"use client";

import { AlertTriangle, Loader2, X } from "lucide-react";
import { useState } from "react";

import type { Documento } from "@/lib/documentos";

function Moldura({
  titulo,
  subtitulo,
  largura = "max-w-md",
  aoFechar,
  children,
  rodape,
}: {
  titulo: string;
  subtitulo?: string;
  largura?: string;
  aoFechar: () => void;
  children: React.ReactNode;
  rodape: React.ReactNode;
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-dark/45 p-4"
      onClick={aoFechar}
    >
      <div
        className={`flex max-h-[92vh] w-full ${largura} flex-col rounded-xl bg-white shadow-xl`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-dark/[.07] px-6 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-dark">{titulo}</h2>
            {subtitulo && (
              <p className="mt-0.5 truncate text-xs text-dark/70">{subtitulo}</p>
            )}
          </div>
          <button
            onClick={aoFechar}
            className="ml-3 rounded-lg p-1 text-dark/55 transition hover:bg-cinza hover:text-dark/88"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-auto">{children}</div>

        <div className="flex justify-end gap-2 border-t border-dark/[.07] px-6 py-4">
          {rodape}
        </div>
      </div>
    </div>
  );
}

export function ModalPreview({
  doc,
  url,
  aoFechar,
}: {
  doc: Documento;
  url: string;
  aoFechar: () => void;
}) {
  return (
    <Moldura
      titulo={doc.nome_original}
      subtitulo={`${doc.paginas ?? "?"} paginas · codigo ${doc.codigo_verificacao ?? "—"}`}
      largura="max-w-4xl"
      aoFechar={aoFechar}
      rodape={
        <>
          <a
            href={url.replace("&inline=true", "")}
            className="rounded-lg px-4 py-2.5 text-sm text-dark/80 transition hover:bg-cinza"
          >
            Baixar
          </a>
          <button onClick={aoFechar} className="btn-primario">
            Fechar
          </button>
        </>
      }
    >
      {/* o navegador renderiza o PDF nativamente; nao carregamos visualizador */}
      <iframe src={url} title={doc.nome_original} className="h-[70vh] w-full bg-cinza" />
    </Moldura>
  );
}

export function ModalConfirmar({
  titulo,
  mensagem,
  rotuloAcao,
  perigo = false,
  ocupado = false,
  aoConfirmar,
  aoFechar,
}: {
  titulo: string;
  mensagem: string;
  rotuloAcao: string;
  perigo?: boolean;
  ocupado?: boolean;
  aoConfirmar: () => void;
  aoFechar: () => void;
}) {
  return (
    <Moldura
      titulo={titulo}
      aoFechar={aoFechar}
      rodape={
        <>
          <button
            onClick={aoFechar}
            className="rounded-lg px-4 py-2.5 text-sm text-dark/80 transition hover:bg-cinza"
          >
            Cancelar
          </button>
          <button
            onClick={aoConfirmar}
            disabled={ocupado}
            className={
              perigo
                ? "inline-flex items-center justify-center gap-2 rounded-lg bg-risco px-4 py-2.5 text-sm font-medium text-white transition hover:bg-risco/90 disabled:opacity-60"
                : "btn-primario"
            }
          >
            {ocupado && <Loader2 className="h-4 w-4 animate-spin" />}
            {rotuloAcao}
          </button>
        </>
      }
    >
      <div className="flex gap-3 px-6 py-5">
        {perigo && (
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-risco" />
        )}
        <p className="text-sm leading-relaxed text-dark/88">{mensagem}</p>
      </div>
    </Moldura>
  );
}

export function ModalRenomear({
  doc,
  ocupado = false,
  aoSalvar,
  aoFechar,
}: {
  doc: Documento;
  ocupado?: boolean;
  aoSalvar: (nome: string) => void;
  aoFechar: () => void;
}) {
  const [nome, setNome] = useState(doc.nome_original.replace(/\.docx$/i, ""));

  return (
    <Moldura
      titulo="Renomear documento"
      subtitulo="Muda so o rotulo na lista — o arquivo e o hash continuam os mesmos"
      aoFechar={aoFechar}
      rodape={
        <>
          <button
            onClick={aoFechar}
            className="rounded-lg px-4 py-2.5 text-sm text-dark/80 transition hover:bg-cinza"
          >
            Cancelar
          </button>
          <button
            onClick={() => aoSalvar(nome)}
            disabled={!nome.trim() || ocupado}
            className="btn-primario"
          >
            {ocupado && <Loader2 className="h-4 w-4 animate-spin" />}
            Salvar
          </button>
        </>
      }
    >
      <div className="px-6 py-5">
        <label className="rotulo">Nome do documento</label>
        <div className="flex items-center gap-2">
          <input
            autoFocus
            className="campo"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && nome.trim() && aoSalvar(nome)}
          />
          <span className="font-mono text-sm text-dark/62">.docx</span>
        </div>
      </div>
    </Moldura>
  );
}
