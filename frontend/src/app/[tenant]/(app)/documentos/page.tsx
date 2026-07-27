"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertCircle,
  CheckCircle2,
  Download,
  Eye,
  FileSignature,
  Loader2,
  Mail,
  Paperclip,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Stamp,
  Trash2,
  X,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { ModalEmail } from "@/components/documentos/modal-email";
import { ModalUpload } from "@/components/documentos/modal-upload";
import {
  ModalConfirmar,
  ModalPreview,
  ModalRenomear,
} from "@/components/documentos/modais";
import { api, mensagemErro } from "@/lib/api";
import {
  CLASSE_STATUS,
  ROTULO_STATUS,
  formatarData,
  formatarTamanho,
  type Documento,
  type Resumo,
  type StatusDocumento,
} from "@/lib/documentos";
import type { Configuracao } from "@/lib/tipos";
import { cn } from "@/lib/utils";
import { useAuth } from "@/store/auth";

type Acao =
  | { tipo: "preview"; doc: Documento }
  | { tipo: "email"; doc: Documento }
  | { tipo: "excluir"; doc: Documento }
  | { tipo: "reprocessar"; doc: Documento }
  | { tipo: "renomear"; doc: Documento }
  | null;

const STATUS_FILTRO: { valor: StatusDocumento | ""; rotulo: string }[] = [
  { valor: "", rotulo: "Todos os status" },
  { valor: "enviado", rotulo: "Na fila" },
  { valor: "processando", rotulo: "Processando" },
  { valor: "pronto", rotulo: "Pronto" },
  { valor: "enviado_email", rotulo: "Enviado por email" },
  { valor: "erro", rotulo: "Erro" },
];

export default function DocumentosPage() {
  const { tenant } = useParams<{ tenant: string }>();
  const qc = useQueryClient();
  const token = useAuth((s) => s.token);

  const [modalUpload, setModalUpload] = useState(false);
  const [acao, setAcao] = useState<Acao>(null);

  const [busca, setBusca] = useState("");
  const [buscaAplicada, setBuscaAplicada] = useState("");
  const [status, setStatus] = useState<StatusDocumento | "">("");
  const [de, setDe] = useState("");
  const [ate, setAte] = useState("");

  // debounce: sem isso cada tecla vira uma consulta ao backend
  useEffect(() => {
    const t = setTimeout(() => setBuscaAplicada(busca), 350);
    return () => clearTimeout(t);
  }, [busca]);

  const filtros = { busca: buscaAplicada, status, de, ate };
  const temFiltro = !!(buscaAplicada || status || de || ate);

  const { data: resumo } = useQuery<Resumo>({
    queryKey: ["resumo", tenant],
    queryFn: async () => (await api.get(`/api/${tenant}/documentos/resumo`)).data,
    refetchInterval: 5000,
  });

  const { data: lista, isLoading } = useQuery<{ itens: Documento[]; total: number }>({
    queryKey: ["documentos", tenant, filtros],
    queryFn: async () =>
      (
        await api.get(`/api/${tenant}/documentos`, {
          params: {
            busca: buscaAplicada || undefined,
            status: status || undefined,
            de: de || undefined,
            ate: ate || undefined,
          },
        })
      ).data,
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

  function atualizar() {
    qc.invalidateQueries({ queryKey: ["documentos", tenant] });
    qc.invalidateQueries({ queryKey: ["resumo", tenant] });
  }

  const excluir = useMutation({
    mutationFn: async (id: number) => api.delete(`/api/${tenant}/documentos/${id}`),
    onSuccess: () => {
      toast.success("Documento excluido");
      setAcao(null);
      atualizar();
    },
    onError: (e) => toast.error(mensagemErro(e, "Nao foi possivel excluir")),
  });

  const reprocessar = useMutation({
    mutationFn: async (id: number) =>
      api.post(`/api/${tenant}/documentos/${id}/reprocessar`),
    onSuccess: () => {
      toast.success("Documento devolvido para a fila");
      setAcao(null);
      atualizar();
    },
    onError: (e) => toast.error(mensagemErro(e, "Nao foi possivel reprocessar")),
  });

  const renomear = useMutation({
    mutationFn: async ({ id, nome }: { id: number; nome: string }) =>
      api.patch(`/api/${tenant}/documentos/${id}`, { nome_original: nome }),
    onSuccess: () => {
      toast.success("Documento renomeado");
      setAcao(null);
      atualizar();
    },
    onError: (e) => toast.error(mensagemErro(e, "Nao foi possivel renomear")),
  });

  /** URL do arquivo com token na query — necessario para <iframe> e <a>. */
  const urlArquivo = (id: number, tipo: "final" | "original", inline = false) =>
    `${api.defaults.baseURL}/api/${tenant}/documentos/${id}/arquivo/${tipo}` +
    `?token=${token}${inline ? "&inline=true" : ""}`;

  function limparFiltros() {
    setBusca("");
    setBuscaAplicada("");
    setStatus("");
    setDe("");
    setAte("");
  }

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
          <h1 className="text-xl font-semibold tracking-tight text-dark">Documentos</h1>
          <p className="mt-1 text-sm text-dark/75">
            Envie um .docx e receba o PDF timbrado, rubricado e assinado.
          </p>
        </div>
        <button onClick={() => setModalUpload(true)} className="btn-primario shrink-0">
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
              <p className="mt-1 text-xs text-dark/70">{rotulo}</p>
            </div>
          </div>
        ))}
      </div>

      {/* ---------------- toolbar ---------------- */}
      <div className="cartao mb-4 flex flex-wrap items-end gap-3 p-4">
        <div className="min-w-[220px] flex-1">
          <label className="rotulo">Buscar</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-dark/50" />
            <input
              className="campo pl-9"
              placeholder="Nome do arquivo"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
            />
          </div>
        </div>

        <div>
          <label className="rotulo">Status</label>
          <select
            className="campo"
            value={status}
            onChange={(e) => setStatus(e.target.value as StatusDocumento | "")}
          >
            {STATUS_FILTRO.map((s) => (
              <option key={s.valor} value={s.valor}>
                {s.rotulo}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="rotulo">De</label>
          <input
            type="date"
            className="campo"
            value={de}
            onChange={(e) => setDe(e.target.value)}
          />
        </div>

        <div>
          <label className="rotulo">Ate</label>
          <input
            type="date"
            className="campo"
            value={ate}
            onChange={(e) => setAte(e.target.value)}
          />
        </div>

        {temFiltro && (
          <button
            onClick={limparFiltros}
            className="flex items-center gap-1.5 rounded-lg border border-dark/10 px-3 py-2.5
                       text-sm text-dark/80 transition hover:bg-cinza"
          >
            <X className="h-4 w-4" />
            Limpar
          </button>
        )}
      </div>

      {/* ---------------- tabela ---------------- */}
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
              {temFiltro ? "Nenhum resultado" : "Nenhum documento ainda"}
            </h2>
            <p className="mt-1.5 max-w-xs text-sm text-dark/70">
              {temFiltro
                ? "Ajuste a busca ou os filtros para encontrar o documento."
                : "Envie seu primeiro .docx e veja o pipeline montar o PDF timbrado."}
            </p>
            <button
              onClick={() => (temFiltro ? limparFiltros() : setModalUpload(true))}
              className="btn-primario mt-5"
            >
              {temFiltro ? (
                <>
                  <X className="h-4 w-4" />
                  Limpar filtros
                </>
              ) : (
                <>
                  <Plus className="h-4 w-4" />
                  Enviar o primeiro
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-dark/[.07] text-left text-xs uppercase tracking-wide text-dark/65">
                  <th className="px-5 py-3 font-medium">Arquivo</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Paginas</th>
                  <th className="px-5 py-3 font-medium">Tamanho</th>
                  <th className="px-5 py-3 font-medium">Enviado em</th>
                  <th className="px-5 py-3 text-right font-medium">Acoes</th>
                </tr>
              </thead>
              <tbody>
                {lista.itens.map((d) => {
                  const pronto = d.status === "pronto" || d.status === "enviado_email";
                  const naFila = d.status === "enviado" || d.status === "processando";

                  return (
                    <tr
                      key={d.id}
                      className="group border-b border-dark/[.05] transition last:border-0 hover:bg-cinza/60"
                    >
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-dark">{d.nome_original}</span>
                          {d.rubricado && (
                            <Stamp className="h-3.5 w-3.5 text-indigo" aria-label="Rubricado" />
                          )}
                        </div>
                        {d.status === "erro" && d.erro_msg && (
                          <p className="mt-0.5 max-w-md text-xs text-risco">{d.erro_msg}</p>
                        )}
                        {d.codigo_verificacao && (
                          <p className="mt-0.5 font-mono text-[11px] text-dark/55">
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
                          {naFila && <Loader2 className="h-3 w-3 animate-spin" />}
                          {ROTULO_STATUS[d.status]}
                        </span>
                      </td>

                      <td className="px-5 py-3.5 text-dark/80">{d.paginas ?? "—"}</td>
                      <td className="px-5 py-3.5 text-dark/80">
                        {formatarTamanho(d.tamanho)}
                      </td>
                      <td className="whitespace-nowrap px-5 py-3.5 text-dark/80">
                        {formatarData(d.criado_em)}
                      </td>

                      <td className="px-5 py-3.5">
                        <div className="flex items-center justify-end gap-0.5">
                          <BotaoAcao
                            titulo="Visualizar PDF"
                            desabilitado={!pronto}
                            onClick={() => setAcao({ tipo: "preview", doc: d })}
                          >
                            <Eye className="h-4 w-4" />
                          </BotaoAcao>

                          <BotaoAcao
                            titulo="Baixar PDF final"
                            desabilitado={!pronto}
                            href={pronto ? urlArquivo(d.id, "final") : undefined}
                          >
                            <Download className="h-4 w-4" />
                          </BotaoAcao>

                          <BotaoAcao
                            titulo="Baixar .docx original"
                            href={urlArquivo(d.id, "original")}
                          >
                            <Paperclip className="h-4 w-4" />
                          </BotaoAcao>

                          <BotaoAcao
                            titulo="Enviar por email"
                            desabilitado={!pronto}
                            onClick={() => setAcao({ tipo: "email", doc: d })}
                          >
                            <Mail className="h-4 w-4" />
                          </BotaoAcao>

                          <BotaoAcao
                            titulo="Renomear"
                            onClick={() => setAcao({ tipo: "renomear", doc: d })}
                          >
                            <Pencil className="h-4 w-4" />
                          </BotaoAcao>

                          <BotaoAcao
                            titulo="Reprocessar"
                            desabilitado={naFila}
                            onClick={() => setAcao({ tipo: "reprocessar", doc: d })}
                          >
                            <RefreshCw className="h-4 w-4" />
                          </BotaoAcao>

                          <BotaoAcao
                            titulo="Excluir"
                            perigo
                            onClick={() => setAcao({ tipo: "excluir", doc: d })}
                          >
                            <Trash2 className="h-4 w-4" />
                          </BotaoAcao>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {lista && lista.total > 0 && (
        <p className="mt-3 text-xs text-dark/62">
          {lista.itens.length} de {lista.total} documento
          {lista.total === 1 ? "" : "s"}
          {temFiltro && " (filtrado)"}
        </p>
      )}

      {/* ---------------- modais ---------------- */}
      {modalUpload && (
        <ModalUpload
          tenant={tenant}
          rubricarPadrao={config?.rubricar_por_padrao ?? false}
          aoFechar={() => {
            setModalUpload(false);
            atualizar();
          }}
        />
      )}

      {acao?.tipo === "preview" && (
        <ModalPreview
          doc={acao.doc}
          url={urlArquivo(acao.doc.id, "final", true)}
          aoFechar={() => setAcao(null)}
        />
      )}

      {acao?.tipo === "email" && (
        <ModalEmail
          tenant={tenant}
          doc={acao.doc}
          aoEnviado={() => {
            setAcao(null);
            atualizar();
          }}
          aoFechar={() => setAcao(null)}
        />
      )}

      {acao?.tipo === "excluir" && (
        <ModalConfirmar
          titulo="Excluir documento"
          mensagem={`"${acao.doc.nome_original}" sai da listagem. O arquivo original e a trilha de auditoria continuam guardados no servidor.`}
          rotuloAcao="Excluir"
          perigo
          ocupado={excluir.isPending}
          aoConfirmar={() => excluir.mutate(acao.doc.id)}
          aoFechar={() => setAcao(null)}
        />
      )}

      {acao?.tipo === "reprocessar" && (
        <ModalConfirmar
          titulo="Reprocessar documento"
          mensagem="O pipeline roda de novo a partir do .docx original, aplicando o cabecalho, o rodape e a assinatura atuais. O PDF anterior sera substituido."
          rotuloAcao="Reprocessar"
          ocupado={reprocessar.isPending}
          aoConfirmar={() => reprocessar.mutate(acao.doc.id)}
          aoFechar={() => setAcao(null)}
        />
      )}

      {acao?.tipo === "renomear" && (
        <ModalRenomear
          doc={acao.doc}
          ocupado={renomear.isPending}
          aoSalvar={(nome) => renomear.mutate({ id: acao.doc.id, nome })}
          aoFechar={() => setAcao(null)}
        />
      )}
    </div>
  );
}

function BotaoAcao({
  titulo,
  children,
  onClick,
  href,
  desabilitado,
  perigo,
}: {
  titulo: string;
  children: React.ReactNode;
  onClick?: () => void;
  href?: string;
  desabilitado?: boolean;
  perigo?: boolean;
}) {
  const classe = cn(
    "rounded-lg p-2 transition",
    desabilitado
      ? "cursor-not-allowed text-dark/15"
      : perigo
        ? "text-dark/62 hover:bg-risco/10 hover:text-risco"
        : "text-dark/62 hover:bg-navy/10 hover:text-navy",
  );

  if (href && !desabilitado) {
    return (
      <a href={href} title={titulo} aria-label={titulo} className={classe}>
        {children}
      </a>
    );
  }

  return (
    <button
      type="button"
      title={titulo}
      aria-label={titulo}
      disabled={desabilitado}
      onClick={onClick}
      className={classe}
    >
      {children}
    </button>
  );
}
