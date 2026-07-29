"use client";

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
}: {
  config: Configuracao;
  escritorio?: Escritorio;
  logoSrc: string | null;
  numeracao?: React.ReactNode;
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
  const logo = temLogo ? (
    <img
      src={logoSrc!}
      alt=""
      style={{ maxHeight: 46, maxWidth: 120, objectFit: "contain" }}
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
    paddingTop: 6,
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
}: {
  config: Configuracao;
  escritorio?: Escritorio;
  logoSrc: string | null;
  rubricaSrc: string | null;
  assinaturaSrc: string | null;
  /** "primeira" mostra o miolo; "ultima" mostra assinatura, rubrica e QR */
  pagina: "primeira" | "ultima";
  escala?: number;
}) {
  const ehUltima = pagina === "ultima";

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
              {assinaturaSrc ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={assinaturaSrc}
                  alt=""
                  style={{ maxHeight: 64, maxWidth: 220, objectFit: "contain" }}
                />
              ) : (
                <div
                  style={{
                    height: 64,
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
              )}
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
            </div>
          )}

          {/* rubrica: canto inferior direito de todas as paginas */}
          {rubricaSrc && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={rubricaSrc}
              alt=""
              style={{
                position: "absolute",
                right: 0,
                bottom: 0,
                maxHeight: 28,
                maxWidth: 80,
                objectFit: "contain",
                opacity: 0.9,
              }}
            />
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
