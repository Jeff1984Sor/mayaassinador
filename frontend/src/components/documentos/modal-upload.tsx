"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  FileText,
  Loader2,
  UploadCloud,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { StepperPipeline } from "@/components/documentos/stepper-pipeline";
import { api, mensagemErro } from "@/lib/api";
import { formatarTamanho, type Documento, type DocumentoDetalhe } from "@/lib/documentos";
import { cn } from "@/lib/utils";

const MAX_MB = 20;

export function ModalUpload({
  tenant,
  rubricarPadrao,
  aoFechar,
}: {
  tenant: string;
  rubricarPadrao: boolean;
  aoFechar: () => void;
}) {
  const qc = useQueryClient();
  const input = useRef<HTMLInputElement>(null);

  const [arquivo, setArquivo] = useState<File | null>(null);
  const [rubricar, setRubricar] = useState(rubricarPadrao);
  const [arrastando, setArrastando] = useState(false);
  const [documentoId, setDocumentoId] = useState<number | null>(null);

  // Polling: so enquanto o documento nao chegou a um estado final.
  const { data: doc } = useQuery<DocumentoDetalhe>({
    queryKey: ["documento", tenant, documentoId],
    queryFn: async () =>
      (await api.get(`/api/${tenant}/documentos/${documentoId}`)).data,
    enabled: documentoId !== null,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "pronto" || s === "erro" || s === "enviado_email" ? false : 1200;
    },
  });

  useEffect(() => {
    if (doc?.status === "pronto") {
      toast.success("Documento pronto!");
      qc.invalidateQueries({ queryKey: ["documentos", tenant] });
      qc.invalidateQueries({ queryKey: ["resumo", tenant] });
    }
    if (doc?.status === "erro") {
      qc.invalidateQueries({ queryKey: ["documentos", tenant] });
      qc.invalidateQueries({ queryKey: ["resumo", tenant] });
    }
  }, [doc?.status, qc, tenant]);

  const enviar = useMutation({
    mutationFn: async () => {
      const form = new FormData();
      form.append("arquivo", arquivo!);
      form.append("rubricar", String(rubricar));
      const { data } = await api.post<Documento>(
        `/api/${tenant}/documentos`,
        form,
        { headers: { "Content-Type": "multipart/form-data" } },
      );
      return data;
    },
    onSuccess: (d) => {
      setDocumentoId(d.id);
      qc.invalidateQueries({ queryKey: ["documentos", tenant] });
    },
    onError: (e) => toast.error(mensagemErro(e, "Falha no upload")),
  });

  function selecionar(f: File | undefined) {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith(".docx")) {
      toast.error("Apenas arquivos .docx sao aceitos");
      return;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      toast.error(`Arquivo maior que ${MAX_MB}MB`);
      return;
    }
    setArquivo(f);
  }

  const processando = documentoId !== null;
  const finalizado = doc?.status === "pronto" || doc?.status === "erro";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-dark/45 p-4"
      onClick={() => (!processando || finalizado) && aoFechar()}
    >
      <div
        className="w-full max-w-lg rounded-xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between border-b border-dark/[.07] px-6 py-4">
          <div>
            <h2 className="text-base font-semibold text-dark">
              {processando ? "Processando documento" : "Novo documento"}
            </h2>
            <p className="mt-0.5 text-xs text-dark/50">
              {processando
                ? arquivo?.name
                : "Envie um .docx e receba o PDF timbrado e assinado"}
            </p>
          </div>
          {(!processando || finalizado) && (
            <button
              onClick={aoFechar}
              className="rounded-lg p-1 text-dark/35 transition hover:bg-cinza hover:text-dark/70"
            >
              <X className="h-4.5 w-4.5" />
            </button>
          )}
        </div>

        <div className="px-6 py-5">
          {!processando ? (
            <>
              <div
                onDragOver={(e) => {
                  e.preventDefault();
                  setArrastando(true);
                }}
                onDragLeave={() => setArrastando(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setArrastando(false);
                  selecionar(e.dataTransfer.files?.[0]);
                }}
                onClick={() => input.current?.click()}
                className={cn(
                  "flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition",
                  arrastando
                    ? "border-indigo bg-indigo/5"
                    : arquivo
                      ? "border-teal/40 bg-teal/5"
                      : "border-dark/12 hover:border-navy/30 hover:bg-cinza",
                )}
              >
                {arquivo ? (
                  <>
                    <FileText className="mb-2 h-8 w-8 text-teal" />
                    <p className="text-sm font-medium text-dark">{arquivo.name}</p>
                    <p className="mt-0.5 text-xs text-dark/45">
                      {formatarTamanho(arquivo.size)} · clique para trocar
                    </p>
                  </>
                ) : (
                  <>
                    <UploadCloud className="mb-2 h-8 w-8 text-navy/35" />
                    <p className="text-sm font-medium text-dark">
                      Arraste o arquivo aqui
                    </p>
                    <p className="mt-0.5 text-xs text-dark/45">
                      ou clique para escolher · .docx ate {MAX_MB}MB
                    </p>
                  </>
                )}
              </div>

              <input
                ref={input}
                type="file"
                accept=".docx"
                className="hidden"
                onChange={(e) => selecionar(e.target.files?.[0])}
              />

              <label className="mt-4 flex cursor-pointer items-start gap-2.5 rounded-lg border border-dark/[.08] p-3">
                <input
                  type="checkbox"
                  checked={rubricar}
                  onChange={(e) => setRubricar(e.target.checked)}
                  className="mt-0.5 h-4 w-4 accent-navy"
                />
                <span>
                  <span className="text-sm text-dark/85">
                    Rubricar todas as paginas
                  </span>
                  <span className="block text-xs text-dark/45">
                    Carimba a rubrica cadastrada no canto de cada pagina.
                  </span>
                </span>
              </label>
            </>
          ) : (
            <>
              <StepperPipeline doc={doc ?? ({ eventos: [], status: "enviado", rubricado: rubricar } as never)} />

              {doc?.status === "pronto" && (
                <div className="mt-4 flex items-start gap-2.5 rounded-lg bg-teal/10 px-3.5 py-3">
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-teal" />
                  <div className="text-xs text-teal">
                    <p className="font-medium">PDF gerado com sucesso</p>
                    <p className="mt-0.5 opacity-80">
                      {doc.paginas} pagina{doc.paginas === 1 ? "" : "s"} ·{" "}
                      {formatarTamanho(doc.tamanho)} · codigo{" "}
                      <span className="font-mono">{doc.codigo_verificacao}</span>
                    </p>
                  </div>
                </div>
              )}

              {doc?.status === "erro" && (
                <div className="mt-4 flex items-start gap-2.5 rounded-lg bg-risco/10 px-3.5 py-3">
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-risco" />
                  <div className="text-xs text-risco">
                    <p className="font-medium">Falha no processamento</p>
                    <p className="mt-0.5 opacity-85">{doc.erro_msg}</p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-dark/[.07] px-6 py-4">
          {!processando ? (
            <>
              <button
                onClick={aoFechar}
                className="rounded-lg px-4 py-2.5 text-sm text-dark/60 transition hover:bg-cinza"
              >
                Cancelar
              </button>
              <button
                onClick={() => enviar.mutate()}
                disabled={!arquivo || enviar.isPending}
                className="btn-primario"
              >
                {enviar.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Enviar e processar
              </button>
            </>
          ) : (
            <button
              onClick={aoFechar}
              disabled={!finalizado}
              className="btn-primario"
            >
              {finalizado ? "Concluir" : "Processando..."}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
