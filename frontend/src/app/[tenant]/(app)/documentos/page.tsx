"use client";

import { useQuery } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  FileSignature,
  Loader2,
  Mail,
  Plus,
  Stamp,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";

import { ModalUpload } from "@/components/documentos/modal-upload";
import { api } from "@/lib/api";
import {
  CLASSE_STATUS,
  ROTULO_STATUS,
  formatarData,
  formatarTamanho,
  type Documento,
  type Resumo,
} from "@/lib/documentos";
import type { Configuracao } from "@/lib/tipos";
import { cn } from "@/lib/utils";

export default function DocumentosPage() {
  const { tenant } = useParams<{ tenant: string }>();
  const [modalAberto, setModalAberto] = useState(false);

  const { data: resumo } = useQuery<Resumo>({
    queryKey: ["resumo", tenant],
    queryFn: async () => (await api.get(`/api/${tenant}/documentos/resumo`)).data,
    refetchInterval: 5000,
  });

  const { data: lista, isLoading } = useQuery<{ itens: Documento[]; total: number }>({
    queryKey: ["documentos", tenant],
    queryFn: async () => (await api.get(`/api/${tenant}/documentos`)).data,
    // enquanto houver algo na fila, a lista se atualiza sozinha
    refetchInterval: (q) =>
      q.state.data?.itens?.some(
        (d) => d.status === "enviado" || d.status === "processando",
      )
        ? 2000
        : false,
  });

  const { data: config } = useQuery<Configuracao>({
    queryKey: ["configuracao", tenant],
    queryFn: async () => (await api.get(`/api/${tenant}/configuracoes`)).data,
  });

  const cards = [
    { rotulo: "Total", valor: resumo?.total ?? 0, Icone: FileSignature, cor: "text-navy" },
    { rotulo: "Prontos", valor: resumo?.prontos ?? 0, Icone: CheckCircle2, cor: "text-teal" },
    { rotulo: "Enviados", valor: resumo?.enviados_email ?? 0, Icone: Mail, cor: "text-indigo" },
    { rotulo: "Com erro", valor: resumo?.com_erro ?? 0, Icone: AlertCircle, cor: "text-risco" },
  ];

  return (
    <div className="px-8 py-7">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-dark">
            Documentos
          </h1>
          <p className="mt-1 text-sm text-dark/55">
            Envie um .docx e receba o PDF timbrado, rubricado e assinado.
          </p>
        </div>
        <button onClick={() => setModalAberto(true)} className="btn-primario shrink-0">
          <Plus className="h-4 w-4" />
          Novo Documento
        </button>
      </header>

      <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map(({ rotulo, valor, Icone, cor }) => (
          <div key={rotulo} className="cartao flex items-center gap-3.5 px-5 py-4">
            <Icone className={cn("h-5 w-5 shrink-0", cor)} />
            <div>
              <p className="text-xl font-semibold leading-none text-dark">{valor}</p>
              <p className="mt-1 text-xs text-dark/50">{rotulo}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="cartao overflow-hidden">
        {isLoading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="h-5 w-5 animate-spin text-navy/40" />
          </div>
        ) : !lista?.itens.length ? (
          <div className="flex flex-col items-center px-6 py-16 text-center">
            <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-cinza">
              <FileSignature className="h-6 w-6 text-navy/45" />
            </div>
            <h2 className="text-base font-medium text-dark">
              Nenhum documento ainda
            </h2>
            <p className="mt-1.5 max-w-xs text-sm text-dark/50">
              Envie seu primeiro .docx e veja o pipeline montar o PDF timbrado.
            </p>
            <button
              onClick={() => setModalAberto(true)}
              className="btn-primario mt-5"
            >
              <Plus className="h-4 w-4" />
              Enviar o primeiro
            </button>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-dark/[.07] text-left text-xs uppercase tracking-wide text-dark/45">
                <th className="px-5 py-3 font-medium">Arquivo</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Paginas</th>
                <th className="px-5 py-3 font-medium">Tamanho</th>
                <th className="px-5 py-3 font-medium">Enviado em</th>
              </tr>
            </thead>
            <tbody>
              {lista.itens.map((d) => (
                <tr
                  key={d.id}
                  className="border-b border-dark/[.05] transition last:border-0 hover:bg-cinza/60"
                >
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-dark">{d.nome_original}</span>
                      {d.rubricado && (
                        <Stamp className="h-3.5 w-3.5 text-indigo" aria-label="Rubricado" />
                      )}
                    </div>
                    {d.status === "erro" && d.erro_msg && (
                      <p className="mt-0.5 text-xs text-risco">{d.erro_msg}</p>
                    )}
                    {d.codigo_verificacao && (
                      <p className="mt-0.5 font-mono text-[11px] text-dark/35">
                        {d.codigo_verificacao}
                      </p>
                    )}
                  </td>
                  <td className="px-5 py-3.5">
                    <span
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium",
                        CLASSE_STATUS[d.status],
                      )}
                    >
                      {(d.status === "enviado" || d.status === "processando") && (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      )}
                      {ROTULO_STATUS[d.status]}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-dark/60">{d.paginas ?? "—"}</td>
                  <td className="px-5 py-3.5 text-dark/60">
                    {formatarTamanho(d.tamanho)}
                  </td>
                  <td className="px-5 py-3.5 text-dark/60">
                    {formatarData(d.criado_em)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <p className="mt-4 text-xs text-dark/40">
        Downloads, preview, reprocessar e exclusao chegam na F4.
      </p>

      {modalAberto && (
        <ModalUpload
          tenant={tenant}
          rubricarPadrao={config?.rubricar_por_padrao ?? false}
          aoFechar={() => setModalAberto(false)}
        />
      )}
    </div>
  );
}
