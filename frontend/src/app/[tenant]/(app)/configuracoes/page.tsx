"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Mail, Save, Send } from "lucide-react";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { AreaTexto, Campo, EditorTipografia, Marcador } from "@/components/config/campos";
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
        rodape_texto: cfg.rodape_texto,
        rodape_tipografia: cfg.rodape_tipografia,
        rodape_numeracao: cfg.rodape_numeracao,
        rodape_numeracao_alinhamento: cfg.rodape_numeracao_alinhamento,
        rubricar_por_padrao: cfg.rubricar_por_padrao,
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
          <p className="mt-1 text-sm text-dark/55">
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
                : "border-transparent text-dark/50 hover:text-dark/75",
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
              </div>

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
                  <option value="sem_logo">Sem logo</option>
                </select>
              </div>

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
                <div>
                  <label className="rotulo">Posicao da numeracao</label>
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
                descricao="Carimbada no canto de todas as paginas quando ativada."
                url={urlArquivo(cfg.rubrica_url)}
                urlOriginal={urlArquivo(cfg.rubrica_original_url)}
                endpoint={`/api/${tenant}/configuracoes/imagens/rubrica`}
                onMudou={recarregarImagens}
              />

              <Marcador
                rotulo="Rubricar todas as paginas por padrao"
                descricao="Valor inicial do toggle na hora do upload."
                marcado={cfg.rubricar_por_padrao}
                onChange={(v) => setConfig("rubricar_por_padrao", v)}
              />

              <UploadImagem
                titulo="Assinatura"
                descricao="Aplicada na ultima pagina, acima da linha do nome."
                url={urlArquivo(cfg.assinatura_url)}
                urlOriginal={urlArquivo(cfg.assinatura_original_url)}
                endpoint={`/api/${tenant}/configuracoes/imagens/assinatura`}
                onMudou={recarregarImagens}
              />

              <p className="rounded-lg bg-teal/10 px-3 py-2 text-xs text-teal">
                O fundo branco vira transparente automaticamente. Compare o
                antes e o depois acima — o xadrez indica transparencia.
              </p>
            </>
          )}

          {aba === "email" && (
            <>
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
                <p className="mt-1.5 text-xs text-dark/45">
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
                <p className="mb-3 text-xs text-dark/45">
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
                        : "bg-white text-dark/50 hover:bg-cinza",
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

            <p className="mt-3 text-center text-[11px] leading-relaxed text-dark/40">
              Simulacao em A4 com os dados reais do escritorio.
              <br />
              Atualiza a cada alteracao, sem salvar.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
