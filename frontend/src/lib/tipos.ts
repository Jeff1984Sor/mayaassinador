export type Alinhamento = "esquerda" | "centro" | "direita";
export type PosicaoLogo =
  | "esquerda"
  | "direita"
  | "acima"
  | "centro"
  | "sem_logo";

export type Tipografia = {
  fonte: string;
  tamanho: number;
  alinhamento: Alinhamento;
  negrito: boolean;
  italico: boolean;
  cor: string;
};

export type CabecalhoCampos = {
  razao_social: boolean;
  cnpj: boolean;
  oab: boolean;
  endereco: boolean;
  telefone: boolean;
  whatsapp: boolean;
  email: boolean;
  site: boolean;
};

export type Escritorio = {
  id: number;
  razao_social: string;
  nome_fantasia: string | null;
  cnpj: string | null;
  oab_numero: string | null;
  oab_seccional: string | null;
  signatario_nome: string | null;
  signatario_oab: string | null;
  logradouro: string | null;
  numero: string | null;
  complemento: string | null;
  bairro: string | null;
  cidade: string | null;
  uf: string | null;
  cep: string | null;
  telefone: string | null;
  whatsapp: string | null;
  email: string | null;
  site: string | null;
  logo_url: string | null;
};

export type Configuracao = {
  id: number;
  cabecalho_campos: CabecalhoCampos;
  cabecalho_tipografia: Tipografia;
  logo_posicao: PosicaoLogo;
  rodape_campos: CabecalhoCampos;
  rodape_texto: string | null;
  rodape_tipografia: Tipografia;
  rodape_numeracao: boolean;
  rodape_numeracao_alinhamento: Alinhamento;
  numeracao_local: "rodape" | "cabecalho";
  rubricar_por_padrao: boolean;
  qrcode_ativo: boolean;
  assinatura_modo: "fixa" | "ancora";
  assinatura_ancora: string | null;
  assinatura_relativa: "acima" | "abaixo";
  assinatura_deslocamento: number;
  rubrica_url: string | null;
  assinatura_url: string | null;
  rubrica_original_url: string | null;
  assinatura_original_url: string | null;
  smtp_host: string | null;
  smtp_porta: number | null;
  smtp_usuario: string | null;
  smtp_tls: boolean;
  smtp_senha_definida: boolean;
  email_remetente_nome: string | null;
  email_assunto_padrao: string | null;
  email_mensagem_padrao: string | null;
};

export type Fonte = { valor: string; rotulo: string };

/** Fontes do servidor -> pilha equivalente no navegador.
 *
 * Carlito e Caladea sao metricamente identicas a Calibri e Cambria, que e
 * justamente o que o Windows tem. Mapear assim faz o preview bater com o
 * PDF gerado pelo LibreOffice em vez de cair num fallback generico. */
export const PILHA_FONTE: Record<string, string> = {
  Arial: "Arial, Helvetica, sans-serif",
  "Times New Roman": "'Times New Roman', Times, serif",
  Georgia: "Georgia, serif",
  "Courier New": "'Courier New', Courier, monospace",
  Carlito: "Calibri, Carlito, sans-serif",
  Caladea: "Cambria, Caladea, Georgia, serif",
};

export const ALINHA_CSS: Record<Alinhamento, "left" | "center" | "right"> = {
  esquerda: "left",
  centro: "center",
  direita: "right",
};
