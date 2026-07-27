export type StatusDocumento =
  | "enviado"
  | "processando"
  | "pronto"
  | "enviado_email"
  | "erro";

export type Documento = {
  id: number;
  nome_original: string;
  status: StatusDocumento;
  rubricado: boolean;
  paginas: number | null;
  tamanho: number | null;
  hash_sha256: string | null;
  codigo_verificacao: string | null;
  erro_msg: string | null;
  criado_em: string;
  processado_em: string | null;
};

export type Evento = {
  id: number;
  tipo: string;
  detalhe: string | null;
  criado_em: string;
};

export type DocumentoDetalhe = Documento & { eventos: Evento[] };

export type Resumo = {
  total: number;
  prontos: number;
  enviados_email: number;
  com_erro: number;
  processando: number;
};

export const ROTULO_STATUS: Record<StatusDocumento, string> = {
  enviado: "Na fila",
  processando: "Processando",
  pronto: "Pronto",
  enviado_email: "Enviado por email",
  erro: "Erro",
};

/** classes do badge por status, na paleta MayaCorp */
export const CLASSE_STATUS: Record<StatusDocumento, string> = {
  enviado: "bg-dark/[.06] text-dark/60",
  processando: "bg-amber/15 text-amber",
  pronto: "bg-teal/15 text-teal",
  enviado_email: "bg-indigo/20 text-navy",
  erro: "bg-risco/15 text-risco",
};

export function formatarTamanho(bytes: number | null): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatarData(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Etapas do stepper. A API nao devolve "etapa atual": derivamos dos
 *  eventos ja registrados, que e a fonte de verdade da auditoria. */
export const ETAPAS = [
  { chave: "cabecalho_aplicado", rotulo: "Cabecalho" },
  { chave: "rodape_aplicado", rotulo: "Rodape" },
  { chave: "convertido_pdf", rotulo: "Conversao" },
  { chave: "rubrica_aplicada", rotulo: "Rubrica" },
  { chave: "assinatura_aplicada", rotulo: "Assinatura" },
  { chave: "pronto", rotulo: "Pronto" },
] as const;
