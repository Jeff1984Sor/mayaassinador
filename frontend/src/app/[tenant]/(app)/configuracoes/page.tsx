"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileText, Loader2, Mail, Save, Send } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import {
  AreaTexto,
  Campo,
  EditorTipografia,
  Marcador,
  Tamanho,
} from "@/components/config/campos";
import { PreviewA4 } from "@/components/config/preview-a4";
import { UploadImagem } from "@/components/config/upload-imagem";
import { api, mensagemErro } from "@/lib/api";
import type { Configuracao, Escritorio, Fonte } from "@/lib/tipos";
import { cn } from "@/lib/utils";
import { useAuth } from "@/store/auth";

const ABAS = [
  { id: "escritorio", rotulo: "Dados do Escritorio" },
  { id: "cabecalho", rotulo: "Cabecalho" },
  { id: "rodape", rotulo: "Rodape" },
  { id: "imagens", rotulo: "Rubrica e Assinatura" },
  { id: "email", rotulo: "Email" },
] as const;

type AbaId = (typeof ABAS)[number]["id"];

/** Presets dos provedores mais usados por escritorio.
 *  Evita o suporte "qual e a porta mesmo?" — e os avisos de senha de app
 *  sao a causa numero 1 de falha de autenticacao. */
const PROVEDORES = [
  {
    id: "gmail",
    nome: "Gmail",
    host: "smtp.gmail.com",
    porta: 587,
    tls: true,
    aviso:
      "O Gmail recusa a senha da conta. Ative a verificacao em duas etapas e gere uma Senha de app em myaccount.google.com/apppasswords.",
  },
  {
    id: "m365",
    nome: "Microsoft 365 / Outlook",
    host: "smtp.office365.com",
    porta: 587,
    tls: true,
    aviso:
      "Se a conta tiver MFA, gere uma senha de aplicativo. O administrador precisa manter o SMTP AUTH habilitado na caixa.",
  },
  {
    id: "zoho",
    nome: "Zoho Mail",
    host: "smtp.zoho.com",
    porta: 587,
    tls: true,
    aviso: "Use uma senha especifica de aplicativo gerada no painel do Zoho.",
  },
  {
    id: "locaweb",
    nome: "Locaweb",
    host: "email-ssl.com.br",
    porta: 587,
    tls: true,
    aviso: "Usuario e o endereco de email completo. A senha e a do painel de email.",
  },
  {
    id: "hostgator",
    nome: "HostGator / cPanel",
    host: "mail.seudominio.com.br",
    porta: 587,
    tls: true,
    aviso: "Troque 'seudominio.com.br' pelo dominio do escritorio.",
  },
] as const;

const CAMPOS_CABECALHO: { chave: keyof Configuracao["cabecalho_campos"]; rotulo: string }[] = [
  { chave: "razao_social", rotulo: "Razao social" },
  { chave: "cnpj", rotulo: "CNPJ" },
  { chave: "oab", rotulo: "OAB" },
  { chave: "endereco", rotulo: "Endereco" },
  { chave: "telefone", rotulo: "Telefone" },
  { chave: "whatsapp", rotulo: "WhatsApp" },
  { chave: "email", rotulo: "Email" },
  { chave: "site", rotulo: "Site" },
];

function Opcao({
  marcada,
  titulo,
  descricao,
  onClick,
}: {
  marcada: boolean;
  titulo: string;
  descricao: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-start gap-3 rounded-lg border p-3 text-left transition",
        marcada
          ? "border-navy bg-navy/5"
          : "border-dark/10 hover:border-navy/30 hover:bg-cinza",
      )}
    >
      <span
        className={cn(
          "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2",
          marcada ? "border-navy" : "border-dark/25",
        )}
      >
        {marcada && <span className="h-2 w-2 rounded-full bg-navy" />}
      </span>
      <span>
        <span className="block text-sm font-medium text-dark">{titulo}</span>
        <span className="block text-xs text-dark/65">{descricao}</span>
      </span>
    </button>
  );
}

export default function ConfiguracoesPage() {
  const { tenant } = useParams<{ tenant: string }>();
  const qc = useQueryClient();
  const token = useAuth((s) => s.token);

  const [aba, setAba] = useState<AbaId>("escritorio");
  const [paginaPreview, setPaginaPreview] = useState<"primeira" | "ultima">("primeira");
  const [esc, setEsc] = useState<Escritorio | null>(null);
  const [cfg, setCfg] = useState<Configuracao | null>(null);
  const [senhaSmtp, setSenhaSmtp] = useState("");
  const [emailTeste, setEmailTeste] = useState("");
  // muda a cada upload para furar o cache do <img>
  const [versao, setVersao] = useState(0);

  const { data: fontes = [] } = useQuery<Fonte[]>({
    queryKey: ["fontes"],
    queryFn: async () =>
      (await api.get(`/api/${tenant}/configuracoes/fontes`)).data,
    staleTime: Infinity,
  });

  const qEsc = useQuery<Escritorio>({
    queryKey: ["escritorio", tenant],
    queryFn: async () => (await api.get(`/api/${tenant}/escritorio`)).data,
  });

  const qCfg = useQuery<Configuracao>({
    queryKey: ["configuracao", tenant],
    queryFn: async () => (await api.get(`/api/${tenant}/configuracoes`)).data,
  });

  // o formulario trabalha em estado local: e o que torna o preview instantaneo,
  // sem ida ao backend a cada tecla
  useEffect(() => {
    if (qEsc.data) setEsc(qEsc.data);
  }, [qEsc.data]);
  useEffect(() => {
    if (qCfg.data) setCfg(qCfg.data);
  }, [qCfg.data]);

  const urlArquivo = useMemo(
    () => (caminho: string | null) =>
      caminho && token
        ? `${api.defaults.baseURL}${caminho}?token=${token}&v=${versao}`
        : null,
    [token, versao],
  );

  const salvar = useMutation({
    mutationFn: async () => {
      if (!esc || !cfg) return;
      const { id, logo_url, ...dadosEsc } = esc;
      await api.put(`/api/${tenant}/escritorio`, dadosEsc);
      await api.put(`/api/${tenant}/configuracoes`, {
        cabecalho_campos: cfg.cabecalho_campos,
        cabecalho_tipografia: cfg.cabecalho_tipografia,
        logo_posicao: cfg.logo_posicao,
        logo_altura: cfg.logo_altura,
        rodape_campos: cfg.rodape_campos,
        rodape_texto: cfg.rodape_texto,
        rodape_tipografia: cfg.rodape_tipografia,
        rodape_numeracao: cfg.rodape_numeracao,
        rodape_numeracao_alinhamento: cfg.rodape_numeracao_alinhamento,
        numeracao_local: cfg.numeracao_local,
        rubricar_por_padrao: cfg.rubricar_por_padrao,
        qrcode_ativo: cfg.qrcode_ativo,
        rubrica_altura: cfg.rubrica_altura,
        assinatura_altura: cfg.assinatura_altura,
        assinatura_modo: cfg.assinatura_modo,
        assinatura_ancora: cfg.assinatura_ancora,
        assinatura_relativa: cfg.assinatura_relativa,
        assinatura_deslocamento: cfg.assinatura_deslocamento,
        smtp_host: cfg.smtp_host,
        smtp_porta: cfg.smtp_porta,
        smtp_usuario: cfg.smtp_usuario,
        smtp_senha: senhaSmtp || null,
        smtp_tls: cfg.smtp_tls,
        email_remetente_nome: cfg.email_remetente_nome,
        email_assunto_padrao: cfg.email_assunto_padrao,
        email_mensagem_padrao: cfg.email_mensagem_padrao,
      });
    },
    onSuccess: () => {
      toast.success("Configuracoes salvas");
      setSenhaSmtp("");
      qc.invalidateQueries({ queryKey: ["escritorio", tenant] });
      qc.invalidateQueries({ queryKey: ["configuracao", tenant] });
    },
    onError: (e) => toast.error(mensagemErro(e, "Nao foi possivel salvar")),
  });

  const pdfTeste = useMutation({
    mutationFn: async () => {
      const { data } = await api.post(
        `/api/${tenant}/configuracoes/pdf-teste`,
        {},
        { responseType: "blob" },
      );
      // abre numa aba nova em vez de baixar: a ideia e comparar com o
      // preview ao lado, nao arquivar o teste
      const url = URL.createObjectURL(data as Blob);
      window.open(url, "_blank");
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    },
    onError: (e) => toast.error(mensagemErro(e, "Falha ao gerar o PDF de teste")),
  });

  const testarEmail = useMutation({
    mutationFn: async () =>
      (
        await api.post(`/api/${tenant}/configuracoes/email-teste`, {
          destinatario: emailTeste,
        })
      ).data,
    onSuccess: (d) => toast.success(d.mensagem),
    onError: (e) => toast.error(mensagemErro(e, "Falha ao enviar")),
  });

  function recarregarImagens() {
    setVersao((v) => v + 1);
    qc.invalidateQueries({ queryKey: ["configuracao", tenant] });
    qc.invalidateQueries({ queryKey: ["escritorio", tenant] });
  }

  if (!esc || !cfg) {
    return (
      <div className="flex h-screen items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-navy/40" />
      </div>
    );
  }

  const provedorAtual = PROVEDORES.find((p) => p.host === cfg.smtp_host);

  const setEscritorio = <K extends keyof Escritorio>(k: K, v: Escritorio[K]) =>
    setEsc({ ...esc, [k]: v });
  const setConfig = <K extends keyof Configuracao>(k: K, v: Configuracao[K]) =>
    setCfg({ ...cfg, [k]: v });

  return (
    <div className="px-8 py-7">
      <header className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-dark">
            Configuracoes
          </h1>
          <p className="mt-1 text-sm text-dark/75">
            Cadastre uma vez — reflete no cabecalho, no rodape, no email e na
            pagina de verificacao.
          </p>
        </div>
        <button
          onClick={() => salvar.mutate()}
          disabled={salvar.isPending}
          className="btn-primario shrink-0"
        >
          {salvar.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          Salvar
        </button>
      </header>

      <div className="mb-6 flex gap-1 overflow-x-auto border-b border-dark/[.08]">
        {ABAS.map((a) => (
          <button
            key={a.id}
            onClick={() => setAba(a.id)}
            className={cn(
              "whitespace-nowrap border-b-2 px-4 py-2.5 text-sm transition",
              aba === a.id
                ? "border-navy font-medium text-navy"
                : "border-transparent text-dark/70 hover:text-dark/90",
            )}
          >
            {a.rotulo}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_400px]">
        {/* ------------------ FORMULARIO ------------------ */}
        <div className="cartao space-y-5 p-6">
          {aba === "escritorio" && (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <Campo
                  rotulo="Razao social *"
                  valor={esc.razao_social}
                  onChange={(v) => setEscritorio("razao_social", v)}
                  className="sm:col-span-2"
                />
                <Campo
                  rotulo="Nome fantasia"
                  valor={esc.nome_fantasia}
                  onChange={(v) => setEscritorio("nome_fantasia", v || null)}
                />
                <Campo
                  rotulo="CNPJ"
                  valor={esc.cnpj}
                  placeholder="00.000.000/0000-00"
                  onChange={(v) => setEscritorio("cnpj", v || null)}
                />
                <Campo
                  rotulo="OAB - numero"
                  valor={esc.oab_numero}
                  placeholder="123456"
                  onChange={(v) => setEscritorio("oab_numero", v || null)}
                />
                <Campo
                  rotulo="OAB - seccional"
                  valor={esc.oab_seccional}
                  placeholder="SP"
                  maxLength={2}
                  onChange={(v) =>
                    setEscritorio("oab_seccional", v.toUpperCase() || null)
                  }
                />
                <Campo
                  rotulo="Signatario - nome"
                  valor={esc.signatario_nome}
                  placeholder="Dra. Maria Silva"
                  onChange={(v) => setEscritorio("signatario_nome", v || null)}
                />
                <Campo
                  rotulo="Signatario - OAB"
                  valor={esc.signatario_oab}
                  placeholder="123456/SP"
                  onChange={(v) => setEscritorio("signatario_oab", v || null)}
                />
              </div>

              <p className="rounded-lg bg-indigo/10 px-3 py-2 text-xs text-navy">
                O nome do signatario e quem assina os documentos — e o texto
                que o sistema procura no PDF para posicionar a assinatura
                automaticamente (aba Rubrica e Assinatura).
              </p>

              <div className="grid gap-4 sm:grid-cols-6">
                <Campo
                  rotulo="Logradouro"
                  valor={esc.logradouro}
                  onChange={(v) => setEscritorio("logradouro", v || null)}
                  className="sm:col-span-4"
                />
                <Campo
                  rotulo="Numero"
                  valor={esc.numero}
                  onChange={(v) => setEscritorio("numero", v || null)}
                  className="sm:col-span-2"
                />
                <Campo
                  rotulo="Complemento"
                  valor={esc.complemento}
                  onChange={(v) => setEscritorio("complemento", v || null)}
                  className="sm:col-span-3"
                />
                <Campo
                  rotulo="Bairro"
                  valor={esc.bairro}
                  onChange={(v) => setEscritorio("bairro", v || null)}
                  className="sm:col-span-3"
                />
                <Campo
                  rotulo="Cidade"
                  valor={esc.cidade}
                  onChange={(v) => setEscritorio("cidade", v || null)}
                  className="sm:col-span-3"
                />
                <Campo
                  rotulo="UF"
                  valor={esc.uf}
                  maxLength={2}
                  onChange={(v) => setEscritorio("uf", v.toUpperCase() || null)}
                  className="sm:col-span-1"
                />
                <Campo
                  rotulo="CEP"
                  valor={esc.cep}
                  placeholder="00000-000"
                  onChange={(v) => setEscritorio("cep", v || null)}
                  className="sm:col-span-2"
                />
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <Campo
                  rotulo="Telefone"
                  valor={esc.telefone}
                  onChange={(v) => setEscritorio("telefone", v || null)}
                />
                <Campo
                  rotulo="WhatsApp"
                  valor={esc.whatsapp}
                  onChange={(v) => setEscritorio("whatsapp", v || null)}
                />
                <Campo
                  rotulo="Email"
                  tipo="email"
                  valor={esc.email}
                  onChange={(v) => setEscritorio("email", v || null)}
                />
                <Campo
                  rotulo="Site"
                  valor={esc.site}
                  placeholder="www.escritorio.com.br"
                  onChange={(v) => setEscritorio("site", v || null)}
                />
              </div>

              <UploadImagem
                titulo="Logo do escritorio"
                descricao="PNG, JPG ou WEBP ate 5MB. Aparece no cabecalho."
                url={urlArquivo(esc.logo_url)}
                endpoint={`/api/${tenant}/escritorio/logo`}
                onMudou={recarregarImagens}
              />
            </>
          )}

          {aba === "cabecalho" && (
            <>
              <div>
                <p className="rotulo">Quais dados aparecem no cabecalho</p>
                <div className="grid grid-cols-2 gap-x-4">
                  {CAMPOS_CABECALHO.map(({ chave, rotulo }) => (
                    <Marcador
                      key={chave}
                      rotulo={rotulo}
                      marcado={cfg.cabecalho_campos[chave]}
                      onChange={(v) =>
                        setConfig("cabecalho_campos", {
                          ...cfg.cabecalho_campos,
                          [chave]: v,
                        })
                      }
                    />
                  ))}
                </div>
              </div>

              <div>
                <label className="rotulo">Posicao do logo</label>
                <select
                  className="campo"
                  value={cfg.logo_posicao}
                  onChange={(e) =>
                    setConfig("logo_posicao", e.target.value as Configuracao["logo_posicao"])
                  }
                >
                  <option value="esquerda">A esquerda do texto</option>
                  <option value="direita">A direita do texto</option>
                  <option value="acima">Acima do texto</option>
                  <option value="centro">
                    Centralizado (logo e texto centrados)
                  </option>
                  <option value="sem_logo">Sem logo</option>
                </select>
              </div>

              {cfg.logo_posicao !== "sem_logo" && (
                <Tamanho
                  rotulo="Tamanho do logo"
                  descricao="Altura no cabecalho. A largura acompanha, mantendo a proporcao da imagem."
                  valor={cfg.logo_altura}
                  onChange={(v) => setConfig("logo_altura", v)}
                  min={10}
                  max={120}
                  padrao={34}
                />
              )}

              <EditorTipografia
                titulo="Tipografia do cabecalho"
                valor={cfg.cabecalho_tipografia}
                fontes={fontes}
                onChange={(t) => setConfig("cabecalho_tipografia", t)}
              />

              <p className="rounded-lg bg-indigo/10 px-3 py-2 text-xs text-navy">
                So aparecem fontes instaladas no servidor. Outras seriam
                substituidas na conversao e o PDF sairia diferente do preview.
              </p>
            </>
          )}

          {aba === "rodape" && (
            <>
              <div>
                <p className="rotulo">Quais dados aparecem no rodape</p>
                <div className="grid grid-cols-2 gap-x-4">
                  {CAMPOS_CABECALHO.map(({ chave, rotulo }) => (
                    <Marcador
                      key={chave}
                      rotulo={rotulo}
                      marcado={cfg.rodape_campos[chave]}
                      onChange={(v) =>
                        setConfig("rodape_campos", {
                          ...cfg.rodape_campos,
                          [chave]: v,
                        })
                      }
                    />
                  ))}
                </div>
                <p className="mt-1 text-xs text-dark/65">
                  Mesmos dados do cabecalho, escolhidos de forma independente.
                  O rodape nao leva logo.
                </p>
              </div>

              <AreaTexto
                rotulo="Texto do rodape"
                valor={cfg.rodape_texto}
                placeholder="Ex: Documento gerado eletronicamente."
                onChange={(v) => setConfig("rodape_texto", v || null)}
              />

              <Marcador
                rotulo="Numerar as paginas"
                descricao='Formato "Pagina X de Y"'
                marcado={cfg.rodape_numeracao}
                onChange={(v) => setConfig("rodape_numeracao", v)}
              />

              {cfg.rodape_numeracao && (
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="rotulo">Onde</label>
                    <select
                      className="campo"
                      value={cfg.numeracao_local}
                      onChange={(e) =>
                        setConfig(
                          "numeracao_local",
                          e.target.value as Configuracao["numeracao_local"],
                        )
                      }
                    >
                      <option value="rodape">No rodape</option>
                      <option value="cabecalho">No cabecalho (topo)</option>
                    </select>
                  </div>
                  <div>
                    <label className="rotulo">Alinhamento</label>
                    <select
                      className="campo"
                      value={cfg.rodape_numeracao_alinhamento}
                      onChange={(e) =>
                        setConfig(
                          "rodape_numeracao_alinhamento",
                          e.target.value as Configuracao["rodape_numeracao_alinhamento"],
                        )
                      }
                    >
                      <option value="esquerda">Esquerda</option>
                      <option value="centro">Centro</option>
                      <option value="direita">Direita</option>
                    </select>
                  </div>
                </div>
              )}

              <EditorTipografia
                titulo="Tipografia do rodape"
                valor={cfg.rodape_tipografia}
                fontes={fontes}
                onChange={(t) => setConfig("rodape_tipografia", t)}
              />
            </>
          )}

          {aba === "imagens" && (
            <>
              <UploadImagem
                titulo="Rubrica"
                descricao="Carimbada nas paginas sem assinatura — todas menos a ultima."
                url={urlArquivo(cfg.rubrica_url)}
                urlOriginal={urlArquivo(cfg.rubrica_original_url)}
                endpoint={`/api/${tenant}/configuracoes/imagens/rubrica`}
                onMudou={recarregarImagens}
              />

              <Tamanho
                rotulo="Tamanho da rubrica"
                descricao="Altura do carimbo no canto inferior direito das paginas."
                valor={cfg.rubrica_altura}
                onChange={(v) => setConfig("rubrica_altura", v)}
                min={10}
                max={80}
                padrao={26}
              />

              <Marcador
                rotulo="Rubricar por padrao"
                descricao="Valor inicial do toggle na hora do upload."
                marcado={cfg.rubricar_por_padrao}
                onChange={(v) => setConfig("rubricar_por_padrao", v)}
              />

              <p className="rounded-lg bg-indigo/10 px-3 py-2 text-xs text-navy">
                A rubrica vai nas paginas que nao tem assinatura: da primeira
                ate a penultima. A ultima pagina leva so a assinatura. Documento
                de uma pagina nao e rubricado.
              </p>

              <UploadImagem
                titulo="Assinatura"
                descricao="Aplicada na ultima pagina, acima da linha do nome."
                url={urlArquivo(cfg.assinatura_url)}
                urlOriginal={urlArquivo(cfg.assinatura_original_url)}
                endpoint={`/api/${tenant}/configuracoes/imagens/assinatura`}
                onMudou={recarregarImagens}
              />

              <Tamanho
                rotulo="Tamanho da assinatura"
                descricao="Altura da assinatura na pagina do fecho."
                valor={cfg.assinatura_altura}
                onChange={(v) => setConfig("assinatura_altura", v)}
                min={20}
                max={200}
                padrao={84}
              />

              <p className="rounded-lg bg-teal/10 px-3 py-2 text-xs text-teal">
                O fundo branco vira transparente automaticamente. Compare o
                antes e o depois acima — o xadrez indica transparencia.
              </p>

              <fieldset className="rounded-lg border border-dark/[.08] p-4">
                <legend className="px-1.5 text-xs font-medium uppercase tracking-wide text-dark/65">
                  Posicao da assinatura
                </legend>

                <div className="space-y-2">
                  <Opcao
                    marcada={cfg.assinatura_modo === "fixa"}
                    titulo="Posicao fixa"
                    descricao="Centralizada no rodape da ultima pagina."
                    onClick={() => setConfig("assinatura_modo", "fixa")}
                  />
                  <Opcao
                    marcada={cfg.assinatura_modo === "ancora"}
                    titulo="Junto ao nome do signatario"
                    descricao="O sistema procura o nome no texto do documento e assina ali."
                    onClick={() => setConfig("assinatura_modo", "ancora")}
                  />
                </div>

                {cfg.assinatura_modo === "ancora" && (
                  <div className="mt-4 space-y-3 border-t border-dark/[.07] pt-4">
                    <Campo
                      rotulo="Texto procurado"
                      valor={cfg.assinatura_ancora}
                      placeholder={
                        esc.signatario_nome ?? "Nome do signatario (aba 1)"
                      }
                      onChange={(v) => setConfig("assinatura_ancora", v || null)}
                    />
                    <p className="-mt-1.5 text-xs text-dark/65">
                      Em branco, usa o nome do signatario cadastrado nos Dados
                      do Escritorio. A busca ignora acentos e maiusculas.
                    </p>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="rotulo">Assinar</label>
                        <select
                          className="campo"
                          value={cfg.assinatura_relativa}
                          onChange={(e) =>
                            setConfig(
                              "assinatura_relativa",
                              e.target.value as Configuracao["assinatura_relativa"],
                            )
                          }
                        >
                          <option value="abaixo">Abaixo do nome</option>
                          <option value="acima">Acima do nome</option>
                        </select>
                      </div>
                      <div>
                        <label className="rotulo">Folga (pt)</label>
                        <input
                          type="number"
                          min={0}
                          max={200}
                          className="campo"
                          value={cfg.assinatura_deslocamento}
                          onChange={(e) =>
                            setConfig(
                              "assinatura_deslocamento",
                              Number(e.target.value) || 0,
                            )
                          }
                        />
                      </div>
                    </div>

                    <p className="rounded-lg bg-amber/10 px-3 py-2 text-xs text-amber">
                      Se o texto nao for encontrado no documento, a assinatura
                      volta para a posicao fixa e o motivo fica registrado no
                      historico do documento. Nunca sai PDF sem assinatura.
                    </p>
                  </div>
                )}
              </fieldset>

              <fieldset className="rounded-lg border border-dark/[.08] p-4">
                <legend className="px-1.5 text-xs font-medium uppercase tracking-wide text-dark/65">
                  QR code de verificacao
                </legend>
                <Marcador
                  rotulo="Estampar o QR code na ultima pagina"
                  descricao="Aponta para a pagina publica de verificacao do documento."
                  marcado={cfg.qrcode_ativo}
                  onChange={(v) => setConfig("qrcode_ativo", v)}
                />
                {!cfg.qrcode_ativo && (
                  <p className="mt-2 rounded-lg bg-indigo/10 px-3 py-2 text-xs text-navy">
                    Sem o QR o documento continua verificavel: o hash SHA-256 e
                    o codigo de autenticidade seguem sendo gerados e aparecem
                    na listagem e no email. So nao ficam impressos no PDF.
                  </p>
                )}
              </fieldset>
            </>
          )}

          {aba === "email" && (
            <>
              <div>
                <p className="rotulo">Provedor</p>
                <div className="flex flex-wrap gap-2">
                  {PROVEDORES.map((p) => {
                    const ativo = cfg.smtp_host === p.host;
                    return (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() =>
                          setCfg({
                            ...cfg,
                            smtp_host: p.host,
                            smtp_porta: p.porta,
                            smtp_tls: p.tls,
                          })
                        }
                        className={cn(
                          "rounded-lg border px-3 py-1.5 text-xs font-medium transition",
                          ativo
                            ? "border-navy bg-navy text-white"
                            : "border-dark/12 text-dark/85 hover:border-navy/35 hover:bg-cinza",
                        )}
                      >
                        {p.nome}
                      </button>
                    );
                  })}
                </div>
                {provedorAtual && (
                  <p className="mt-2 rounded-lg bg-amber/10 px-3 py-2 text-xs text-amber">
                    {provedorAtual.aviso}
                  </p>
                )}
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <Campo
                  rotulo="Servidor SMTP"
                  valor={cfg.smtp_host}
                  placeholder="smtp.gmail.com"
                  onChange={(v) => setConfig("smtp_host", v || null)}
                  className="sm:col-span-2"
                />
                <Campo
                  rotulo="Porta"
                  tipo="number"
                  valor={cfg.smtp_porta?.toString() ?? ""}
                  placeholder="587"
                  onChange={(v) => setConfig("smtp_porta", v ? Number(v) : null)}
                />
              </div>

              <Campo
                rotulo="Usuario"
                valor={cfg.smtp_usuario}
                placeholder="contato@escritorio.com.br"
                onChange={(v) => setConfig("smtp_usuario", v || null)}
              />

              <div>
                <label className="rotulo">
                  Senha{" "}
                  {cfg.smtp_senha_definida && (
                    <span className="font-normal text-teal">· ja cadastrada</span>
                  )}
                </label>
                <input
                  type="password"
                  className="campo"
                  placeholder={
                    cfg.smtp_senha_definida
                      ? "Deixe em branco para manter a atual"
                      : "Senha ou senha de app"
                  }
                  value={senhaSmtp}
                  onChange={(e) => setSenhaSmtp(e.target.value)}
                />
                <p className="mt-1.5 text-xs text-dark/65">
                  Guardada criptografada no banco. No Gmail, use uma senha de
                  app — a senha da conta e recusada.
                </p>
              </div>

              <Marcador
                rotulo="Usar TLS (STARTTLS)"
                descricao="Deixe ativo para a porta 587. Na 465 o SSL e automatico."
                marcado={cfg.smtp_tls}
                onChange={(v) => setConfig("smtp_tls", v)}
              />

              <Campo
                rotulo="Nome do remetente"
                valor={cfg.email_remetente_nome}
                placeholder="Escritorio Silva Advogados"
                onChange={(v) => setConfig("email_remetente_nome", v || null)}
              />
              <Campo
                rotulo="Assunto padrao"
                valor={cfg.email_assunto_padrao}
                placeholder="Documento assinado"
                onChange={(v) => setConfig("email_assunto_padrao", v || null)}
              />
              <AreaTexto
                rotulo="Mensagem padrao"
                valor={cfg.email_mensagem_padrao}
                linhas={4}
                placeholder="Prezado(a), segue em anexo o documento assinado."
                onChange={(v) => setConfig("email_mensagem_padrao", v || null)}
              />

              <div className="rounded-lg border border-dark/[.08] p-4">
                <p className="mb-1 flex items-center gap-2 text-sm font-medium text-dark">
                  <Mail className="h-4 w-4 text-navy" />
                  Enviar email de teste
                </p>
                <p className="mb-3 text-xs text-dark/65">
                  Salve as configuracoes antes — o teste usa o que esta no banco.
                </p>
                <div className="flex gap-2">
                  <input
                    type="email"
                    className="campo"
                    placeholder="destinatario@exemplo.com"
                    value={emailTeste}
                    onChange={(e) => setEmailTeste(e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => testarEmail.mutate()}
                    disabled={!emailTeste || testarEmail.isPending}
                    className="btn-primario shrink-0"
                  >
                    {testarEmail.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                    Enviar
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        {/* ------------------ PREVIEW ------------------ */}
        <div className="lg:sticky lg:top-6 lg:self-start">
          <div className="cartao p-4">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm font-medium text-dark">Preview</p>
              <div className="flex overflow-hidden rounded-lg border border-dark/10 text-xs">
                {(["primeira", "ultima"] as const).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPaginaPreview(p)}
                    className={cn(
                      "px-2.5 py-1.5 transition",
                      paginaPreview === p
                        ? "bg-navy text-white"
                        : "bg-white text-dark/70 hover:bg-cinza",
                    )}
                  >
                    {p === "primeira" ? "1a pagina" : "Ultima"}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-center rounded-lg bg-cinza p-3">
              <PreviewA4
                config={cfg}
                escritorio={esc}
                logoSrc={urlArquivo(esc.logo_url)}
                rubricaSrc={urlArquivo(cfg.rubrica_url)}
                assinaturaSrc={urlArquivo(cfg.assinatura_url)}
                pagina={paginaPreview}
                escala={0.58}
              />
            </div>

            <button
              onClick={() => pdfTeste.mutate()}
              disabled={pdfTeste.isPending}
              className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg
                         border border-navy/20 py-2.5 text-sm font-medium text-navy
                         transition hover:bg-navy/5 disabled:opacity-60"
            >
              {pdfTeste.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <FileText className="h-4 w-4" />
              )}
              Gerar PDF de teste
            </button>

            <p className="mt-3 text-center text-[11px] leading-relaxed text-dark/62">
              Roda o pipeline real no servidor com uma peticao de exemplo.
              <br />
              Use para conferir se o PDF bate com o preview. Salve antes.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
