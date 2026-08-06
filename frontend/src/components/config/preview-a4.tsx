"use client";

import { useRef } from "react";

import {
  ALINHA_CSS,
  PILHA_FONTE,
  type Configuracao,
  type Escritorio,
  type Tipografia,
} from "@/lib/tipos";

/** A4 em pontos (72dpi): 595 x 842. Renderizamos numa largura fixa e
 *  deixamos o CSS escalar — assim tamanhos em pt viram px na proporcao
 *  certa e o preview bate com o PDF. */
const LARGURA_PT = 595;
const ALTURA_PT = 842;
const MARGEM_PT = 56; // ~2cm

/** Teto de largura dos carimbos, como fracao da altura escolhida.
 *  Espelha RAZAO_LARGURA_MAX em pdf_carimbo.py — manter as duas em sincronia,
 *  senao o preview volta a mentir sobre o tamanho do carimbo. */
const RAZAO_LARGURA_MAX = 3.45;

/** Dimensoes do carimbo a partir da altura configurada.
 *  `objectFit: contain` faz o papel do escalonamento proporcional do Pillow:
 *  a imagem cresce ate a altura pedida e recua se estourar a largura. */
function carimbo(altura: number, teto: number | null): React.CSSProperties {
  return {
    height: altura,
    maxWidth: teto ? altura * teto : undefined,
    objectFit: "contain",
  };
}

/** Faixa e padrao de cada carimbo, em pt.
 *
 * Fonte unica para a alca de arraste e para os sliders da aba — e a mesma
 * faixa validada nos Fields do backend (schemas/configuracao.py). */
export const LIMITES = {
  logo_altura: { min: 10, max: 120, padrao: 34 },
  rubrica_altura: { min: 10, max: 80, padrao: 26 },
  assinatura_altura: { min: 20, max: 200, padrao: 84 },
} as const;

export type CampoAltura = keyof typeof LIMITES;

/** Quem tem teto de largura e quem nao tem.
 *
 * O logo entra no .docx por `add_picture(height=...)`, que so fixa a altura e
 * deixa a largura acompanhar a proporcao — nao existe teto la, e inventar um
 * aqui encolheria no preview um logo largo que sairia inteiro no PDF. Rubrica
 * e assinatura passam pelo pdf_carimbo, que tem o teto. */
const TETO_LARGURA: Record<CampoAltura, number | null> = {
  logo_altura: null,
  rubrica_altura: RAZAO_LARGURA_MAX,
  assinatura_altura: RAZAO_LARGURA_MAX,
};

/** Imagem com alca de canto para redimensionar arrastando, como no Paint.
 *
 * A pagina inteira e desenhada em pt e escalada por CSS (`transform:
 * scale`), entao o arraste chega em pixels de tela: dividir pela escala e o
 * que faz 10px de mouse virarem os 10pt certos no PDF. Sem isso o carimbo
 * cresceria mais rapido ou mais devagar que a mao.
 */
function Redimensionavel({
  src,
  campo,
  altura,
  escala,
  onAltura,
  opacidade = 1,
}: {
  src: string;
  campo: CampoAltura;
  altura: number;
  escala: number;
  /** ausente = preview so de leitura, sem alca */
  onAltura?: (campo: CampoAltura, valor: number) => void;
  opacidade?: number;
}) {
  const inicio = useRef<{ x: number; y: number; altura: number } | null>(null);
  const { min, max } = LIMITES[campo];

  function aoMover(e: React.PointerEvent) {
    if (!inicio.current || !onAltura) return;
    const dy = (e.clientY - inicio.current.y) / escala;
    const dx = (e.clientX - inicio.current.x) / escala;
    // media entre os dois eixos: arrastar na diagonal do canto cresce junto,
    // que e o gesto que a pessoa espera do canto de uma imagem
    const delta = (dy + dx / (TETO_LARGURA[campo] ?? RAZAO_LARGURA_MAX)) / 2;
    const nova = Math.round(inicio.current.altura + delta);
    onAltura(campo, Math.min(max, Math.max(min, nova)));
  }

  return (
    <span style={{ position: "relative", display: "inline-block", lineHeight: 0 }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt=""
        draggable={false}
        style={{ ...carimbo(altura, TETO_LARGURA[campo]), opacity: opacidade }}
      />

      {onAltura && (
        <span
          role="slider"
          aria-label="Redimensionar"
          aria-valuenow={altura}
          aria-valuemin={min}
          aria-valuemax={max}
          tabIndex={0}
          onPointerDown={(e) => {
            (e.target as HTMLElement).setPointerCapture(e.pointerId);
            inicio.current = { x: e.clientX, y: e.clientY, altura };
          }}
          onPointerMove={aoMover}
          onPointerUp={() => {
            inicio.current = null;
          }}
          // teclado: a alca precisa funcionar sem mouse
          onKeyDown={(e) => {
            const passo = e.key === "ArrowUp" ? 1 : e.key === "ArrowDown" ? -1 : 0;
            if (!passo) return;
            e.preventDefault();
            onAltura(campo, Math.min(max, Math.max(min, altura + passo)));
          }}
          title={`${altura}pt — arraste para redimensionar`}
          // a alca vive dentro da pagina, que esta escalada por CSS: dividir
          // pela escala mantem o alvo do mesmo tamanho na tela em qualquer
          // zoom. Sem isso ela encolhe junto com a pagina e fica impossivel
          // de pegar.
          style={{
            position: "absolute",
            right: -5 / escala,
            bottom: -5 / escala,
            width: 9 / escala,
            height: 9 / escala,
            background: "#fff",
            borderStyle: "solid",
            borderWidth: 1.5 / escala,
            borderColor: "#7C8FFF",
            cursor: "nwse-resize",
            touchAction: "none",
          }}
        />
      )}
    </span>
  );
}

const LOREM_JURIDICO = [
  "EXCELENTISSIMO SENHOR DOUTOR JUIZ DE DIREITO DA VARA CIVEL DA COMARCA DE SAO PAULO",
  "FULANO DE TAL, brasileiro, casado, engenheiro, portador da cedula de identidade RG n. 00.000.000-0, inscrito no CPF sob o n. 000.000.000-00, residente e domiciliado nesta Capital, vem, respeitosamente, a presenca de Vossa Excelencia, por intermedio de seu advogado que esta subscreve, propor a presente",
  "ACAO DE COBRANCA",
  "em face de BELTRANO DE TAL, pelos fatos e fundamentos juridicos a seguir expostos.",
  "I - DOS FATOS. As partes celebraram, em data de 12 de marco, instrumento particular de prestacao de servicos, por meio do qual o requerente se obrigou a executar os servicos ali descritos, mediante contraprestacao pecuniaria.",
];

function estilo(t: Tipografia): React.CSSProperties {
  return {
    fontFamily: PILHA_FONTE[t.fonte] ?? PILHA_FONTE.Arial,
    fontSize: `${t.tamanho}pt`,
    textAlign: ALINHA_CSS[t.alinhamento],
    fontWeight: t.negrito ? 700 : 400,
    fontStyle: t.italico ? "italic" : "normal",
    color: t.cor,
    lineHeight: 1.35,
  };
}

/** Monta linhas a partir dos Dados do Escritorio, respeitando os checkboxes.
 *  Serve cabecalho e rodape. Mesma regra que o python-docx aplicara
 *  (`linhas_escritorio` em docx_timbre.py) — manter as duas em sincronia. */
export function linhasEscritorio(
  esc: Escritorio | undefined,
  campos: Configuracao["cabecalho_campos"],
): string[] {
  if (!esc) return [];
  const linhas: string[] = [];

  if (campos.razao_social) linhas.push(esc.razao_social);

  const identidade: string[] = [];
  if (campos.cnpj && esc.cnpj) identidade.push(`CNPJ ${esc.cnpj}`);
  if (campos.oab && esc.oab_numero) {
    identidade.push(
      `OAB ${esc.oab_numero}${esc.oab_seccional ? `/${esc.oab_seccional}` : ""}`,
    );
  }
  if (identidade.length) linhas.push(identidade.join(" · "));

  if (campos.endereco) {
    const rua = [esc.logradouro, esc.numero].filter(Boolean).join(", ");
    const local = [esc.bairro, esc.cidade, esc.uf].filter(Boolean).join(" - ");
    const endereco = [rua, local, esc.cep].filter(Boolean).join(" · ");
    if (endereco) linhas.push(endereco);
  }

  const contato: string[] = [];
  if (campos.telefone && esc.telefone) contato.push(esc.telefone);
  if (campos.whatsapp && esc.whatsapp) contato.push(`WhatsApp ${esc.whatsapp}`);
  if (campos.email && esc.email) contato.push(esc.email);
  if (campos.site && esc.site) contato.push(esc.site);
  if (contato.length) linhas.push(contato.join(" · "));

  return linhas;
}

function Cabecalho({
  config,
  escritorio,
  logoSrc,
  numeracao,
  escala,
  onAltura,
}: {
  config: Configuracao;
  escritorio?: Escritorio;
  logoSrc: string | null;
  numeracao?: React.ReactNode;
  escala: number;
  onAltura?: (campo: CampoAltura, valor: number) => void;
}) {
  const linhas = linhasEscritorio(escritorio, config.cabecalho_campos);
  const t = config.cabecalho_tipografia;
  const pos = config.logo_posicao;
  const temLogo = pos !== "sem_logo" && !!logoSrc;

  // em "centro" o texto acompanha o logo, ignorando o alinhamento da tipografia
  const alinhamentoTexto =
    pos === "centro" ? "center" : ALINHA_CSS[t.alinhamento];

  const texto = (
    <div style={{ ...estilo(t), textAlign: alinhamentoTexto, flex: 1 }}>
      {linhas.length ? (
        linhas.map((l, i) => (
          <div key={i} style={{ fontWeight: i === 0 ? 700 : undefined }}>
            {l}
          </div>
        ))
      ) : (
        <span className="italic opacity-40">
          Preencha os Dados do Escritorio
        </span>
      )}
    </div>
  );

  // eslint-disable-next-line @next/next/no-img-element
  // a altura vem da configuracao, igual ao `add_picture` do docx_timbre;
  // a largura acompanha, mantendo a proporcao da imagem
  const logo = temLogo ? (
    <Redimensionavel
      src={logoSrc!}
      campo="logo_altura"
      altura={config.logo_altura}
      escala={escala}
      onAltura={onAltura}
    />
  ) : null;

  const empilhado = pos === "acima" || pos === "centro";

  return (
    <div
      style={{
        borderBottom: "0.75pt solid rgba(15,23,41,.25)",
        paddingBottom: 8,
        marginBottom: 14,
      }}
    >
      {numeracao}
      <div
        style={{
          display: "flex",
          flexDirection: empilhado ? "column" : "row",
          alignItems: "center",
          gap: 12,
        }}
      >
        {pos === "direita" ? (
          <>
            {texto}
            {logo}
          </>
        ) : (
          <>
            {logo}
            {texto}
          </>
        )}
      </div>
    </div>
  );
}

function Rodape({
  config,
  escritorio,
  pagina,
  total,
}: {
  config: Configuracao;
  escritorio?: Escritorio;
  pagina: number;
  total: number;
}) {
  const t = config.rodape_tipografia;
  const lado = config.rodape_numeracao_alinhamento;

  // mesma ordem do docx_timbre: dados do escritorio, depois o texto livre
  const conteudo = [
    ...linhasEscritorio(escritorio, config.rodape_campos),
    ...(config.rodape_texto ? [config.rodape_texto] : []),
  ];

  // se a numeracao subiu para o cabecalho, o rodape nao a repete
  const numeracao =
    config.rodape_numeracao && config.numeracao_local !== "cabecalho" ? (
      <span style={{ whiteSpace: "nowrap" }}>
        Pagina {pagina} de {total}
      </span>
    ) : null;

  const base: React.CSSProperties = {
    ...estilo(t),
    borderTop: "0.75pt solid rgba(15,23,41,.2)",
    // mesmos respiros do `_separador` no docx_timbre: 10pt em cima, 7 embaixo
    marginTop: 10,
    paddingTop: 7,
  };

  // com uma linha so, texto e numeracao dividem a mesma altura
  if (conteudo.length === 1 && numeracao && lado !== "centro") {
    return (
      <div
        style={{
          ...base,
          display: "flex",
          alignItems: "center",
          gap: 10,
          justifyContent: "space-between",
        }}
      >
        {lado === "esquerda" && numeracao}
        <span style={{ flex: 1, textAlign: ALINHA_CSS[t.alinhamento] }}>
          {conteudo[0]}
        </span>
        {lado === "direita" && numeracao}
      </div>
    );
  }

  return (
    <div style={base}>
      {conteudo.length ? (
        conteudo.map((linha, i) => <div key={i}>{linha}</div>)
      ) : (
        <div className="italic opacity-40">Rodape vazio</div>
      )}
      {numeracao && (
        <div style={{ textAlign: ALINHA_CSS[lado] }}>{numeracao}</div>
      )}
    </div>
  );
}

function Pagina({
  children,
  escala,
}: {
  children: React.ReactNode;
  escala: number;
}) {
  return (
    <div
      style={{
        width: LARGURA_PT,
        height: ALTURA_PT,
        transform: `scale(${escala})`,
        transformOrigin: "top left",
        background: "#fff",
        padding: MARGEM_PT,
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 2px 12px rgba(15,23,41,.12)",
        borderRadius: 2,
      }}
    >
      {children}
    </div>
  );
}

export function PreviewA4({
  config,
  escritorio,
  logoSrc,
  rubricaSrc,
  assinaturaSrc,
  pagina,
  escala = 0.62,
  onAltura,
}: {
  config: Configuracao;
  escritorio?: Escritorio;
  logoSrc: string | null;
  rubricaSrc: string | null;
  assinaturaSrc: string | null;
  /** "primeira" mostra o miolo; "ultima" mostra assinatura, rubrica e QR */
  pagina: "primeira" | "ultima";
  escala?: number;
  /** ausente = preview so de leitura, sem as alcas de redimensionar */
  onAltura?: (campo: CampoAltura, valor: number) => void;
}) {
  const ehUltima = pagina === "ultima";
  const ancorada = config.assinatura_modo === "ancora";

  // O carimbo real alinha a imagem pelo INICIO da linha do nome (`ancora.x`
  // em pdf_carimbo), nao pelo centro dela. Aqui o bloco do nome tem 240pt
  // centrados, entao encostamos a assinatura na borda esquerda desse bloco.
  const assinatura = assinaturaSrc ? (
    <div
      style={{
        width: 240,
        margin: "0 auto",
        textAlign: ancorada ? "left" : "center",
      }}
    >
      <Redimensionavel
        src={assinaturaSrc}
        campo="assinatura_altura"
        altura={config.assinatura_altura}
        escala={escala}
        onAltura={onAltura}
      />
    </div>
  ) : (
    <div
      style={{
        height: config.assinatura_altura,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "9pt",
        color: "#b6bac7",
        fontStyle: "italic",
      }}
    >
      assinatura nao cadastrada
    </div>
  );

  return (
    <div
      style={{
        width: LARGURA_PT * escala,
        height: ALTURA_PT * escala,
        overflow: "hidden",
      }}
    >
      <Pagina escala={escala}>
        <Cabecalho
          config={config}
          escritorio={escritorio}
          logoSrc={logoSrc}
          escala={escala}
          onAltura={onAltura}
          numeracao={
            config.rodape_numeracao && config.numeracao_local === "cabecalho" ? (
              <div
                style={{
                  ...estilo(config.rodape_tipografia),
                  textAlign: ALINHA_CSS[config.rodape_numeracao_alinhamento],
                  marginBottom: 4,
                }}
              >
                Pagina {ehUltima ? 4 : 1} de 4
              </div>
            ) : null
          }
        />

        <div style={{ flex: 1, position: "relative", overflow: "hidden" }}>
          <div
            style={{
              fontFamily: "'Times New Roman', serif",
              fontSize: "11pt",
              lineHeight: 1.5,
              textAlign: "justify",
              color: "#1a1a1a",
            }}
          >
            {(ehUltima ? LOREM_JURIDICO.slice(3) : LOREM_JURIDICO).map((p, i) => (
              <p
                key={i}
                style={{
                  margin: "0 0 10pt",
                  textAlign: p === p.toUpperCase() ? "center" : "justify",
                  fontWeight: p === p.toUpperCase() ? 700 : 400,
                }}
              >
                {p}
              </p>
            ))}
          </div>

          {ehUltima && (
            <div style={{ marginTop: 24, textAlign: "center" }}>
              {/* modo "ancora" com "acima": a assinatura vem antes do nome */}
              {ancorada && config.assinatura_relativa === "acima" && assinatura}
              <div
                style={{
                  borderTop: "1pt solid #333",
                  width: 240,
                  margin: "2pt auto 0",
                  paddingTop: 4,
                  fontFamily: "'Times New Roman', serif",
                  fontSize: "10pt",
                }}
              >
                {escritorio?.signatario_nome ||
                  escritorio?.razao_social ||
                  "Nome do signatario"}
                {(escritorio?.signatario_oab || escritorio?.oab_numero) && (
                  <div style={{ fontSize: "9pt", color: "#555" }}>
                    OAB{" "}
                    {escritorio.signatario_oab ??
                      `${escritorio.oab_numero}${
                        escritorio.oab_seccional ? `/${escritorio.oab_seccional}` : ""
                      }`}
                  </div>
                )}
              </div>
              {ancorada && config.assinatura_relativa === "abaixo" && assinatura}
            </div>
          )}

          {/* modo "fixa": centralizada no pe da pagina, ignorando o nome —
              e o fallback do backend quando a ancora nao e encontrada */}
          {ehUltima && !ancorada && (
            <div
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                bottom: 46,
                textAlign: "center",
              }}
            >
              {assinatura}
            </div>
          )}

          {/* rubrica: paginas sem assinatura, ou seja, todas menos a ultima */}
          {rubricaSrc && !ehUltima && (
            <span style={{ position: "absolute", right: 0, bottom: 0 }}>
              <Redimensionavel
                src={rubricaSrc}
                campo="rubrica_altura"
                altura={config.rubrica_altura}
                escala={escala}
                onAltura={onAltura}
                opacidade={0.9}
              />
            </span>
          )}

          {/* QR de verificacao: so na ultima pagina, e so se ativado */}
          {ehUltima && config.qrcode_ativo && (
            <div
              style={{
                position: "absolute",
                left: 0,
                bottom: 0,
                display: "flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <div
                style={{
                  width: 42,
                  height: 42,
                  background:
                    "repeating-conic-gradient(#0F1729 0% 25%, #fff 0% 50%) 50%/8px 8px",
                  border: "1px solid #0F1729",
                }}
              />
              <div style={{ fontSize: "6.5pt", color: "#555", lineHeight: 1.3 }}>
                Verifique a autenticidade
                <br />
                <span style={{ fontFamily: "monospace" }}>MAYA-XXXX-XXXX</span>
              </div>
            </div>
          )}
        </div>

        <Rodape
          config={config}
          escritorio={escritorio}
          pagina={ehUltima ? 4 : 1}
          total={4}
        />
      </Pagina>
    </div>
  );
}
